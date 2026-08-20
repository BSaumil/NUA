"""
Autonomous Marketing daily digest.

Turns 'go check every draft campaign' into a single owner ritual:
- GET  /marketing/digest              — today's pending drafts + summary card
- POST /marketing/digest/approve-all  — send everything (or a curated subset)
- POST /marketing/digest/deliver      — post the digest as a notification for the
                                        owner (called by the daily nua_scheduler
                                        or manually from the UI)

Design:
- Idempotent per day: a digest for today is only delivered once per business.
- Never sends a campaign already on hold — those need explicit unhold.
- Reuses the existing _execute_campaign_send() so voucher-issuance + email
  path stays identical to the manual Send button.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional, List
from database import db
from routes.auth import get_current_user

router = APIRouter(prefix="/marketing/digest", tags=["marketing-digest"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


async def _pending_drafts(business_id: Optional[str] = None) -> List[dict]:
    q: dict = {"status": "draft"}
    if business_id:
        q["businessId"] = business_id
    rows = await db.marketing_campaigns.find(q, {"_id": 0}).sort("createdAt", -1).limit(50).to_list(50)
    return rows


@router.get("")
async def get_digest(request: Request):
    """Return today's pending drafts + summary the owner can approve at a glance."""
    user = await get_current_user(request)
    if user.get("role") not in ("owner", "manager"):
        raise HTTPException(403, "Owner or manager only")
    business_id = user.get("businessId")
    drafts = await _pending_drafts(business_id)
    total_reach = sum(int(d.get("recipients") or 0) for d in drafts)
    return {
        "date": _today_key(),
        "count": len(drafts),
        "totalReach": total_reach,
        "drafts": drafts,
        "notes": "Approve all to send everything, or open each to Edit / Hold / Send individually.",
    }


@router.post("/approve-all")
async def approve_all(request: Request, payload: Optional[dict] = None):
    """Send every draft campaign in one owner action. Held drafts are skipped
    on purpose — the owner must explicitly unhold them.

    Optional payload:
      { "onlyIds": ["MKT-abc", "MKT-def"] }  → send just those.
    """
    user = await get_current_user(request)
    if user.get("role") not in ("owner", "manager"):
        raise HTTPException(403, "Owner or manager only")

    # Late import to avoid a circular reference with v25_suite.
    from routes.v25_suite import _execute_campaign_send  # type: ignore

    business_id = user.get("businessId")
    drafts = await _pending_drafts(business_id)
    only_ids = set((payload or {}).get("onlyIds") or [])
    if only_ids:
        drafts = [d for d in drafts if d.get("id") in only_ids]

    results = {"sent": [], "skipped": [], "failed": []}
    for d in drafts:
        try:
            r = await _execute_campaign_send(d)
            if r and r.get("status") == "sent":
                results["sent"].append({"id": d["id"], "recipients": r.get("sent", 0)})
            else:
                results["skipped"].append({"id": d["id"], "reason": (r or {}).get("reason", "unknown")})
        except Exception as exc:
            results["failed"].append({"id": d["id"], "error": str(exc)[:200]})
    # Persist a tiny audit trail on the digest doc — helpful for the tile that
    # shows 'approved 4/4 at 08:12'.
    await db.marketing_digest_log.update_one(
        {"date": _today_key(), "businessId": business_id},
        {"$set": {
            "approvedAt": _now_iso(),
            "approvedBy": user.get("email"),
            "results": results,
        }},
        upsert=True,
    )
    return {"date": _today_key(), **results, "totalSent": len(results["sent"])}


@router.post("/deliver")
async def deliver_digest(request: Request):
    """Materialise today's digest as an owner-facing notification. Idempotent
    per business per day — safe to call from the daily scheduler."""
    user = await get_current_user(request)
    if user.get("role") not in ("owner",):
        raise HTTPException(403, "Owner only")
    business_id = user.get("businessId")
    drafts = await _pending_drafts(business_id)
    if not drafts:
        return {"delivered": False, "reason": "no drafts pending"}
    existing = await db.marketing_digest_log.find_one(
        {"date": _today_key(), "businessId": business_id, "delivered": True}
    )
    if existing:
        return {"delivered": False, "reason": "already delivered today"}
    total_reach = sum(int(d.get("recipients") or 0) for d in drafts)
    notif = {
        "userId": user.get("id"),
        "kind": "marketing_digest",
        "title": f"{len(drafts)} campaign{'s' if len(drafts) != 1 else ''} queued for today",
        "body": f"Est. reach {total_reach:,} customers. Approve all with one tap on the dashboard.",
        "cta": {"path": "/auto-marketing", "label": "Review"},
        "read": False,
        "createdAt": _now_iso(),
    }
    await db.notifications.insert_one(notif)
    await db.marketing_digest_log.update_one(
        {"date": _today_key(), "businessId": business_id},
        {"$set": {"delivered": True, "deliveredAt": _now_iso(),
                  "draftCount": len(drafts), "totalReach": total_reach}},
        upsert=True,
    )
    return {"delivered": True, "count": len(drafts), "totalReach": total_reach}
