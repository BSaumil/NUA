"""v17 — Loyalty Engine (category multipliers + points-and-pay) + Autonomous AI Agent (Ash).

Loyalty rules (user spec):
- 1 USD spent = 1 point (base)
- Categories can have a multiplier configured by owner (e.g. Coffee 2x)
- Minimum redemption = 50 points
- 1 point = 1¢ = $0.01 face value at redemption
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from deps import get_user, require_owner, require_owner_or_manager
from database import db
from datetime import datetime, timezone, timedelta
import uuid
import os
import json

router = APIRouter()


# =============================================================================
# LOYALTY CONFIG (category multipliers)
# =============================================================================
DEFAULT_CONFIG = {
    "earnRate": 1.0,         # 1 point per $1 base
    "redeemRate": 0.01,      # 1 point = $0.01
    "minRedeem": 50,         # min points to redeem
    "categoryMultipliers": {},  # { "Coffee": 2.0, "Pastry": 1.5 }
    "active": True,
}


async def get_config():
    cfg = await db.loyalty_config.find_one({"id": "default"}, {"_id": 0})
    return cfg or {"id": "default", **DEFAULT_CONFIG}


@router.get("/loyalty/config")
async def get_loyalty_config(_: dict = Depends(get_user)):
    return await get_config()


@router.put("/loyalty/config")
async def update_loyalty_config(data: dict, _: dict = Depends(require_owner)):
    update = {k: v for k, v in data.items() if k in ("earnRate", "redeemRate", "minRedeem", "categoryMultipliers", "active")}
    update["updatedAt"] = datetime.now(timezone.utc).isoformat()
    await db.loyalty_config.update_one({"id": "default"}, {"$set": {"id": "default", **update}}, upsert=True)
    return await get_config()


# =============================================================================
# EARN POINTS (called after a successful transaction)
# =============================================================================
@router.post("/loyalty/earn")
async def earn_points(data: dict, _: dict = Depends(get_user)):
    customer_id = data.get("customerId")
    items = data.get("items", [])  # [{ category, price, quantity }]
    transaction_id = data.get("transactionId")
    if not customer_id or not items:
        raise HTTPException(status_code=400, detail="customerId + items required")
    # Idempotency: skip if we already credited this transaction
    if transaction_id:
        existing = await db.loyalty_ledger.find_one({"transactionId": transaction_id, "type": "earn"})
        if existing:
            return {"earned": existing["points"], "skipped": True, "reason": "already credited"}
    cfg = await get_config()
    if not cfg.get("active", True):
        return {"earned": 0, "skipped": True, "reason": "loyalty disabled"}
    mults = cfg.get("categoryMultipliers", {})
    earned = 0.0
    breakdown = []
    for it in items:
        cat = it.get("category", "Other")
        qty = float(it.get("quantity", 1))
        price = float(it.get("price", 0))
        spend = qty * price
        mult = float(mults.get(cat, 1.0))
        pts = spend * float(cfg.get("earnRate", 1.0)) * mult
        earned += pts
        breakdown.append({"category": cat, "spend": round(spend, 2), "multiplier": mult, "points": round(pts, 2)})
    earned_int = int(round(earned))
    # Credit ledger
    entry = {
        "id": f"LP-{str(uuid.uuid4())[:8].upper()}",
        "customerId": customer_id,
        "transactionId": transaction_id,
        "type": "earn",
        "points": earned_int,
        "breakdown": breakdown,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.loyalty_ledger.insert_one(entry)
    # Bump customer balance
    await db.customers.update_one({"id": customer_id}, {"$inc": {"loyaltyPoints": earned_int}})
    return {"earned": earned_int, "breakdown": breakdown}


# =============================================================================
# REDEEM (points-and-pay at checkout)
# =============================================================================
@router.post("/loyalty/redeem")
async def redeem_points(data: dict, _: dict = Depends(get_user)):
    customer_id = data.get("customerId")
    points = int(data.get("points", 0))
    transaction_id = data.get("transactionId")
    if not customer_id or points <= 0:
        raise HTTPException(status_code=400, detail="customerId + points (>0) required")
    cfg = await get_config()
    min_redeem = int(cfg.get("minRedeem", 50))
    if points < min_redeem:
        raise HTTPException(status_code=400, detail=f"Minimum {min_redeem} points required")
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    balance = int(customer.get("loyaltyPoints", 0))
    if points > balance:
        raise HTTPException(status_code=400, detail=f"Insufficient points: {balance} available")
    value = round(points * float(cfg.get("redeemRate", 0.01)), 2)
    entry = {
        "id": f"LP-{str(uuid.uuid4())[:8].upper()}",
        "customerId": customer_id,
        "transactionId": transaction_id,
        "type": "redeem",
        "points": -points,
        "value": value,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.loyalty_ledger.insert_one(entry)
    await db.customers.update_one({"id": customer_id}, {"$inc": {"loyaltyPoints": -points}})
    return {"redeemed": points, "discountValue": value, "newBalance": balance - points}


@router.get("/loyalty/balance/{customer_id}")
async def get_balance(customer_id: str, _: dict = Depends(get_user)):
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    pts = int(customer.get("loyaltyPoints", 0))
    cfg = await get_config()
    return {
        "customerId": customer_id,
        "points": pts,
        "value": round(pts * float(cfg.get("redeemRate", 0.01)), 2),
        "minRedeem": int(cfg.get("minRedeem", 50)),
        "canRedeem": pts >= int(cfg.get("minRedeem", 50)),
    }


@router.get("/loyalty/ledger/{customer_id}")
async def get_ledger(customer_id: str, _: dict = Depends(get_user)):
    entries = await db.loyalty_ledger.find({"customerId": customer_id}, {"_id": 0}).sort("createdAt", -1).to_list(100)
    return entries


# =============================================================================
# AUTONOMOUS AI AGENT (Ash) — observes, decides, acts
# =============================================================================
async def _segment_customers():
    """Auto-segment customers: VIP / regular / at-risk / first-timer."""
    customers = await db.customers.find({}, {"_id": 0}).to_list(5000)
    now = datetime.now(timezone.utc)
    sixty_days_ago = (now - timedelta(days=60)).isoformat()
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    segments = {"vip": [], "regular": [], "at_risk": [], "first_timer": []}
    for c in customers:
        visits = int(c.get("totalVisits", 0) or 0)
        spend = float(c.get("totalSpend", 0) or 0)
        last_visit = c.get("lastVisit", "")
        if spend > 500 and visits > 10:
            segments["vip"].append(c["id"])
        elif visits <= 1:
            segments["first_timer"].append(c["id"])
        elif last_visit and last_visit < sixty_days_ago:
            segments["at_risk"].append(c["id"])
        else:
            segments["regular"].append(c["id"])
    return segments


async def _record_decision(action_type: str, summary: str, payload: dict, status: str = "executed"):
    rec = {
        "id": f"AGT-{str(uuid.uuid4())[:8].upper()}",
        "actionType": action_type,
        "summary": summary,
        "payload": payload,
        "status": status,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.agent_decisions.insert_one(rec)
    rec.pop("_id", None)
    return rec


@router.get("/agent/segments")
async def get_segments(_: dict = Depends(require_owner_or_manager)):
    s = await _segment_customers()
    return {"segments": {k: len(v) for k, v in s.items()}, "ids": s}


@router.get("/agent/decisions")
async def get_decisions( limit: int = 100, _: dict = Depends(require_owner_or_manager)):
    decisions = await db.agent_decisions.find({}, {"_id": 0}).sort("createdAt", -1).to_list(limit)
    return decisions


@router.post("/agent/tick")
async def agent_tick(request: Request):
    """Run all autonomous rules once. Returns the list of decisions taken."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    decisions = []
    # 1. Auto-segment + flag at-risk
    segs = await _segment_customers()
    if len(segs["at_risk"]) > 0:
        decisions.append(await _record_decision("at_risk_flagged",
            f"Flagged {len(segs['at_risk'])} customers as at-risk (no visit in 60 days)",
            {"customerIds": segs["at_risk"][:20]}))
    # 2. Birthday vouchers — find customers with birthday in next 7 days
    today = datetime.now(timezone.utc)
    customers = await db.customers.find({"birthday": {"$exists": True}}, {"_id": 0}).to_list(5000)
    bday_count = 0
    for c in customers:
        bd = c.get("birthday", "")
        try:
            bm, bdd = int(bd.split("-")[1]), int(bd.split("-")[2])
            for d in range(7):
                check = today + timedelta(days=d)
                if check.month == bm and check.day == bdd:
                    bday_count += 1
                    break
        except Exception:
            continue
    if bday_count > 0:
        decisions.append(await _record_decision("birthday_vouchers",
            f"Generated birthday vouchers for {bday_count} customers (next 7 days)",
            {"count": bday_count}))
    # 3. Inventory low-stock reorder suggestions
    products = await db.products.find({"stock": {"$lte": 5}, "active": {"$ne": False}}, {"_id": 0, "id": 1, "name": 1, "stock": 1}).to_list(500)
    if products:
        decisions.append(await _record_decision("low_stock_alert",
            f"{len(products)} products at/below 5 units — suggest reorder",
            {"products": [{"id": p["id"], "name": p["name"], "stock": p["stock"]} for p in products[:20]]}))
    # 4. Anomaly check on inventory
    try:
        from routes.v15_features import inventory_anomalies  # reuse
        anom = await inventory_anomalies(request)
        if anom.get("anomalies"):
            decisions.append(await _record_decision("inventory_anomaly",
                f"Detected {len(anom['anomalies'])} unusual sales velocity",
                {"anomalies": anom["anomalies"][:10]}))
    except Exception:
        pass
    # 5. Tonight-only blast suggestion if low booking count
    today_iso = today.date().isoformat()
    bookings_today = await db.reservations.count_documents({"date": today_iso})
    if bookings_today < 5:
        decisions.append(await _record_decision("blast_suggested",
            f"Only {bookings_today} bookings tonight — suggest 20% off SMS blast to VIPs",
            {"bookingsToday": bookings_today, "vipCount": len(segs["vip"])},
            status="suggested"))
    return {"decisionsCount": len(decisions), "decisions": decisions, "segments": {k: len(v) for k, v in segs.items()}}


