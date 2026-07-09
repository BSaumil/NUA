"""
Universal audit log — every mutation on a tracked entity writes an
`AuditEvent` here. It's write-only from the app's perspective; the
audit UI reads it.
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from database import db
from middleware.actor_context import get_actor_context
import uuid
import logging

logger = logging.getLogger(__name__)


async def log_event(
    *,
    entity_type: str,
    entity_id: Optional[str],
    action: str,               # created | updated | deleted | restored | executed
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
    memo: Optional[str] = None,
    severity: str = "info",    # info | notice | warning | high
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    ctx = get_actor_context()
    doc = {
        "id": str(uuid.uuid4()),
        "entityType": entity_type,
        "entityId": entity_id,
        "action": action,
        "actor": ctx.get("email") or "system",
        "role": ctx.get("role"),
        "device": ctx.get("device"),
        "ip": ctx.get("ip"),
        "businessId": ctx.get("businessId"),
        "locationId": ctx.get("locationId"),
        "before": before,
        "after": after,
        "memo": memo,
        "severity": severity,
        "tags": tags or [],
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.audit_events.insert_one(dict(doc))
    except Exception as e:
        logger.warning(f"[audit] insert failed for {entity_type}:{entity_id} — {e}")
    return doc


async def list_events(
    *,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {}
    if entity_type: q["entityType"] = entity_type
    if entity_id: q["entityId"] = entity_id
    if action: q["action"] = action
    if actor: q["actor"] = actor
    rows = await db.audit_events.find(q, {"_id": 0}).sort("ts", -1).limit(limit).to_list(limit)
    return rows
