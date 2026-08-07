"""
Universal audit / history / restore endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from deps import get_user, require_owner_or_manager, require_owner
from services import audit_service, entity_service
from database import db

router = APIRouter(prefix="/audit")

# entity_type (what audit events are tagged with, e.g. from stamped_update's
# entity_type= kwarg) -> the actual Mongo collection name. Restoring a
# version needs the real collection, and the two names diverge often enough
# (singular vs. plural, "category" -> "categories") that guessing it
# client-side would be a good way to silently restore into the wrong
# collection. Callers that already know the right collection can still pass
# ?collection= explicitly to override this.
ENTITY_TYPE_TO_COLLECTION = {
    "customer": "customers",
    "product": "products",
    "category": "categories",
    "stock_unit": "stock_units",
    "sell_variant": "sell_variants",
    "wastage_event": "wastage_events",
    "approval": "approvals",
    "open_container": "open_containers",
    "journal_entry": "journal_entries",
    "ash_plan": "ash_plans",
    "cash_drawer": "cash_drawers",
    "kitchen_order": "kitchen_orders",
    "stocktake_reconcile": "stocktake_reconciles",
    "transaction": "transactions",
    "loyalty_fraud_flag": "loyalty_fraud_flags",
}


@router.get("/events")
async def list_events(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    limit: int = 200,
    user: dict = Depends(get_user),
):
    return await audit_service.list_events(
        business_id=user.get("businessId") or "default",
        entity_type=entity_type, entity_id=entity_id,
        action=action, actor=actor, limit=limit,
    )


@router.get("/history/{entity_type}/{entity_id}")
async def history(entity_type: str, entity_id: str, user: dict = Depends(get_user)):
    return await entity_service.get_history(entity_type, entity_id, business_id=user.get("businessId") or "default")


@router.post("/restore/{entity_type}/{entity_id}/{version}")
async def restore(entity_type: str, entity_id: str, version: int,
                  collection: Optional[str] = Query(None),
                  _: dict = Depends(require_owner_or_manager)):
    coll_name = collection or ENTITY_TYPE_TO_COLLECTION.get(entity_type)
    if not coll_name:
        raise HTTPException(400, f"Unknown entity_type '{entity_type}' — pass ?collection= explicitly")
    r = await entity_service.restore_version(coll_name, entity_type, entity_id, version)
    if not r:
        raise HTTPException(404, "Version not found")
    return r


@router.delete("/purge/{entity_type}/{entity_id}")
async def gdpr_purge(entity_type: str, entity_id: str,
                     collection: str = Query(...),
                     _: dict = Depends(require_owner)):
    """Owner-only right-to-be-forgotten. Removes doc + history."""
    ok = await entity_service.hard_delete(collection, entity_id, entity_type=entity_type)
    if not ok:
        raise HTTPException(404, "Entity not found")
    return {"purged": True}


@router.get("/summary")
async def summary(user: dict = Depends(get_user)):
    """Quick actor / action mix over the recent audit stream."""
    business_id = user.get("businessId") or "default"
    match = {"$match": {"businessId": business_id}}
    pipeline_action = [match, {"$group": {"_id": "$action", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    pipeline_type = [match, {"$group": {"_id": "$entityType", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": 20}]
    pipeline_actor = [match, {"$group": {"_id": "$actor", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": 10}]
    return {
        "byAction": await db.audit_events.aggregate(pipeline_action).to_list(20),
        "byEntity": await db.audit_events.aggregate(pipeline_type).to_list(20),
        "byActor": await db.audit_events.aggregate(pipeline_actor).to_list(10),
        "total": await db.audit_events.count_documents({"businessId": business_id}),
    }
