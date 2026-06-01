"""ABR (Australian Business Register) ABN Lookup integration.

Official endpoint: https://abr.business.gov.au/json/AbnDetails.aspx
Requires a `GUID` obtained from registering at https://abr.business.gov.au/Tools/WebServices
The GUID is sent as the `authenticationGuid` query parameter.

Set the GUID via env var: ABR_GUID
"""
from __future__ import annotations
import os
import re
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)
ABR_URL = "https://abr.business.gov.au/json/AbnDetails.aspx"


def _strip(abn: str) -> str:
    """Remove spaces, dashes, and non-digits from ABN input."""
    return re.sub(r"\D", "", str(abn or ""))


def checksum_valid(abn: str) -> bool:
    """ABN MOD-89 checksum. Last gate before contacting ABR. Not a replacement
    for the live ABR call but rejects obvious typos with zero network overhead."""
    s = _strip(abn)
    if len(s) != 11 or not s.isdigit():
        return False
    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    digits = [int(c) for c in s]
    digits[0] -= 1
    total = sum(d * w for d, w in zip(digits, weights))
    return total % 89 == 0


async def lookup_abn(abn: str, guid: Optional[str] = None) -> dict:
    """Live ABR call. Returns a normalized dict on success or raises ValueError
    with a precise reason. The caller should map ValueError → 422 / 400."""
    s = _strip(abn)
    if not checksum_valid(s):
        raise ValueError("ABN failed local MOD-89 checksum")
    g = guid or os.environ.get("ABR_GUID", "").strip()
    if not g:
        # We refuse to fall back silently — the user explicitly said checksum
        # alone is NOT acceptable. Raise so onboarding can show the right error.
        raise RuntimeError(
            "ABR_GUID not configured. Register at "
            "https://abr.business.gov.au/Tools/WebServices and add ABR_GUID to backend/.env"
        )
    params = {"abn": s, "callback": "", "authenticationGuid": g}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(ABR_URL, params=params)
        except httpx.HTTPError as e:
            raise RuntimeError(f"ABR network error: {e}") from e
    if r.status_code != 200:
        raise RuntimeError(f"ABR HTTP {r.status_code}")
    # ABR sometimes wraps JSON in `callback(...)`; strip if present
    body = r.text.strip()
    if body.startswith("callback(") and body.endswith(")"):
        body = body[9:-1]
    import json
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"ABR returned non-JSON: {body[:120]}") from e
    if data.get("Message"):
        raise ValueError(f"ABR: {data['Message']}")
    if data.get("AbnStatus", "").lower() not in ("active", "current"):
        raise ValueError(f"ABN status is {data.get('AbnStatus', 'unknown')}, not Active")
    return {
        "abn": s,
        "entityName": data.get("EntityName") or data.get("BusinessName") or "",
        "entityType": data.get("EntityTypeName", ""),
        "status": data.get("AbnStatus", ""),
        "statusEffectiveFrom": data.get("AbnStatusEffectiveFrom", ""),
        "gstRegistered": bool(data.get("Gst")),
        "state": data.get("AddressState", ""),
        "postcode": data.get("AddressPostcode", ""),
        "raw": data,
    }
