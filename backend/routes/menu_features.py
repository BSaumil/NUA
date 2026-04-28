from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from database import db
from datetime import datetime, timezone
import uuid, os, base64

router = APIRouter()

# ============ AI MENU IMPORT (PDF/JPEG) ============
@router.post("/menu/ai-import")
async def ai_import_menu(data: dict, request: Request):
    """AI extracts menu items from uploaded image/PDF data (base64 encoded)"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")

    file_data = data.get("fileData", "")  # base64 encoded
    file_type = data.get("fileType", "image")  # image or pdf

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        chat = LlmChat(api_key=api_key, session_id=f"menu-import-{uuid.uuid4()}", system_message="""You are a menu extraction expert. Extract ALL menu items from the provided menu description.
Return ONLY a JSON array of items with this exact format (no markdown, no explanation, just pure JSON):
[{"name": "Item Name", "category": "Category", "price": 12.50, "cost": 4.00, "description": "Brief desc"}]
Categories should be one of: Beverages, Food, Bakery, Alcohol, Desserts, Appetizers, Mains, Sides.
Estimate cost at roughly 30-35% of price if not available.""")
        chat.with_model("openai", "gpt-5.2")

        prompt = f"Extract all menu items from this {file_type} menu. The file content is provided as base64. Parse it and return the JSON array of items:\n\n{file_data[:5000]}"
        if len(file_data) > 5000:
            prompt = f"Here is a menu to parse. Extract all items with their names, categories, prices. Estimate costs at 30-35% of price:\n\n{file_data[:3000]}"

        msg = UserMessage(text=prompt)
        response = await chat.send_message(msg)

        # Parse the JSON response
        import json
        items = []
        try:
            # Try to find JSON array in the response
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            items = json.loads(text)
        except:
            # If parsing fails, return the raw response for user to see
            return {"items": [], "rawResponse": response, "message": "Could not auto-parse. Please check the raw response."}

        # Create products in DB
        created = []
        for item in items:
            product = {
                "id": str(uuid.uuid4()),
                "name": item.get("name", "Unknown"),
                "category": item.get("category", "Food"),
                "price": float(item.get("price", 0)),
                "cost": float(item.get("cost", 0)),
                "stock": 100,
                "sku": f"{item.get('category', 'FOO')[:3].upper()}-{str(uuid.uuid4())[:4].upper()}",
                "image": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=200",
                "gstRate": 10.0,
                "description": item.get("description", ""),
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            }
            await db.products.insert_one(product)
            product.pop("_id", None)
            created.append(product)

        return {"items": created, "count": len(created), "message": f"Successfully imported {len(created)} menu items"}
    except Exception as e:
        return {"items": [], "error": str(e), "message": "AI extraction failed - check your file format"}

# ============ PRICE ADJUSTMENT (Bulk) ============
@router.post("/menu/price-adjust")
async def bulk_price_adjust(data: dict, request: Request):
    """Adjust prices by category with inflation/percentage"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")

    category = data.get("category")  # None = all categories
    adjustment_type = data.get("type", "percentage")  # percentage or fixed
    amount = float(data.get("amount", 0))  # e.g. 5 for 5% or $5
    direction = data.get("direction", "increase")  # increase or decrease

    query = {"category": category} if category else {}
    products = await db.products.find(query, {"_id": 0}).to_list(10000)

    updated = []
    for p in products:
        old_price = p.get("price", 0)
        if adjustment_type == "percentage":
            change = old_price * (amount / 100)
        else:
            change = amount

        new_price = old_price + change if direction == "increase" else old_price - change
        new_price = max(round(new_price, 2), 0.01)

        await db.products.update_one({"id": p["id"]}, {"$set": {"price": new_price, "updatedAt": datetime.now(timezone.utc).isoformat()}})
        updated.append({"id": p["id"], "name": p["name"], "oldPrice": old_price, "newPrice": new_price})

    return {"updated": len(updated), "items": updated, "message": f"Adjusted {len(updated)} items by {amount}{'%' if adjustment_type == 'percentage' else '$'} {direction}"}

