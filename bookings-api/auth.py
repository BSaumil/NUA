import hashlib
import os
import secrets
import time

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database import db

bearer = HTTPBearer(auto_error=False)

# Requests per minute by billing tier — sandbox (test) keys get a flat low cap.
TIER_LIMITS = {"standard": 120, "growth": 600, "enterprise": 3000}
TEST_LIMIT = 30


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_key(test: bool = False) -> str:
    prefix = "nbk_test_" if test else "nbk_live_"
    return prefix + secrets.token_urlsafe(24)


class _RateLimiter:
    """Per-partner sliding window. In-memory is fine: one process per region,
    and the point is abuse protection tiered by contract, not exact accounting
    (usage billing is metered separately in usage.py)."""

    def __init__(self):
        self.buckets: dict[str, list[float]] = {}

    def allow(self, key: str, limit: int) -> bool:
        now = time.time()
        window = self.buckets.setdefault(key, [])
        window[:] = [t for t in window if now - t < 60]
        if len(window) >= limit:
            return False
        window.append(now)
        return True


rate_limiter = _RateLimiter()


async def get_partner(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    """Resolve the calling partner from its bearer API key. Every /v1 route
    depends on this — there is no unauthenticated surface."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing API key")
    raw = credentials.credentials
    key_hash = hash_key(raw)
    partner = await db.partners.find_one({"api_key_hash": key_hash}, {"_id": 0})
    test_mode = False
    if not partner:
        partner = await db.partners.find_one({"test_key_hash": key_hash}, {"_id": 0})
        if partner:
            test_mode = True
    if not partner:
        raise HTTPException(status_code=401, detail="Invalid API key")

    limit = TEST_LIMIT if test_mode else TIER_LIMITS.get(partner.get("billing_tier", "standard"), 120)
    if not rate_limiter.allow(f"{partner['id']}:{'t' if test_mode else 'l'}", limit):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for your plan tier")

    partner["test_mode"] = test_mode
    return partner


async def require_platform_admin(request: Request) -> None:
    """Platform-operator surface (partner provisioning, usage reports). Guarded
    by a deploy-time secret, never by partner keys."""
    admin_key = os.environ.get("BOOKINGS_ADMIN_KEY", "")
    provided = request.headers.get("X-Admin-Key", "")
    if not admin_key or not secrets.compare_digest(provided, admin_key):
        raise HTTPException(status_code=403, detail="Platform admin key required")
