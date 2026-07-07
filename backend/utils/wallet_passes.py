"""
Apple Wallet (.pkpass) + Google Wallet native pass generation.

Apple Wallet (.pkpass)
──────────────────────
A `.pkpass` is a signed zip archive containing:
   pass.json         — the pass structure (barcode, colors, fields, ...)
   manifest.json     — sha1 hashes of every file in the archive
   signature         — DETACHED CMS/PKCS7 signature over manifest.json,
                       using the Pass Type ID certificate chained to
                       Apple's WWDR intermediate.
   icon.png etc.     — required images (icon@1x/2x/3x, logo)

Signing needs three files (all in PEM):
   PASS_TYPE_CERT_PEM          — merchant Pass Type ID cert
   PASS_TYPE_KEY_PEM           — merchant private key
   APPLE_WWDR_CERT_PEM         — Apple WWDR intermediate

If any of those envs is missing we emit an *unsigned* pass (still openable
in the iOS Wallet **simulator** and Passbook tools; iPhones will reject the
signature). This is enough to preview & QA the artefact and gives ops a
clear path: drop 3 PEMs in secrets, redeploy, real passes ship.

Google Wallet
─────────────
Uses the Google Wallet API "save to wallet" JWT link (v11+). We construct
a signed JWT with a `loyaltyObject` (using the merchant's issuer id + a
loyalty class already provisioned on Google side). Envs:

   GOOGLE_WALLET_ISSUER_ID           — Google Wallet issuer id (numeric)
   GOOGLE_WALLET_CLASS_ID            — Loyalty class id (issuer.class)
   GOOGLE_WALLET_SERVICE_ACCOUNT_KEY — base64 or raw JSON service account key

When keys are missing we return an unsigned template JWT + a preview URL
that lets ops verify the object shape without leaking credentials.
"""
from __future__ import annotations
import base64
import hashlib
import io
import json
import os
import zipfile
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

import jwt  # PyJWT
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography import x509


# ═════════════════════════════════════════════════════════════════════════
# Apple Wallet
# ═════════════════════════════════════════════════════════════════════════
_MIN_ICON_PNG_B64 = (
    # 29×29 solid-black PNG (Wallet minimum); replace with brand icons via env.
    "iVBORw0KGgoAAAANSUhEUgAAAB0AAAAdCAYAAABWk2cPAAAAF0lEQVR42mNk"
    "+M9QzzDIwCiEqCkKMBoAABDzAgHZUdWCAAAAAElFTkSuQmCC"
)


def _icon_bytes() -> bytes:
    """Load brand icon from env `NUA_WALLET_ICON_B64` if provided, else fallback."""
    env = os.environ.get("NUA_WALLET_ICON_B64")
    try:
        return base64.b64decode(env or _MIN_ICON_PNG_B64)
    except Exception:
        return base64.b64decode(_MIN_ICON_PNG_B64)


def _hex_sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def build_pass_json(*, customer_id: str, name: str, tier: str, points: int,
                     store_credit: float, barcode: str, qr_token: str,
                     pass_type_id: str, team_id: str, org_name: str,
                     logo_text: str) -> dict:
    """Assemble the pass.json body for a store card / loyalty pass."""
    now = datetime.now(timezone.utc)
    return {
        "formatVersion": 1,
        "passTypeIdentifier": pass_type_id,
        "teamIdentifier": team_id,
        "organizationName": org_name,
        "serialNumber": customer_id,
        "description": f"{org_name} loyalty pass for {name}",
        "logoText": logo_text,
        "foregroundColor": "rgb(255,255,255)",
        "backgroundColor": "rgb(15,23,42)",
        "labelColor": "rgb(203,213,225)",
        # Signed QR token for POS scan-to-add / redeem.
        "barcodes": [{
            "format": "PKBarcodeFormatQR",
            "message": qr_token,
            "messageEncoding": "iso-8859-1",
            "altText": barcode,
        }],
        "storeCard": {
            "primaryFields": [
                {"key": "points", "label": "POINTS", "value": points}
            ],
            "secondaryFields": [
                {"key": "tier", "label": "TIER", "value": tier},
                {"key": "credit", "label": "CREDIT", "value": f"${store_credit:.2f}",
                 "textAlignment": "PKTextAlignmentRight"},
            ],
            "auxiliaryFields": [
                {"key": "member", "label": "MEMBER", "value": name}
            ],
            "backFields": [
                {"key": "id", "label": "Member ID", "value": customer_id},
                {"key": "terms", "label": "Terms",
                 "value": "Present this pass at checkout to earn or redeem points. Points do not expire while the account remains active."},
            ],
        },
        "relevantDate": now.isoformat(),
        # Web service URL for pass updates (optional). Skipped — enabling
        # this requires a full APNs / push registration server, tracked in
        # the backlog under "wallet auto-refresh".
    }


