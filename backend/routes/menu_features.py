from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends
from deps import get_user, require_owner, require_owner_or_manager
from database import db
from datetime import datetime, timezone
import uuid, os, base64

router = APIRouter()

# ============ AI MENU IMPORT (PDF/JPEG/PNG) ============
@router.post("/menu/ai-import")
async def ai_import_menu(data: dict, _: dict = Depends(require_owner_or_manager)):
    """AI extracts menu items from an uploaded image (JPG/PNG/WebP) or PDF.

    Frontend sends `fileData` as base64 (data URL prefix stripped by caller or
    still included — we normalise) and `fileType` = "image" | "pdf".
    - Images: sent as a multimodal ImageContent so GPT-5.2 can actually SEE the
      menu. (The previous implementation passed the raw base64 characters as
      text, which is why it "never fetched anything".)
    - PDFs:   text extracted with pypdf then fed to the LLM as plain text.
    """
    import json as _json
    file_data = data.get("fileData", "") or ""
    file_type = (data.get("fileType") or "image").lower()

    # Normalise base64 — strip any leading data URL prefix
    if "," in file_data and file_data.startswith("data:"):
        file_data = file_data.split(",", 1)[1]
    if not file_data:
        return {"items": [], "count": 0, "message": "No file data received"}

    system_msg = (
        "You are a menu extraction expert. Extract EVERY menu item you can see.\n"
        "Return ONLY a JSON array — no markdown fences, no explanations — with this exact shape:\n"
        '[{"name": "Item Name", "category": "Category", "price": 12.50, "cost": 4.00, "description": "Brief desc"}]\n'
        "Category must be one of: Beverages, Food, Bakery, Alcohol, Desserts, Appetizers, Mains, Sides, Coffee, Wine, Cocktails.\n"
        "If cost is not on the menu, estimate at 30–35% of price. Include description only if the menu shows one."
    )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        if not api_key:
            return {"items": [], "count": 0, "message": "LLM key not configured"}

        chat = LlmChat(
            api_key=api_key,
            session_id=f"menu-import-{uuid.uuid4()}",
            system_message=system_msg,
        ).with_model("openai", "gpt-5.2")

        if file_type == "pdf":
            # Extract text from PDF then send as plain text
            try:
                import pypdf, io
                pdf_bytes = base64.b64decode(file_data)
                reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
                pdf_text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
                pdf_text = pdf_text.strip()
                if not pdf_text:
                    return {"items": [], "count": 0, "message": "Could not read any text from the PDF. Try uploading a photo of the menu instead."}
                user_msg = UserMessage(
                    text=f"Parse this menu text and return the JSON array of items:\n\n{pdf_text[:12000]}",
                )
            except Exception as pdf_err:
                return {"items": [], "count": 0, "message": f"PDF parse failed: {pdf_err}"}
        else:
            # Image — pass through multimodal vision so the model can actually SEE it
            user_msg = UserMessage(
                text="Extract every menu item from this image and return the JSON array.",
                file_contents=[ImageContent(image_base64=file_data)],
            )

        response = await chat.send_message(user_msg)

        # Parse the JSON response — strip common fence patterns
        items: list = []
        text = (response or "").strip()
        if text.startswith("```"):
            # remove leading fence + optional language tag
            text = text.split("```", 2)[1] if text.count("```") >= 2 else text.lstrip("`")
            if text.lstrip().lower().startswith("json"):
                text = text.split("\n", 1)[1] if "\n" in text else text[4:]
            text = text.rsplit("```", 1)[0].strip()
        try:
            parsed = _json.loads(text)
            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
                items = parsed["items"]
        except Exception:
            return {"items": [], "count": 0, "rawResponse": response, "message": "Could not auto-parse the LLM response. See rawResponse."}

        if not items:
            return {"items": [], "count": 0, "message": "No menu items detected. Try a clearer photo or a different page."}

        # Create products in DB
        from services.entity_service import stamped_insert
        created = []
        for item in items:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            try:
                price = float(item.get("price") or 0)
            except (TypeError, ValueError):
                price = 0.0
            try:
                cost = float(item.get("cost") or 0) or round(price * 0.35, 2)
            except (TypeError, ValueError):
                cost = round(price * 0.35, 2)
            category = str(item.get("category") or "Food").strip() or "Food"
            prod_id = str(uuid.uuid4())
            product = {
                "id": prod_id,
                "name": name,
                "category": category,
                "price": price,
                "cost": cost,
                "stock": 100,
                "sku": f"AI-{prod_id[:8].upper()}",
                "image": "",
                "gstRate": 10.0,
                "description": str(item.get("description") or ""),
                "active": True,
                "eightySixed": False,
            }
            saved = await stamped_insert("products", product, entity_type="product")
            saved.pop("_id", None)
            created.append(saved)

        return {
            "items": created,
            "count": len(created),
            "message": f"Successfully imported {len(created)} menu items",
        }
    except Exception as e:
        return {"items": [], "count": 0, "error": str(e), "message": f"AI extraction failed: {e}"}

# ============ PRICE ADJUSTMENT (Bulk) ============
@router.post("/menu/price-adjust")
async def bulk_price_adjust(data: dict, _: dict = Depends(require_owner_or_manager)):
    """Adjust prices by category with inflation/percentage"""

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
async def apply_ghost_discount(data: dict, user: dict = Depends(require_owner)):
    """Apply a secret discount that doesn't appear in any reports or sales records"""

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
async def get_ghost_discounts(_: dict = Depends(require_owner)):
    """Owner-only: view all ghost discounts (hidden from regular reports)"""
    ghosts = await db.ghost_discounts.find({}, {"_id": 0}).sort("appliedAt", -1).to_list(1000)
    return ghosts

# ============ WHAT-IF SIMULATOR (Enhanced with Quantity) ============
@router.post("/analytics/what-if-advanced")
async def what_if_advanced(data: dict, _: dict = Depends(require_owner_or_manager)):
    """Enhanced what-if with manual quantity projections"""

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
