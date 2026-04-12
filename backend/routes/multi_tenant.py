from fastapi import APIRouter, HTTPException, Request
from database import db
from typing import Optional
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/business")

# ============ MULTI-BUSINESS / MULTI-TENANT ============

@router.post("/create")
async def create_business(data: dict, request: Request):
    """Create a new business (Owner only)"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")

    business = {
        "id": f"BIZ-{str(uuid.uuid4())[:8].upper()}",
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
async def list_businesses(request: Request):
    """List all businesses for current owner"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    businesses = await db.businesses.find({"ownerId": user["id"]}, {"_id": 0}).to_list(100)
    return businesses

@router.get("/{business_id}")
async def get_business(business_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    business = await db.businesses.find_one({"id": business_id}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business

@router.put("/{business_id}")
async def update_business(business_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
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
async def export_business_data(business_id: str, request: Request, collection: Optional[str] = None):
    """Export all data for a specific business (Owner only)"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")

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
async def get_business_summary(business_id: str, request: Request):
    """Quick summary stats for a business"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")

    txns = await db.transactions.find({}, {"_id": 0}).to_list(10000)
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    customers = await db.customers.find({}, {"_id": 0}).to_list(10000)
    members = await db.members.find({}, {"_id": 0}).to_list(10000)
    staff = await db.auth_users.find({"businessId": business_id}, {"_id": 0, "password_hash": 0}).to_list(100)

    return {
        "businessId": business_id,
        "totalRevenue": round(sum(t.get("total", 0) for t in txns), 2),
        "totalTransactions": len(txns),
        "totalProducts": len(products),
        "totalCustomers": len(customers),
        "totalMembers": len(members),
        "totalStaff": len(staff),
    }

# Seed default business
async def seed_default_business():
    existing = await db.businesses.find_one({"id": "default"})
    if not existing:
        await db.businesses.insert_one({
            "id": "default",
            "name": "NUVA Restaurant",
            "type": "restaurant",
            "abn": "",
            "address": "",
            "phone": "",
            "email": "info@nuva.com",
            "timezone": "Australia/Sydney",
            "currency": "AUD",
            "taxRate": 10,
            "ownerId": "system",
            "status": "active",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "settings": {"autoGratuity": 0, "serviceCharge": 0, "bookingEnabled": True, "tableOrderingEnabled": True}
        })
