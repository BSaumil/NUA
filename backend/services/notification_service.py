"""
Universal notification service.

Everything downstream (Loyalty earn events, Kitchen fire/ready pings,
Ash campaign proposals, approvals) writes through `send()`.

Delivery today
──────────────
• In-app bell — `db.notifications` fanned out by (email | role | topic).
• (Wire-ready) SMS / email — call `notify_out` which is a shim over the
  abstraction in utils/notifications.py; if credentials are absent it
  logs and no-ops, so the pipeline is always safe to call.

Model
─────
{ id, recipient: {email?, role?, topic?}, kind, title, body, link,
  data, severity, readAt, createdAt }

kind vocabulary  (keep small — the UI colours from this)
  loyalty | kitchen | approval | marketing | ash | referral | system
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from database import db
from services.retention import notification_expiry
import uuid
import logging

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def send(
    *,
    kind: str,
    title: str,
    body: str = "",
    email: Optional[str] = None,
    role: Optional[str] = None,
    topic: Optional[str] = None,
    link: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    severity: str = "info",
) -> Dict[str, Any]:
    """Fan out ONE notification. At least one of email/role/topic is required
    so we always know who should see it. `role` = 'owner' | 'manager' |
    'cashier' | 'server' | 'kitchen'; `topic` for pub-sub-style channels
    like 'kitchen.station.grill'."""
    if not any([email, role, topic]):
        raise ValueError("notification requires email, role, or topic")
    doc = {
        "id": str(uuid.uuid4()),
        "recipient": {"email": email, "role": role, "topic": topic},
        "kind": kind,
        "title": title,
        "body": body,
        "link": link,
        "data": data or {},
        "severity": severity,
        "readAt": None,
        "createdAt": _now(),
        # 90 days by default (services/retention.py) — long enough to look
        # back on a season, not a permanent record.
        "expiresAt": notification_expiry(),
    }
    await db.notifications.insert_one(dict(doc))
    return doc


async def list_for(email: str, role: Optional[str] = None,
                    unread_only: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
    conditions = [{"recipient.email": email}]
    if role:
        conditions.append({"recipient.role": role})
    # Owners are super-users — they see notifications routed to any role
    # so a marketing-scoped alert still lands on the owner's dashboard when
    # there's no dedicated marketing user account.
    if role == "owner":
        conditions.append({"recipient.role": {"$in": ["marketing", "manager", "server", "kitchen"]}})
    q: Dict[str, Any] = {"$or": conditions}
    if unread_only:
        q["readAt"] = None
    return await db.notifications.find(q, {"_id": 0}).sort("createdAt", -1).limit(limit).to_list(limit)


async def mark_read(notification_id: str, email: str) -> bool:
    r = await db.notifications.update_one(
        {"id": notification_id, "$or": [{"recipient.email": email},
                                          {"recipient.email": None}]},
        {"$set": {"readAt": _now()}},
    )
    return r.matched_count > 0


async def mark_all_read(email: str, role: Optional[str] = None) -> int:
    conditions = [{"recipient.email": email}]
    if role:
        conditions.append({"recipient.role": role})
    r = await db.notifications.update_many(
        {"$or": conditions, "readAt": None},
        {"$set": {"readAt": _now()}},
    )
    return r.modified_count


async def unread_count(email: str, role: Optional[str] = None) -> int:
    conditions = [{"recipient.email": email}]
    if role:
        conditions.append({"recipient.role": role})
    if role == "owner":
        conditions.append({"recipient.role": {"$in": ["marketing", "manager", "server", "kitchen"]}})
    return await db.notifications.count_documents({"$or": conditions, "readAt": None})
