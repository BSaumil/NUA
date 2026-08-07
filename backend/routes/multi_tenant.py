from fastapi import APIRouter, HTTPException, Depends
from deps import get_user, require_owner
from database import db
from typing import Optional
import re
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/business")

# ============ MULTI-BUSINESS / MULTI-TENANT ============


async def _unique_slug(name: str) -> str:
    """URL-safe handle for the public online-ordering storefront
    (/order-online?business=<slug>) — friendlier than the raw BIZ-xxxxxxxx id.
    Not globally enforced at the DB level (no unique index; this is a
    small, owner-driven collection), just checked-and-retried here so two
    businesses named the same thing don't collide."""
    base = re.sub(r"[^a-z0-9]+", "-", (name or "business").lower()).strip("-") or "business"
    slug = base
    n = 2
    while await db.businesses.find_one({"slug": slug}, {"_id": 1}):
        slug = f"{base}-{n}"
        n += 1
    return slug

@router.post("/create")
async def create_business(data: dict, user: dict = Depends(require_owner)):
    """Create a new business (Owner only)"""

    business = {
        "id": f"BIZ-{str(uuid.uuid4())[:8].upper()}",
        "slug": await _unique_slug(data.get("name", "")),
        "name": data.get("name", ""),
        "type": data.get("type", "restaurant"),  # restaurant, cafe, bar, catering
        "abn": data.get("abn", ""),
        "address": data.get("address", ""),
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "timezone": data.get("timezone", "Australia/Sydney"),
        "currency": data.get("currency", "AUD"),
        "taxRate": data.get("taxRate", 10),
        "ownerId": user["id"],
        "status": "active",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "settings": {
            "autoGratuity": data.get("autoGratuity", 0),
            "serviceCharge": data.get("serviceCharge", 0),
            "bookingEnabled": True,
            "tableOrderingEnabled": True,
        }
    }
    await db.businesses.insert_one(business)
    business.pop("_id", None)
    return business

@router.get("/list")
async def list_businesses(user: dict = Depends(require_owner)):
    """List all businesses for current owner"""
    businesses = await db.businesses.find({"ownerId": user["id"]}, {"_id": 0}).to_list(100)
    return businesses

