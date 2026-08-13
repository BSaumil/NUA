"""Coinbase Commerce client — accepts Bitcoin and USDC at the POS counter.

Real HTTP calls to Coinbase Commerce's REST API (https://commerce.coinbase.com),
gated by COINBASE_COMMERCE_API_KEY — same "honest status" posture as every
other money integration in this codebase (Stripe checkout, NUA Connect's
Square/CDR-bank connectors): never claims to be configured or connected when
it isn't, so a venue that hasn't set up a real merchant account gets a clear
"not configured" answer instead of a fake success.

Coinbase Commerce is a hosted checkout: create a charge, send the guest to
`hosted_url`, they pay in whichever supported asset they choose. Bitcoin
settles on-chain or, when the guest's wallet supports it, over Lightning for
near-instant confirmation — which path is used is decided by Coinbase
Commerce and the guest's wallet, not something this integration controls.
USDC is offered specifically so a bill's value doesn't drift while payment
confirms, unlike a volatile asset.
"""
from __future__ import annotations
import hashlib
import hmac
import os
from typing import Any, Dict

import httpx

API_BASE = "https://api.commerce.coinbase.com"
API_VERSION = "2018-03-22"


class CoinbaseCommerceError(Exception):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("COINBASE_COMMERCE_API_KEY"))


def _headers() -> Dict[str, str]:
    return {
        "X-CC-Api-Key": os.environ["COINBASE_COMMERCE_API_KEY"],
        "X-CC-Version": API_VERSION,
        "Content-Type": "application/json",
    }


async def create_charge(*, amount: float, currency: str, name: str, description: str,
                         redirect_url: str, cancel_url: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    if not is_configured():
        raise CoinbaseCommerceError("Coinbase Commerce not configured")
    body = {
        "name": name,
        "description": description,
        "pricing_type": "fixed_price",
        "local_price": {"amount": f"{amount:.2f}", "currency": currency.upper()},
        "redirect_url": redirect_url,
        "cancel_url": cancel_url,
        "metadata": metadata,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{API_BASE}/charges", json=body, headers=_headers())
    if r.status_code >= 400:
        raise CoinbaseCommerceError(f"charge create failed: {r.status_code} {r.text}")
    return r.json()["data"]


async def get_charge(code: str) -> Dict[str, Any]:
    if not is_configured():
        raise CoinbaseCommerceError("Coinbase Commerce not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{API_BASE}/charges/{code}", headers=_headers())
    if r.status_code >= 400:
        raise CoinbaseCommerceError(f"charge lookup failed: {r.status_code} {r.text}")
    return r.json()["data"]


def charge_status(charge: Dict[str, Any]) -> str:
    """Collapse Coinbase Commerce's timeline (NEW/PENDING/COMPLETED/RESOLVED/
    EXPIRED/CANCELED/UNRESOLVED) into the same pending|paid|expired
    vocabulary the Stripe checkout status endpoint already uses, so the
    frontend doesn't need a second status model to branch on."""
    statuses = {t.get("status") for t in (charge.get("timeline") or [])}
    if statuses & {"COMPLETED", "RESOLVED"}:
        return "paid"
    if statuses & {"EXPIRED", "CANCELED"}:
        return "expired"
    return "pending"


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """Coinbase Commerce signs each webhook delivery with
    HMAC-SHA256(shared_secret, raw_body), sent as the X-CC-Webhook-Signature
    header. No shared secret configured means no delivery can ever verify —
    fail closed, not open."""
    secret = os.environ.get("COINBASE_COMMERCE_WEBHOOK_SECRET", "")
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
