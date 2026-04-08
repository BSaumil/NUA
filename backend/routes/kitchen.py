from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime
from database import db
from models.kitchen_order import KitchenOrder, KitchenOrderCreate

router = APIRouter()

# ============ KITCHEN DISPLAY (KDS) API ============
@router.get("/kitchen/orders")
async def get_kitchen_orders(status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    else:
        query["status"] = {"$in": ["new", "preparing", "ready"]}
    orders = await db.kitchen_orders.find(query, {"_id": 0}).sort("createdAt", 1).to_list(100)
    return orders

@router.post("/kitchen/orders")
async def create_kitchen_order(order: KitchenOrderCreate):
    order_obj = KitchenOrder(**order.dict())
    await db.kitchen_orders.insert_one(order_obj.dict())
    return order_obj.dict()

@router.post("/kitchen/orders/{order_id}/start")
async def start_kitchen_order(order_id: str):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id}, {"$set": {"status": "preparing", "startedAt": datetime.utcnow().isoformat()}}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

@router.post("/kitchen/orders/{order_id}/ready")
async def mark_order_ready(order_id: str):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id}, {"$set": {"status": "ready", "readyAt": datetime.utcnow().isoformat()}}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

@router.post("/kitchen/orders/{order_id}/served")
async def mark_order_served(order_id: str):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id}, {"$set": {"status": "served", "servedAt": datetime.utcnow().isoformat()}}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

@router.post("/kitchen/orders/{order_id}/cancel")
async def cancel_kitchen_order(order_id: str):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id}, {"$set": {"status": "cancelled"}}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

@router.post("/kitchen/orders/{order_id}/fire-course")
async def fire_next_course(order_id: str, course: int = 2):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id}, {"$set": {"currentCourse": course}}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

@router.post("/kitchen/orders/{order_id}/priority")
async def set_order_priority(order_id: str, priority: str = "rush"):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id}, {"$set": {"priority": priority}}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

# ============ PREP MANAGEMENT API ============
@router.get("/kitchen/prep-list")
async def get_prep_list():
    today = datetime.utcnow().strftime('%Y-%m-%d')
    reservations = await db.reservations.find({"date": today}, {"_id": 0}).to_list(100)
    total_covers = sum(r.get("partySize", 0) for r in reservations)

    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    all_txns = await db.transactions.find({}, {"_id": 0}).to_list(10000)

    product_popularity = {}
    for txn in all_txns:
        for item in txn.get("items", []):
            pid = item.get("productId", "")
            product_popularity[pid] = product_popularity.get(pid, 0) + item.get("quantity", 0)

    total_qty = sum(product_popularity.values()) or 1

    prep_items = []
    for p in products:
        pop_qty = product_popularity.get(p["id"], 0)
        popularity_pct = (pop_qty / total_qty) * 100
        est_qty = max(1, int((pop_qty / max(len(all_txns), 1)) * max(total_covers, 10)))
        prep_items.append({
            "productId": p["id"], "name": p["name"], "category": p.get("category", "Other"),
            "currentStock": p.get("stock", 0), "estimatedNeeded": est_qty,
            "popularityPct": round(popularity_pct, 1), "prepStatus": "pending",
        })

    prep_items.sort(key=lambda x: x["estimatedNeeded"], reverse=True)
    return {"date": today, "expectedCovers": total_covers, "totalReservations": len(reservations), "prepItems": prep_items[:20]}