@router.get("/{business_id}")
async def get_business(business_id: str, _: dict = Depends(get_user)):
    business = await db.businesses.find_one({"id": business_id}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business

@router.put("/{business_id}")
async def update_business(business_id: str, data: dict, _: dict = Depends(require_owner)):
    allowed = {"name", "type", "abn", "address", "phone", "email", "timezone", "currency", "taxRate", "settings"}
    update_data = {k: v for k, v in data.items() if k in allowed}
    result = await db.businesses.find_one_and_update(
        {"id": business_id}, {"$set": update_data}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Business not found")
    result.pop("_id", None)
    return result

@router.get("/{business_id}/export")
async def export_business_data(business_id: str, collection: Optional[str] = None, _: dict = Depends(require_owner)):
    """Export all data for a specific business (Owner only)"""

    business = await db.businesses.find_one({"id": business_id}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    collections_to_export = ["products", "transactions", "customers", "reservations",
                              "kitchen_orders", "expenses", "suppliers", "feedback",
                              "members", "vouchers", "automation_rules"]

    if collection and collection in collections_to_export:
        collections_to_export = [collection]

    export_data = {"business": business, "exportedAt": datetime.now(timezone.utc).isoformat()}
    for coll_name in collections_to_export:
        coll = db[coll_name]
        docs = await coll.find({"businessId": business_id}, {"_id": 0}).to_list(10000)
        if not docs:
            docs = await coll.find({}, {"_id": 0}).to_list(10000)
        export_data[coll_name] = {"count": len(docs), "data": docs}

    return export_data

@router.get("/{business_id}/summary")
async def get_business_summary(business_id: str, _: dict = Depends(require_owner)):
    """Quick summary stats for a business"""

    # Scoped to this business_id specifically (not the caller's own token
    # businessId — an owner with multiple businesses needs to pull summaries
    # for businesses other than the one they're currently acting as), with
    # the same fail-open-to-untagged-legacy-data semantics as
    # tenant_scope_filter so a not-yet-backfilled deployment still shows
    # its (single, real) numbers instead of zero.
    biz_or_untagged = {"$or": [{"businessId": business_id}, {"businessId": None}, {"businessId": {"$exists": False}}]}
    txns = await db.transactions.find(biz_or_untagged, {"_id": 0}).to_list(10000)
    products = await db.products.find(biz_or_untagged, {"_id": 0}).to_list(1000)
    customers = await db.customers.find(biz_or_untagged, {"_id": 0}).to_list(10000)
    members = await db.members.find(biz_or_untagged, {"_id": 0}).to_list(10000)
    staff = await db.auth_users.find({"businessId": business_id}, {"_id": 0, "password_hash": 0}).to_list(100)
    # Online orders have no businessId field at all yet — there's no
    # per-business storefront/slug for a guest to pick which business
    # they're ordering from, so biz_or_untagged matches every online order
    # on the deployment here, same as it would for any other untagged
    # collection. On a real multi-business deployment these counts are
    # deployment-wide until online ordering gets a businessId of its own.
    online_orders = await db.online_orders.find(biz_or_untagged, {"_id": 0, "paymentStatus": 1}).to_list(10000)
    payment_counts = {"paid": 0, "refunded": 0, "refund_failed": 0}
    for o in online_orders:
        status = o.get("paymentStatus")
        if status in payment_counts:
            payment_counts[status] += 1

    return {
        "businessId": business_id,
        "totalRevenue": round(sum(t.get("total", 0) for t in txns), 2),
        "totalTransactions": len(txns),
        "totalProducts": len(products),
        "totalCustomers": len(customers),
        "totalMembers": len(members),
        "totalStaff": len(staff),
        "onlineOrdersPaid": payment_counts["paid"],
        "onlineOrdersRefunded": payment_counts["refunded"],
        "onlineOrdersRefundFailed": payment_counts["refund_failed"],
    }

# Seed default business
async def seed_default_business():
    existing = await db.businesses.find_one({"id": "default"})
    if not existing:
        await db.businesses.insert_one({
            "id": "default",
            "slug": "default",
            "name": "NUA Restaurant",
            "type": "restaurant",
            "abn": "",
            "address": "",
            "phone": "",
            "email": "info@nua.com",
            "timezone": "Australia/Sydney",
            "currency": "AUD",
            "taxRate": 10,
            "ownerId": "system",
            "status": "active",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "settings": {"autoGratuity": 0, "serviceCharge": 0, "bookingEnabled": True, "tableOrderingEnabled": True}
        })


# Collections that get a businessId at write time now (see
# middleware/actor_context.py + entity_service.py) but predate that fix —
# every document in them either has no businessId field at all, or has it
# explicitly set to null (stamped_insert's setdefault wrote null before the
# actor context ever had a real value to give it). Backfilling them to
# "default" is the prerequisite for turning on any read-side tenant
# filtering: filtering today, before this runs, would make untagged data
# disappear rather than isolate it.
_BACKFILL_COLLECTIONS = ["customers", "vouchers", "wallet_ledger", "loyalty_ledger", "members",
                          "transactions", "refunds", "products", "expenses", "suppliers", "promotions",
                          "categories", "online_orders"]


@router.post("/backfill-tenant")
async def backfill_tenant(user: dict = Depends(require_owner)):
    """One-time (but safe to re-run — idempotent) migration: stamp
    businessId="default" onto any document in the collections above that's
    missing one. Only ever sets a currently-absent-or-null value; never
    overwrites a businessId a document already has."""
    results = {}
    query = {"$or": [{"businessId": {"$exists": False}}, {"businessId": None}]}
    for name in _BACKFILL_COLLECTIONS:
        r = await db[name].update_many(query, {"$set": {"businessId": "default"}})
        results[name] = r.modified_count
    # Businesses created before the online-storefront slug field existed
    # never got one — without it, /order-online?business=<slug> has nothing
    # to resolve for them. Assigned one per business (not update_many; each
    # needs its own collision-checked slug).
    slugged = 0
    async for biz in db.businesses.find({"$or": [{"slug": {"$exists": False}}, {"slug": None}]}, {"_id": 0, "id": 1, "name": 1}):
        await db.businesses.update_one({"id": biz["id"]}, {"$set": {"slug": await _unique_slug(biz.get("name", ""))}})
        slugged += 1
    results["businesses.slug"] = slugged
    return {"backfilled": results, "total": sum(results.values())}
