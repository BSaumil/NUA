from fastapi import APIRouter, HTTPException, Request
from database import db
import os
import uuid
from datetime import datetime

router = APIRouter()

async def _get_ai_chat():
    from emergentintegrations.llm.chat import LlmChat
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="AI not configured")
    chat = LlmChat(api_key=key, session_id=f"pantry-{uuid.uuid4()}", system_message=(
        "You are an expert restaurant supply chain manager and chef. "
        "Analyze menu items, their descriptions, and sales data to determine exact ingredient needs. "
        "Always respond with valid JSON only, no markdown."
    ))
    chat.with_model("openai", "gpt-5.2")
    return chat

@router.get("/ai-pantry/generate")
async def generate_pantry_list(request: Request):
    """AI-powered weekly ordering list based on menu, sales, and reservations"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")

    # Gather data
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    txns = await db.transactions.find({}, {"_id": 0}).to_list(5000)
    reservations = await db.reservations.find({}, {"_id": 0}).to_list(500)

    # Build sales summary
    product_sales = {}
    for txn in txns:
        for item in txn.get("items", []):
            pid = item.get("productId", "")
            product_sales[pid] = product_sales.get(pid, 0) + item.get("quantity", 0)

    upcoming_covers = sum(r.get("partySize", 0) for r in reservations if r.get("status") in ("confirmed", "seated"))

    menu_data = []
    for p in products:
        menu_data.append({
            "id": p["id"], "name": p["name"],
            "category": p.get("category", "Other"),
            "description": p.get("description", ""),
            "price": p.get("price", 0),
            "cost": p.get("cost", 0),
            "currentStock": p.get("stock", 0),
            "weeklySales": product_sales.get(p["id"], 0),
        })

    prompt = f"""Analyze this restaurant menu and sales data to generate a weekly ordering/pantry list.

Menu Items:
{str(menu_data)}

Upcoming reservations: {upcoming_covers} covers booked this week.
Total transactions last period: {len(txns)}

Generate a JSON response with this EXACT structure:
{{
  "orderingList": [
    {{
      "ingredient": "ingredient name",
      "category": "Produce|Dairy|Meat|Seafood|Dry Goods|Beverages|Other",
      "estimatedQuantity": "amount with unit (e.g., 5kg, 2L, 50 units)",
      "urgency": "high|medium|low",
      "estimatedCost": 0.00,
      "usedIn": ["menu item 1", "menu item 2"],
      "notes": "any wastage or storage notes"
    }}
  ],
  "wastageInsights": [
    {{
      "item": "ingredient name",
      "risk": "high|medium|low",
      "recommendation": "suggestion to minimize waste"
    }}
  ],
  "weeklyBudgetEstimate": 0.00,
  "coverForecast": 0,
  "summary": "brief summary of ordering priorities"
}}"""

    from emergentintegrations.llm.chat import UserMessage
    chat = await _get_ai_chat()
    response = await chat.send_message(UserMessage(text=prompt))

    import json
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        # Try extracting JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(response[start:end])
        else:
            parsed = {"raw": response, "error": "Could not parse AI response"}

    # Save to DB
    pantry_doc = {
        "id": f"PANTRY-{str(uuid.uuid4())[:8].upper()}",
        "generatedAt": datetime.utcnow().isoformat(),
        "generatedBy": user["id"],
        "data": parsed,
        "menuItemCount": len(products),
        "transactionCount": len(txns),
        "upcomingCovers": upcoming_covers,
    }
    await db.pantry_lists.insert_one(pantry_doc)
    pantry_doc.pop("_id", None)
    return pantry_doc

@router.get("/ai-pantry/history")
async def get_pantry_history(request: Request):
    """Get previous pantry list generations"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    lists = await db.pantry_lists.find({}, {"_id": 0}).sort("generatedAt", -1).to_list(20)
    return lists