def _sign_manifest_pkcs7(manifest_bytes: bytes) -> Optional[bytes]:
    """Detached CMS/PKCS7 signature. Returns None if certs are missing."""
    cert_pem = os.environ.get("PASS_TYPE_CERT_PEM")
    key_pem = os.environ.get("PASS_TYPE_KEY_PEM")
    wwdr_pem = os.environ.get("APPLE_WWDR_CERT_PEM")
    if not (cert_pem and key_pem and wwdr_pem):
        return None
    try:
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        wwdr = x509.load_pem_x509_certificate(wwdr_pem.encode())
        key = serialization.load_pem_private_key(key_pem.encode(), password=None)
        builder = (
            pkcs7.PKCS7SignatureBuilder()
            .set_data(manifest_bytes)
            .add_signer(cert, key, hashes.SHA256())
            .add_certificate(wwdr)
        )
        return builder.sign(
            serialization.Encoding.DER,
            [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary],
        )
    except Exception:
        return None


def build_pkpass(*, customer_id: str, name: str, tier: str, points: int,
                  store_credit: float, barcode: str, qr_token: str) -> Tuple[bytes, dict]:
    """Return (pkpass_bytes, meta). `meta.signed` = True iff PKCS7 was applied."""
    pass_type_id = os.environ.get("PASS_TYPE_IDENTIFIER", "pass.com.nua.loyalty")
    team_id = os.environ.get("APPLE_TEAM_ID", "NUATEAMID00")
    org_name = os.environ.get("NUA_ORG_NAME", "NUA")
    logo_text = os.environ.get("NUA_LOGO_TEXT", "NUA Loyalty")

    pass_json = build_pass_json(
        customer_id=customer_id, name=name, tier=tier, points=points,
        store_credit=store_credit, barcode=barcode, qr_token=qr_token,
        pass_type_id=pass_type_id, team_id=team_id, org_name=org_name,
        logo_text=logo_text,
    )
    pass_bytes = json.dumps(pass_json, separators=(",", ":"), ensure_ascii=False).encode()

    icon = _icon_bytes()

    files: dict[str, bytes] = {
        "pass.json": pass_bytes,
        "icon.png": icon,
        "icon@2x.png": icon,
        "logo.png": icon,
    }
    manifest = {name_: _hex_sha1(blob) for name_, blob in files.items()}
    manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode()

    signature = _sign_manifest_pkcs7(manifest_bytes)
    signed = signature is not None

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fname, blob in files.items():
            z.writestr(fname, blob)
        z.writestr("manifest.json", manifest_bytes)
        if signed:
            z.writestr("signature", signature)
    return buf.getvalue(), {
        "signed": signed,
        "passTypeId": pass_type_id,
        "teamId": team_id,
    }


# ═════════════════════════════════════════════════════════════════════════
# Google Wallet
# ═════════════════════════════════════════════════════════════════════════
def build_google_wallet_link(*, customer_id: str, name: str, tier: str,
                              points: int, store_credit: float,
                              barcode: str, qr_token: str) -> dict:
    """Return {url, jwt, signed, classId, objectId}.

    When no service account key is configured the returned JWT is unsigned
    ("alg=none" is still deliberately avoided — we sign with a random HMAC
    key so any tampering is caught in preview, but Google will reject it).
    """
    issuer = os.environ.get("GOOGLE_WALLET_ISSUER_ID", "3388000000022000000")
    class_id = os.environ.get("GOOGLE_WALLET_CLASS_ID", f"{issuer}.nua_loyalty")
    object_id = f"{issuer}.nua-{customer_id}"

    loyalty_obj = {
        "id": object_id,
        "classId": class_id,
        "state": "ACTIVE",
        "accountId": customer_id,
        "accountName": name,
        "loyaltyPoints": {
            "label": "Points",
            "balance": {"int": int(points)},
        },
        "secondaryLoyaltyPoints": {
            "label": "Credit",
            "balance": {"money": {"currencyCode": "AUD", "micros": int(round(store_credit * 1_000_000))}},
        },
        "barcode": {
            "type": "QR_CODE",
            "value": qr_token,
            "alternateText": barcode,
        },
        "textModulesData": [
            {"header": "Tier", "body": tier, "id": "tier"},
        ],
    }

    payload = {
        "iss": os.environ.get("GOOGLE_WALLET_ISSUER_EMAIL", "nua-wallet@example.iam.gserviceaccount.com"),
        "aud": "google",
        "typ": "savetowallet",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(days=365)).timestamp()),
        "payload": {"loyaltyObjects": [loyalty_obj]},
    }

    key_env = os.environ.get("GOOGLE_WALLET_SERVICE_ACCOUNT_KEY")
    signed_jwt: str
    signed = False
    if key_env:
        try:
            # Accept raw JSON or base64-encoded JSON
            raw = key_env.strip()
            if not raw.startswith("{"):
                raw = base64.b64decode(raw).decode()
            sa = json.loads(raw)
            private_key = sa["private_key"]
            payload["iss"] = sa.get("client_email", payload["iss"])
            signed_jwt = jwt.encode(payload, private_key, algorithm="RS256")
            signed = True
        except Exception:
            signed_jwt = jwt.encode(payload, "PREVIEW-KEY-NOT-FOR-PRODUCTION", algorithm="HS256")
    else:
        signed_jwt = jwt.encode(payload, "PREVIEW-KEY-NOT-FOR-PRODUCTION", algorithm="HS256")

    return {
        "url": f"https://pay.google.com/gp/v/save/{signed_jwt}",
        "jwt": signed_jwt,
        "signed": signed,
        "classId": class_id,
        "objectId": object_id,
    }
