from fastapi import APIRouter, HTTPException, Request
from database import db
from datetime import datetime, timezone
import uuid

router = APIRouter()

# ============ CATEGORIES ============
@router.get("/categories")
async def get_categories():
    cats = await db.categories.find({}, {"_id": 0}).to_list(200)
    if not cats:
        defaults = [
            {"id": "cat-beverages", "name": "Beverages", "sortOrder": 0, "active": True},
            {"id": "cat-food", "name": "Food", "sortOrder": 1, "active": True},
            {"id": "cat-bakery", "name": "Bakery", "sortOrder": 2, "active": True},
            {"id": "cat-alcohol", "name": "Alcohol", "sortOrder": 3, "active": True},
            {"id": "cat-desserts", "name": "Desserts", "sortOrder": 4, "active": True},
        ]
        for d in defaults:
            await db.categories.insert_one(d)
        return defaults
    return cats

@router.post("/categories")
async def create_category(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    cat = {
        "id": f"cat-{str(uuid.uuid4())[:8]}",
        "name": data.get("name", ""), "sortOrder": data.get("sortOrder", 99),
        "active": data.get("active", True),
    }
    await db.categories.insert_one(cat)
    cat.pop("_id", None)
    return cat

@router.put("/categories/{cat_id}")
async def update_category(cat_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    allowed = {"name", "sortOrder", "active"}
    update = {k: v for k, v in data.items() if k in allowed}
    result = await db.categories.find_one_and_update({"id": cat_id}, {"$set": update}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    result.pop("_id", None)
    return result

@router.delete("/categories/{cat_id}")
async def delete_category(cat_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    await db.categories.delete_one({"id": cat_id})
    return {"message": "Category deleted"}

# ============ MODIFIERS (Universal) ============
@router.get("/modifiers")
async def get_modifiers():
    mods = await db.modifiers.find({}, {"_id": 0}).to_list(500)
    return mods

@router.post("/modifiers")
async def create_modifier(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    mod = {
        "id": f"mod-{str(uuid.uuid4())[:8]}",
        "name": data.get("name", ""),
        "type": data.get("type", "list"),  # list or dropdown
        "mandatory": data.get("mandatory", False),
        "multiSelect": data.get("multiSelect", False),
        "maxSelections": data.get("maxSelections", 1),
        "options": data.get("options", []),  # [{name, price}]
        "assignedCategories": data.get("assignedCategories", []),
        "printWithItem": data.get("printWithItem", True),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.modifiers.insert_one(mod)
    mod.pop("_id", None)
    return mod

@router.put("/modifiers/{mod_id}")
async def update_modifier(mod_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    allowed = {"name", "type", "mandatory", "multiSelect", "maxSelections", "options", "assignedCategories", "printWithItem"}
    update = {k: v for k, v in data.items() if k in allowed}
    result = await db.modifiers.find_one_and_update({"id": mod_id}, {"$set": update}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    result.pop("_id", None)
    return result

@router.delete("/modifiers/{mod_id}")
async def delete_modifier(mod_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    await db.modifiers.delete_one({"id": mod_id})
    return {"message": "Modifier deleted"}

# ============ DISCOUNTS & OFFERS ============
@router.get("/discounts")
async def get_discounts():
    discounts = await db.discounts.find({}, {"_id": 0}).to_list(200)
    return discounts

@router.post("/discounts")
async def create_discount(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    disc = {
        "id": f"DISC-{str(uuid.uuid4())[:8].upper()}",
        "name": data.get("name", ""),
        "type": data.get("type", "percentage"),  # percentage, fixed, bundle, bogo, half_price
        "value": data.get("value", 0),  # % or $ amount
        "conditions": data.get("conditions", {}),  # e.g. {minQty: 2, productId: "..."}
        "active": data.get("active", True),
        "startDate": data.get("startDate"), "endDate": data.get("endDate"),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.discounts.insert_one(disc)
    disc.pop("_id", None)
    return disc

@router.put("/discounts/{disc_id}")
async def update_discount(disc_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    allowed = {"name", "type", "value", "conditions", "active", "startDate", "endDate"}
    update = {k: v for k, v in data.items() if k in allowed}
    result = await db.discounts.find_one_and_update({"id": disc_id}, {"$set": update}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    result.pop("_id", None)
    return result

@router.delete("/discounts/{disc_id}")
async def delete_discount(disc_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    await db.discounts.delete_one({"id": disc_id})
    return {"message": "Discount deleted"}

# ============ COMP / VOID ============
@router.post("/comp-void")
async def create_comp_void(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    record = {
        "id": f"CV-{str(uuid.uuid4())[:8].upper()}",
        "type": data.get("type", "comp"),  # comp or void
        "transactionId": data.get("transactionId"),
        "items": data.get("items", []),
        "reason": data.get("reason", ""),
        "amount": data.get("amount", 0),
        "printVoid": data.get("printVoid", False),
        "processedBy": user["id"],
        "processedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.comp_voids.insert_one(record)
    record.pop("_id", None)
    return record

@router.get("/comp-void")
async def get_comp_voids(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    records = await db.comp_voids.find({}, {"_id": 0}).sort("processedAt", -1).to_list(500)
    return records

# ============ PAYMENT LINKS ============
@router.post("/payment-links")
async def create_payment_link(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    link = {
        "id": f"PLINK-{str(uuid.uuid4())[:8].upper()}",
        "productId": data.get("productId"),
        "productName": data.get("productName", ""),
        "price": data.get("price", 0),
        "url": f"https://pay.nua.pos/{str(uuid.uuid4())[:12]}",
        "active": True,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.payment_links.insert_one(link)
    link.pop("_id", None)
    return link

@router.get("/payment-links")
async def get_payment_links():
    links = await db.payment_links.find({}, {"_id": 0}).to_list(500)
    return links

@router.delete("/payment-links/{link_id}")
async def delete_payment_link(link_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    await db.payment_links.delete_one({"id": link_id})
    return {"message": "Payment link deleted"}
