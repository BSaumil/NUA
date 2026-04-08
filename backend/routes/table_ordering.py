from fastapi import APIRouter, HTTPException, Request
from typing import Optional
from datetime import datetime
from database import db
from models.kitchen_order import KitchenOrder
import uuid

router = APIRouter()

# ============ TABLE-SIDE ORDERING API ============

@router.get("/table/{table_id}/menu")
async def get_table_menu(table_id: str):
    """Get menu for a specific table (public endpoint for QR scan)"""
    products = await db.products.find({"stock": {"$gt": 0}}, {"_id": 0}).to_list(1000)
    categories = {}
    for p in products:
        cat = p.get("category", "Other")
        if cat not in categories:
            categories[cat] = {"name": cat, "items": []}
        categories[cat]["items"].append({
            "id": p["id"], "name": p["name"], "price": p.get("price", 0),
            "description": p.get("description", ""),
            "image": p.get("image", ""),
            "dietary": p.get("dietary", []),
            "allergens": p.get("allergens", []),
        })
    # Get table info
    table_info = None
    floor_plans = await db.floor_plans.find({}, {"_id": 0}).to_list(10)
    for fp in floor_plans:
        for t in fp.get("tables", []):
            if t.get("id") == table_id:
                table_info = {"id": t["id"], "number": t.get("number", ""), "section": t.get("section", "")}
                break
    return {
        "tableId": table_id,
        "tableInfo": table_info,
        "categories": list(categories.values()),
        "restaurantName": "Ananta",
    }

@router.post("/table/{table_id}/order")
async def place_table_order(table_id: str, data: dict):
    """Place an order from a table (customer-initiated)"""
    items = data.get("items", [])
    customer_name = data.get("customerName", "Table Guest")
    notes = data.get("notes", "")

    if not items:
        raise HTTPException(status_code=400, detail="No items in order")

    # Build kitchen order items
    kitchen_items = []
    subtotal = 0
    for item in items:
        product = await db.products.find_one({"id": item["productId"]}, {"_id": 0})
        if not product:
            continue
        qty = item.get("quantity", 1)
        price = product.get("price", 0)
        kitchen_items.append({
            "productId": product["id"], "name": product["name"],
            "quantity": qty, "price": price,
            "modifications": item.get("modifications", ""),
        })
        subtotal += price * qty

    # Get table number
    table_number = table_id
    floor_plans = await db.floor_plans.find({}, {"_id": 0}).to_list(10)
    for fp in floor_plans:
        for t in fp.get("tables", []):
            if t.get("id") == table_id:
                table_number = t.get("number", table_id)
                break

    # Create kitchen order
    order_id = f"TORD-{str(uuid.uuid4())[:8].upper()}"
    order_doc = {
        "id": order_id,
        "tableId": table_id,
        "tableNumber": table_number,
        "items": kitchen_items,
        "customerName": customer_name,
        "notes": notes,
        "source": "table_qr",
        "status": "new",
        "subtotal": round(subtotal, 2),
        "gst": round(subtotal * 0.1, 2),
        "total": round(subtotal * 1.1, 2),
        "createdAt": datetime.utcnow().isoformat(),
        "priority": "normal",
    }
    await db.kitchen_orders.insert_one(order_doc)
    order_doc.pop("_id", None)

    # Update table status
    for fp in floor_plans:
        for t in fp.get("tables", []):
            if t.get("id") == table_id:
                t["status"] = "occupied"
                await db.floor_plans.update_one(
                    {"id": fp["id"]}, {"$set": {"tables": fp["tables"]}}
                )
                break

    return {
        "orderId": order_id,
        "tableNumber": table_number,
        "items": kitchen_items,
        "subtotal": order_doc["subtotal"],
        "gst": order_doc["gst"],
        "total": order_doc["total"],
        "status": "new",
        "message": "Order placed! Your food is being prepared.",
    }

@router.get("/table/{table_id}/orders")
async def get_table_orders(table_id: str):
    """Get active orders for a table"""
    orders = await db.kitchen_orders.find(
        {"tableId": table_id, "status": {"$in": ["new", "preparing", "ready"]}},
        {"_id": 0}
    ).sort("createdAt", -1).to_list(50)
    return orders

@router.get("/table/order/{order_id}/status")
async def get_order_status(order_id: str):
    """Check status of a specific order"""
    order = await db.kitchen_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "orderId": order["id"],
        "status": order["status"],
        "items": order.get("items", []),
        "total": order.get("total", 0),
        "createdAt": order.get("createdAt"),
        "startedAt": order.get("startedAt"),
        "readyAt": order.get("readyAt"),
    }

# ============ TABLE QR CODE GENERATION (Staff) ============
@router.get("/tables/qr-codes")
async def get_table_qr_codes():
    """Generate QR code data for all tables"""
    floor_plans = await db.floor_plans.find({}, {"_id": 0}).to_list(10)
    tables = []
    for fp in floor_plans:
        for t in fp.get("tables", []):
            tables.append({
                "tableId": t.get("id"),
                "number": t.get("number", ""),
                "section": t.get("section", ""),
                "status": t.get("status", "available"),
            })
    return tables