# ============ GHOST DISCOUNT / VOID (Secret Owner Feature) ============
@router.post("/pos/ghost-discount")
async def apply_ghost_discount(data: dict, request: Request):
    """Apply a secret discount that doesn't appear in any reports or sales records"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Access denied")

    transaction_id = data.get("transactionId")
    discount_amount = float(data.get("amount", 0))
    reason = data.get("reason", "Owner discretion")

    if not transaction_id:
        raise HTTPException(status_code=400, detail="Transaction ID required")

    txn = await db.transactions.find_one({"id": transaction_id})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Record ghost discount in separate hidden collection
    ghost = {
        "id": f"GHOST-{str(uuid.uuid4())[:8].upper()}",
        "transactionId": transaction_id,
        "amount": discount_amount,
        "reason": reason,
        "appliedBy": user["id"],
        "appliedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.ghost_discounts.insert_one(ghost)
    ghost.pop("_id", None)

    # Adjust the transaction total without leaving a trace in regular reports
    new_total = max(txn.get("total", 0) - discount_amount, 0)
    await db.transactions.update_one(
        {"id": transaction_id},
        {"$set": {"total": round(new_total, 2), "ghostAdjusted": True}}
    )

    return ghost

@router.get("/pos/ghost-discounts")
async def get_ghost_discounts(request: Request):
    """Owner-only: view all ghost discounts (hidden from regular reports)"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Access denied")
    ghosts = await db.ghost_discounts.find({}, {"_id": 0}).sort("appliedAt", -1).to_list(1000)
    return ghosts

# ============ WHAT-IF SIMULATOR (Enhanced with Quantity) ============
@router.post("/analytics/what-if-advanced")
async def what_if_advanced(data: dict, request: Request):
    """Enhanced what-if with manual quantity projections"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")

    changes = data.get("changes", [])
    results = []
    total_current_revenue = 0
    total_projected_revenue = 0
    total_current_profit = 0
    total_projected_profit = 0

    for c in changes:
        pid = c.get("productId")
        product = await db.products.find_one({"id": pid}, {"_id": 0})
        if not product:
            continue

        current_price = product.get("price", 0)
        current_cost = product.get("cost", 0)
        new_price = c.get("newPrice", current_price)
        new_cost = c.get("newCost", current_cost)
        projected_qty = c.get("projectedQty", 0)  # NEW: manual quantity

        # Calculate using projected quantity
        if projected_qty > 0:
            current_revenue = current_price * projected_qty
            projected_revenue = new_price * projected_qty
            current_profit = (current_price - current_cost) * projected_qty
            projected_profit = (new_price - new_cost) * projected_qty
        else:
            # Fallback to historical average (from transactions)
            txns = await db.transactions.find({}, {"_id": 0, "items": 1}).to_list(10000)
            qty_sold = 0
            for t in txns:
                for item in t.get("items", []):
                    if item.get("productId") == pid:
                        qty_sold += item.get("quantity", 0)
            avg_daily = max(qty_sold / 30, 1)
            projected_qty = round(avg_daily * 30)
            current_revenue = current_price * projected_qty
            projected_revenue = new_price * projected_qty
            current_profit = (current_price - current_cost) * projected_qty
            projected_profit = (new_price - new_cost) * projected_qty

        results.append({
            "productId": pid, "productName": product.get("name", ""),
            "currentPrice": current_price, "newPrice": new_price,
            "currentCost": current_cost, "newCost": new_cost,
            "projectedQty": projected_qty,
            "currentRevenue": round(current_revenue, 2),
            "projectedRevenue": round(projected_revenue, 2),
            "currentProfit": round(current_profit, 2),
            "projectedProfit": round(projected_profit, 2),
            "revenueChange": round(projected_revenue - current_revenue, 2),
            "profitChange": round(projected_profit - current_profit, 2),
        })
        total_current_revenue += current_revenue
        total_projected_revenue += projected_revenue
        total_current_profit += current_profit
        total_projected_profit += projected_profit

    return {
        "items": results,
        "summary": {
            "currentRevenue": round(total_current_revenue, 2),
            "projectedRevenue": round(total_projected_revenue, 2),
            "revenueChange": round(total_projected_revenue - total_current_revenue, 2),
            "currentProfit": round(total_current_profit, 2),
            "projectedProfit": round(total_projected_profit, 2),
            "profitChange": round(total_projected_profit - total_current_profit, 2),
        }
    }