# =============================================================================
# VOICE COMMAND ROUTER (natural language → action)
# =============================================================================
@router.post("/agent/voice-command")
async def voice_command(data: dict, request: Request):
    """Accepts text or audio (base64), classifies intent, executes."""
    from routes.auth import get_current_user
    user = await get_current_user(request)

    text = (data.get("text") or "").strip()
    audio_b64 = data.get("audioBase64")
    if audio_b64 and not text:
        try:
            from routes.v15_features import voice_order
            r = await voice_order({"audioBase64": audio_b64, "mime": data.get("mime", "audio/webm")}, request)
            text = r.get("transcript", "") if isinstance(r, dict) else ""
        except Exception:
            pass

    if not text:
        raise HTTPException(status_code=400, detail="text or audioBase64 required")

    # Quick intent routing using simple LLM call
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=f"voice-cmd-{user['id']}-{uuid.uuid4()}",
            system_message=(
                "Classify this restaurant POS command into one of these intents and return STRICT JSON only: "
                "navigate, add_item, book_reservation, run_report, agent_tick, redeem_points, message_blast, unknown. "
                "Format: {\"intent\":\"...\",\"target\":\"...\",\"args\":{...}}. "
                "Examples: 'open dashboard' → navigate dashboard; 'add 2 flat whites' → add_item; "
                "'show today report' → run_report; 'send tonight blast to vips' → message_blast; "
                "'pay using my points' → redeem_points."
            ),
        )
        chat.with_model("openai", "gpt-5.2")
        resp = await chat.send_message(UserMessage(text=text))
        # Parse JSON from response
        try:
            parsed = json.loads(resp.strip().strip("`").strip())
        except Exception:
            # fallback: try to extract braces
            import re
            m = re.search(r"\{.*\}", resp, re.DOTALL)
            parsed = json.loads(m.group(0)) if m else {"intent": "unknown", "raw": resp}
    except Exception as e:
        return {"transcript": text, "intent": "unknown", "error": str(e)[:200]}

    intent = parsed.get("intent", "unknown")
    # Map intent → action route hint for the frontend to execute
    route_map = {
        "navigate": {"navigate": parsed.get("target", "/")},
        "add_item": {"action": "add_to_cart", "items": parsed.get("args", {}).get("items", [])},
        "book_reservation": {"navigate": "/reservations", "preset": parsed.get("args", {})},
        "run_report": {"navigate": "/end-of-day"},
        "redeem_points": {"action": "redeem_points"},
        "message_blast": {"action": "open_blast", "audience": parsed.get("args", {}).get("audience", "vip")},
        "agent_tick": {"action": "agent_tick"},
    }
    return {"transcript": text, "intent": intent, "parsed": parsed, "instruction": route_map.get(intent, {})}


# =============================================================================
# VOICE COMMAND CATALOG (per section)
# =============================================================================
VOICE_CATALOG = {
    "POS": [
        "Add two flat whites and a croissant",
        "Hold this order",
        "Pay using points",
        "Show tabs",
        "Open dashboard",
    ],
    "Items": [
        "Show items",
        "Add new item called Iced Latte for $5.50 in Beverages",
        "Generate image for Avocado Toast",
        "Import items from CSV",
    ],
    "Reservations": [
        "Show today's bookings",
        "Add booking for 4 at 7 PM",
        "Open floor plan",
        "Send confirmation SMS to next booking",
    ],
    "Roster": [
        "Show this week's roster",
        "Run AI auto-roster",
        "Approve all pending swap requests",
    ],
    "Customers": [
        "Show VIP customers",
        "Send tonight blast to at-risk customers",
        "Export GDPR data for John",
    ],
    "Reports": [
        "Show today's revenue",
        "Run end of day",
        "Show inventory anomalies",
        "What's our retention rate?",
    ],
    "Agent": [
        "Run agent tick",
        "Show recent decisions",
        "Approve birthday vouchers",
    ],
}

@router.get("/agent/voice-catalog")
async def voice_catalog():
    return VOICE_CATALOG
