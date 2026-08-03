"""What tells you the backend is actually okay, and what tells you why it isn't.

Two audiences: a deep health check for uptime monitors and load balancers
(anonymous, deliberately thin on detail), and a recent-errors list for the
owner, who has no other way to see that something has been failing quietly
since 3am.
"""
from fastapi import APIRouter, Depends

from database import db
from deps import require_owner_or_manager
from services.observability import check_health
from services import retention

router = APIRouter()


@router.get("/health")
@router.get("/healthz")
async def health():
    return await check_health()


@router.get("/ops/errors")
async def recent_errors(limit: int = 50, _: dict = Depends(require_owner_or_manager)):
    """The last N unhandled exceptions, newest first.

    This is the thing that used to only exist in whatever terminal happened to
    be tailing stdout at the moment it happened — invisible to an owner with
    no shell access, and gone the moment that terminal closed.
    """
    limit = max(1, min(limit, 200))
    rows = await db.error_log.find({}, {"_id": 0}).sort("at", -1).to_list(limit)
    for r in rows:
        at = r.get("at")
        r["at"] = at.isoformat() if hasattr(at, "isoformat") else at
        exp = r.get("expiresAt")
        r["expiresAt"] = exp.isoformat() if hasattr(exp, "isoformat") else exp
    return {"errors": rows, "count": len(rows)}


@router.get("/ops/retention")
async def retention_status(_: dict = Depends(require_owner_or_manager)):
    """What gets auto-deleted, how long it's kept, and why — deliberately
    limited to the ephemeral collections (kiosk carts, notifications, login
    lockouts). Financial and audit records are never on this list."""
    return {"policy": await retention.status()}


@router.post("/ops/retention/purge")
async def retention_purge(_: dict = Depends(require_owner_or_manager)):
    """Run the purge immediately rather than waiting for Mongo's own TTL
    sweep. Only ever removes what was already past its expiry."""
    return {"deleted": await retention.purge_now()}
