"""
Stamped-CRUD helpers — the ONE place we apply the audit stamp before
writing to Mongo.

Contract
────────
• `stamped_insert(coll, doc)` — writes a *new* document with createdBy /
  createdAt / device / ip / businessId / locationId set, and version=1.
  Emits an "audit_service.log_event" of action='created'.

• `stamped_update(coll, {id}, patch)` — reads the current doc, snapshots
  it into `entity_versions`, bumps `version`, sets updatedBy/updatedAt,
  and emits action='updated'.

• `soft_delete(coll, entity_id)` — sets deletedAt / deletedBy without
  removing the row. Emits action='deleted'.

• `hard_delete(coll, entity_id)` — physical remove + purge of history
  (GDPR right-to-be-forgotten). Emits action='deleted' with tag=purge.

Legacy documents in Mongo may not have any audit fields. That's OK — we
stamp them opportunistically on the next update.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from middleware.actor_context import get_actor_context
from services import audit_service
from database import db


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp_new(doc: Dict[str, Any]) -> Dict[str, Any]:
    ctx = get_actor_context()
    doc.setdefault("createdBy", ctx.get("email") or "system")
    doc.setdefault("createdAt", _now_iso())
    doc.setdefault("updatedBy", doc["createdBy"])
    doc.setdefault("updatedAt", doc["createdAt"])
    doc.setdefault("device", ctx.get("device"))
    doc.setdefault("ip", ctx.get("ip"))
    # NOT setdefault: every BaseEntity-derived model (Product, etc.) declares
    # businessId/locationId as real fields defaulting to None, so a caller
    # that builds a full model instance and passes model.dict() here already
    # has an explicit "businessId": None key in the dict — setdefault is a
    # no-op against an EXISTING key, even one whose value is None, so the
    # actor's real businessId never got applied. Every document created
    # through a caller that shaped its dict from such a model (confirmed:
    # routes/products.py's create_product, likely others) was silently
    # stamped with businessId=None regardless of who created it or which
    # business they belonged to — universally visible to every tenant via
    # tenant_scope_filter's "missing/null businessId = visible to everyone"
    # backward-compat default. A caller that deliberately supplies a real,
    # truthy businessId (e.g. an explicit cross-tenant/system write) still
    # wins; only a falsy one is overwritten.
    if not doc.get("businessId"):
        doc["businessId"] = ctx.get("businessId")
    if not doc.get("locationId"):
        doc["locationId"] = ctx.get("locationId")
    doc.setdefault("version", 1)
    doc.setdefault("deletedAt", None)
    return doc


async def stamped_insert(coll_name: str, doc: Dict[str, Any], *, entity_type: Optional[str] = None) -> Dict[str, Any]:
    doc = _stamp_new(doc)
    await getattr(db, coll_name).insert_one(dict(doc))
    doc.pop("_id", None)
    await audit_service.log_event(
        entity_type=entity_type or coll_name,
        entity_id=doc.get("id"),
        action="created",
        after=doc,
    )
    return doc


async def stamped_update(coll_name: str, entity_id: str, patch: Dict[str, Any], *,
                         entity_type: Optional[str] = None,
                         id_field: str = "id") -> Optional[Dict[str, Any]]:
    coll = getattr(db, coll_name)
    before = await coll.find_one({id_field: entity_id}, {"_id": 0})
    if not before:
        return None
    ctx = get_actor_context()

    # Snapshot the current version into entity_versions.
    try:
        await db.entity_versions.insert_one({
            "entityType": entity_type or coll_name,
            "entityId": entity_id,
            "version": before.get("version") or 1,
            "snapshot": {k: v for k, v in before.items() if k != "_id"},
            "capturedAt": _now_iso(),
            "capturedBy": ctx.get("email"),
        })
    except Exception:
        pass

    # Build the final update payload.
    upd = dict(patch)
    upd["updatedBy"] = ctx.get("email") or "system"
    upd["updatedAt"] = _now_iso()
    upd["version"] = (before.get("version") or 1) + 1
    if before.get("createdAt") is None:
        # Opportunistic legacy stamp
        upd.setdefault("createdBy", before.get("createdBy") or upd["updatedBy"])
        upd.setdefault("createdAt", upd["updatedAt"])
        upd.setdefault("device", ctx.get("device"))
        upd.setdefault("ip", ctx.get("ip"))

    await coll.update_one({id_field: entity_id}, {"$set": upd})
    after = await coll.find_one({id_field: entity_id}, {"_id": 0})

    await audit_service.log_event(
        entity_type=entity_type or coll_name,
        entity_id=entity_id,
        action="updated",
        before=before,
        after=after,
    )
    return after


async def soft_delete(coll_name: str, entity_id: str, *,
                      entity_type: Optional[str] = None,
                      id_field: str = "id") -> Optional[Dict[str, Any]]:
    coll = getattr(db, coll_name)
    ctx = get_actor_context()
    r = await coll.update_one({id_field: entity_id}, {"$set": {
        "deletedAt": _now_iso(),
        "deletedBy": ctx.get("email") or "system",
    }})
    if r.matched_count == 0:
        return None
    after = await coll.find_one({id_field: entity_id}, {"_id": 0})
    await audit_service.log_event(
        entity_type=entity_type or coll_name,
        entity_id=entity_id,
        action="deleted",
        after=after,
        tags=["soft_delete"],
    )
    return after


async def hard_delete(coll_name: str, entity_id: str, *,
                      entity_type: Optional[str] = None,
                      id_field: str = "id") -> bool:
    """GDPR-style purge — physical remove + history purge."""
    coll = getattr(db, coll_name)
    before = await coll.find_one({id_field: entity_id}, {"_id": 0})
    if not before:
        return False
    await coll.delete_one({id_field: entity_id})
    await db.entity_versions.delete_many({"entityType": entity_type or coll_name, "entityId": entity_id})
    await audit_service.log_event(
        entity_type=entity_type or coll_name,
        entity_id=entity_id,
        action="deleted",
        before=before,
        tags=["hard_delete", "gdpr_purge"],
        severity="warning",
    )
    return True


async def get_history(entity_type: str, entity_id: str, *, business_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
    versions = await db.entity_versions.find(
        {"entityType": entity_type, "entityId": entity_id},
        {"_id": 0},
    ).sort("version", -1).limit(limit).to_list(limit)
    audit = await audit_service.list_events(business_id=business_id, entity_type=entity_type, entity_id=entity_id, limit=limit)
    return {"versions": versions, "audit": audit}


async def restore_version(coll_name: str, entity_type: str, entity_id: str, version: int) -> Optional[Dict[str, Any]]:
    snap = await db.entity_versions.find_one(
        {"entityType": entity_type, "entityId": entity_id, "version": version},
        {"_id": 0},
    )
    if not snap:
        return None
    payload = snap["snapshot"]
    # Restore everything except id/createdBy/createdAt.
    protected = {k: payload[k] for k in ("id", "createdBy", "createdAt") if k in payload}
    restored = await stamped_update(
        coll_name, entity_id,
        {k: v for k, v in payload.items() if k not in protected},
        entity_type=entity_type,
    )
    # Log restore separately
    await audit_service.log_event(
        entity_type=entity_type,
        entity_id=entity_id,
        action="restored",
        after=restored,
        memo=f"Restored from version {version}",
        severity="notice",
    )
    return restored
