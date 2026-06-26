"""Phase E + F — Deeper Ash autonomy + Nomni-gap features.

E: auto-publish roster (within budget), auto-confirm SMS queue, auto-VIP tagging,
voice intents 'void last item' / 'raise espresso 50 cents'
F: AI Phone Agent, auto-PO generation, live menu A/B testing, guest 'your usual'
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from deps import get_user, require_owner, require_owner_or_manager
from database import db
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict
import uuid
import os
import json

router = APIRouter()


# =============================================================================
# CONFIG — owner-controlled thresholds for Ash autonomy
# =============================================================================
DEFAULT_AUTONOMY = {
    "autoPublishRoster": False,
    "autoPublishBudgetCap": 5000.0,
    "autoConfirmSMS": True,
    "autoVipThresholdSpend": 500.0,
    "autoVipThresholdVisits": 10,
    "autoReorderThreshold": 5,
    "abTestingEnabled": True,
}


@router.get("/agent/autonomy")
async def get_autonomy(_: dict = Depends(get_user)):
    cfg = await db.agent_autonomy.find_one({"id": "default"}, {"_id": 0})
    return cfg or {"id": "default", **DEFAULT_AUTONOMY}


@router.put("/agent/autonomy")
async def update_autonomy(data: dict, _: dict = Depends(require_owner)):
    update = {k: v for k, v in data.items() if k in DEFAULT_AUTONOMY}
    await db.agent_autonomy.update_one(
        {"id": "default"}, {"$set": {"id": "default", **update}}, upsert=True
    )
    return {"updated": update}


# =============================================================================
# E1 — AUTO-VIP TAGGING
# =============================================================================
async def auto_tag_vips():
    cfg = await db.agent_autonomy.find_one({"id": "default"}, {"_id": 0}) or DEFAULT_AUTONOMY
    promoted = []
    customers = await db.customers.find({}, {"_id": 0}).to_list(5000)
    for c in customers:
        spend = float(c.get("totalSpend", 0) or 0)
        visits = int(c.get("totalVisits", 0) or 0)
        current_tier = c.get("membershipTier", "Bronze")
        if spend >= cfg.get("autoVipThresholdSpend", 500) and visits >= cfg.get("autoVipThresholdVisits", 10):
            if current_tier != "VIP":
                await db.customers.update_one({"id": c["id"]}, {"$set": {"membershipTier": "VIP", "vipPromotedAt": datetime.now(timezone.utc).isoformat()}})
                promoted.append({"id": c["id"], "name": c.get("name"), "from": current_tier})
    return promoted


# =============================================================================
# E2 — AUTO-CONFIRM SMS QUEUE
# =============================================================================
@router.get("/comms/sms-queue")
async def get_sms_queue(_: dict = Depends(require_owner_or_manager)):
    q = await db.sms_queue.find({}, {"_id": 0}).sort("createdAt", -1).to_list(200)
    return q


async def queue_sms(to: str, name: str, body: str, kind: str = "manual"):
    msg = {
        "id": f"SMS-{str(uuid.uuid4())[:8].upper()}",
        "to": to, "name": name, "body": body, "kind": kind,
        "status": "queued",  # will be 'sent' after Twilio integration
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.sms_queue.insert_one(msg)
    msg.pop("_id", None)
    return msg


@router.post("/comms/auto-confirm/{reservation_id}")
async def auto_confirm_reservation(reservation_id: str, _: dict = Depends(get_user)):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    phone = res.get("guestPhone") or res.get("phone") or res.get("customerPhone") or ""
    if not phone:
        raise HTTPException(status_code=400, detail="No phone on reservation")
    name = res.get("guestName") or res.get("customerName") or "guest"
    body = (f"Hi {name}, your booking for {res.get('partySize','?')} on "
            f"{res.get('date','?')} at {res.get('time','?')} is confirmed at NUA. Reply C to cancel.")
    msg = await queue_sms(phone, name, body, "reservation_confirm")
    await db.reservations.update_one({"id": reservation_id}, {"$set": {"confirmationSent": True, "confirmationAt": msg["createdAt"]}})
    return msg


# =============================================================================
# E3 — VOICE COMMAND ROUTER EXTENSIONS (void last item, raise price)
# =============================================================================
@router.post("/agent/voice-extended")
async def voice_extended(data: dict, user: dict = Depends(get_user)):
    """Extended voice routing for commands the basic router doesn't handle.
    Specifically: 'void last item', 'raise espresso 50 cents', '86 the croissant'."""
    text = (data.get("text") or "").lower().strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")

    import re
    # Pattern 1: "void last item" / "remove last"
    if re.search(r"\b(void|remove|delete)\s+(the\s+)?last\s+(item|product|line)?\b", text):
        return {"intent": "void_last_item", "instruction": {"action": "void_last_item"}}

    # Pattern 2: "raise espresso by 50 cents" / "drop latte 1 dollar"
    # Try cents/dollars suffix FIRST so "50 cents" doesn't match plain "$50"
    m = re.search(r"\b(raise|drop|lower|increase|reduce)\s+(.+?)\s+(?:by\s+)?(\d+(?:\.\d{1,2})?\s*cents?|\d+(?:\.\d{1,2})?\s*dollars?|\$\d+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\b", text)
    if m:
        direction = 1 if m.group(1) in ("raise", "increase") else -1
        product_name = m.group(2).strip()
        amount_str = m.group(3).strip()
        # Parse amount
        amount_str_lower = amount_str.lower().replace("$", "").strip()
        nums = re.findall(r"\d+(?:\.\d+)?", amount_str_lower)
        if not nums:
            return {"intent": "price_change", "error": "Could not parse amount"}
        n = float(nums[0])
        if "cent" in amount_str_lower:
            amount = n / 100
        elif "dollar" in amount_str_lower or amount_str.startswith("$"):
            amount = n
        else:
            # Plain number — if integer < 10 assume dollars, otherwise cents
            amount = n if n < 100 else n / 100
        delta = direction * amount
        # Find product
        product = await db.products.find_one({"name": {"$regex": f"^{product_name}", "$options": "i"}}, {"_id": 0})
        if not product:
            return {"intent": "price_change", "error": f"Product '{product_name}' not found"}
        new_price = max(0.01, round(float(product.get("price", 0)) + delta, 2))
        if user["role"] in ("owner", "manager"):
            await db.products.update_one({"id": product["id"]}, {"$set": {"price": new_price, "lastPriceChange": {"by": user["id"], "delta": delta, "at": datetime.now(timezone.utc).isoformat(), "reason": "voice command"}}})
            await db.agent_decisions.insert_one({
                "id": f"AGT-{str(uuid.uuid4())[:8].upper()}",
                "actionType": "price_change",
                "summary": f"Price of {product['name']} changed by ${delta:+.2f} → ${new_price:.2f}",
                "payload": {"productId": product["id"], "delta": delta, "newPrice": new_price, "by": "voice"},
                "status": "executed",
                "createdAt": datetime.now(timezone.utc).isoformat(),
            })
            return {"intent": "price_change", "productId": product["id"], "productName": product["name"], "oldPrice": product["price"], "newPrice": new_price}
        return {"intent": "price_change", "error": "Owner/Manager only"}

    # Pattern 3: "86 the croissant" — mark out-of-stock
    m = re.search(r"\b86\s+(the\s+)?(.+?)$", text)
    if m:
        product_name = m.group(2).strip().rstrip("s")
        product = await db.products.find_one({"name": {"$regex": f"^{product_name}", "$options": "i"}}, {"_id": 0})
        if product and user["role"] in ("owner", "manager"):
            await db.products.update_one({"id": product["id"]}, {"$set": {"stock": 0, "eightySixed": True, "eightySixedAt": datetime.now(timezone.utc).isoformat()}})
            return {"intent": "eighty_six", "productId": product["id"], "productName": product["name"]}

    return {"intent": "unknown", "transcript": text}


# =============================================================================
# E4 — AUTO-PUBLISH ROSTER (within budget cap)
# =============================================================================
@router.post("/agent/auto-publish-roster")
async def auto_publish_roster(data: dict, request: Request, _: dict = Depends(require_owner_or_manager)):
    cfg = await db.agent_autonomy.find_one({"id": "default"}, {"_id": 0}) or DEFAULT_AUTONOMY
    if not cfg.get("autoPublishRoster", False):
        raise HTTPException(status_code=400, detail="Auto-publish roster disabled in autonomy config")

    week_start = data.get("weekStart")
    # Generate via existing auto_roster
    from routes.v15_features import auto_roster
    proposal = await auto_roster({"weekStart": week_start}, request)
    shifts = proposal.get("suggestions", []) if isinstance(proposal, dict) else []
    # Estimate cost
    staff_pay = {s["id"]: s.get("payRate", 0) for s in await db.auth_users.find({}, {"_id": 0}).to_list(500)}
    cost = 0.0
    for s in shifts:
        start = list(map(int, s.get("startTime", "0:0").split(":")))
        end = list(map(int, s.get("endTime", "0:0").split(":")))
        hours = max((end[0] + end[1] / 60) - (start[0] + start[1] / 60), 0)
        cost += hours * float(staff_pay.get(s.get("staffId"), 0))

    cap = float(cfg.get("autoPublishBudgetCap", 5000))
    if cost > cap:
        return {"published": False, "reason": f"Estimated cost ${cost:.2f} exceeds cap ${cap:.2f}", "estimatedCost": cost}

    # Commit
    for s in shifts:
        shift = {**s, "id": f"SHIFT-{str(uuid.uuid4())[:8].upper()}", "createdAt": datetime.now(timezone.utc).isoformat(), "autoPublished": True}
        shift.pop("aiGenerated", None)
        await db.roster_shifts.insert_one(shift)
    await db.agent_decisions.insert_one({
        "id": f"AGT-{str(uuid.uuid4())[:8].upper()}",
        "actionType": "roster_auto_published",
        "summary": f"Auto-published {len(shifts)} shifts (cost ${cost:.2f} within ${cap:.2f} cap)",
        "payload": {"shiftCount": len(shifts), "cost": cost},
        "status": "executed",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })
    return {"published": True, "shifts": len(shifts), "estimatedCost": cost}


# =============================================================================
# F1 — AI PHONE AGENT (inbound voice agent)
# =============================================================================
@router.get("/phone-agent/calls")
async def get_calls(_: dict = Depends(require_owner_or_manager)):
    calls = await db.phone_calls.find({}, {"_id": 0}).sort("startedAt", -1).to_list(200)
    return calls


@router.post("/phone-agent/simulate")
async def simulate_call(data: dict, _: dict = Depends(get_user)):
    """Simulate an inbound call. Sends transcript to LLM, returns intent + actions taken."""
    caller = data.get("caller", "Unknown")
    transcript = data.get("transcript", "").strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="transcript required")
    call = {
        "id": f"CALL-{str(uuid.uuid4())[:8].upper()}",
        "caller": caller, "transcript": transcript,
        "startedAt": datetime.now(timezone.utc).isoformat(),
    }

    # Classify with LLM
    intent_result = {"intent": "unknown", "actions": []}
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=f"phone-{call['id']}",
            system_message=(
                "You are an AI phone agent for NUA restaurant. Given a caller transcript, return STRICT JSON: "
                '{"intent":"reservation|order|inquiry|other","details":{"partySize":2,"date":"YYYY-MM-DD","time":"19:00","name":"...","items":[{"name":"...","qty":1}],"question":"..."}}. '
                "Only fill details that match. Today is " + datetime.now().date().isoformat()
            ),
        )
        chat.with_model("openai", "gpt-5.2")
        resp = await chat.send_message(UserMessage(text=transcript))
        try:
            parsed = json.loads(resp.strip().strip("`").strip())
        except Exception:
            import re
            m = re.search(r"\{.*\}", resp, re.DOTALL)
            parsed = json.loads(m.group(0)) if m else {"intent": "unknown"}
        intent_result["intent"] = parsed.get("intent", "unknown")
        details = parsed.get("details", {})

        # Take action based on intent
        if parsed.get("intent") == "reservation" and details.get("date"):
            r = {
                "id": f"RES-{str(uuid.uuid4())[:8].upper()}",
                "guestName": details.get("name") or caller,
                "guestPhone": caller,
                "partySize": int(details.get("partySize", 2) or 2),
                "date": details.get("date"),
                "time": details.get("time", "19:00"),
                "status": "confirmed",
                "source": "ai_phone_agent",
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            await db.reservations.insert_one(r)
            intent_result["actions"].append({"action": "reservation_created", "id": r["id"]})
            # Auto-confirm SMS
            await queue_sms(caller, r["guestName"], f"Booking confirmed: {r['date']} at {r['time']} for {r['partySize']} at NUA.", "phone_agent")
        elif parsed.get("intent") == "order":
            items = details.get("items", [])
            intent_result["actions"].append({"action": "order_drafted", "items": items})
        elif parsed.get("intent") == "inquiry":
            intent_result["actions"].append({"action": "inquiry_logged", "question": details.get("question", "")})
        intent_result["details"] = details
    except Exception as e:
        intent_result["error"] = str(e)[:200]

    call.update(intent_result)
    call["endedAt"] = datetime.now(timezone.utc).isoformat()
    await db.phone_calls.insert_one(call)
    call.pop("_id", None)
    return call


# =============================================================================
# F2 — AUTO PO GENERATION
# =============================================================================
@router.get("/purchase-orders")
async def get_pos_list(_: dict = Depends(require_owner_or_manager)):
    pos = await db.purchase_orders.find({}, {"_id": 0}).sort("createdAt", -1).to_list(200)
    return pos


@router.post("/purchase-orders/generate")
async def generate_po(user: dict = Depends(require_owner_or_manager)):
    """Auto-generate purchase orders from low-stock products grouped by supplier."""
    cfg = await db.agent_autonomy.find_one({"id": "default"}, {"_id": 0}) or DEFAULT_AUTONOMY
    threshold = int(cfg.get("autoReorderThreshold", 5))
    low = await db.products.find({"stock": {"$lte": threshold}, "active": {"$ne": False}}, {"_id": 0}).to_list(500)

    # Group by supplier (fallback "Default Supplier")
    by_supplier = defaultdict(list)
    for p in low:
        sup = p.get("supplier") or "Default Supplier"
        # Reorder qty = (reorderLevel or 50) - stock
        target = int(p.get("reorderLevel", 50))
        qty = max(target - int(p.get("stock", 0)), 1)
        by_supplier[sup].append({"productId": p["id"], "productName": p["name"], "currentStock": p.get("stock", 0), "orderQty": qty, "unitCost": p.get("cost", 0)})

    pos_list = []
    for sup, items in by_supplier.items():
        total = sum((i["orderQty"] * float(i["unitCost"] or 0)) for i in items)
        po = {
            "id": f"PO-{str(uuid.uuid4())[:8].upper()}",
            "supplier": sup,
            "items": items,
            "totalCost": round(total, 2),
            "status": "draft",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "createdBy": user["id"],
        }
        await db.purchase_orders.insert_one(po)
        po.pop("_id", None)
        pos_list.append(po)
    if pos_list:
        await db.agent_decisions.insert_one({
            "id": f"AGT-{str(uuid.uuid4())[:8].upper()}",
            "actionType": "po_generated",
            "summary": f"Auto-generated {len(pos_list)} purchase orders for {len(low)} low-stock items",
            "payload": {"supplierCount": len(pos_list), "itemCount": len(low)},
            "status": "executed",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })
    return {"created": len(pos_list), "purchaseOrders": pos_list}


@router.post("/purchase-orders/{po_id}/{action}")
async def update_po(po_id: str, action: str, _: dict = Depends(require_owner_or_manager)):
    if action not in ("approve", "send", "receive", "cancel"):
        raise HTTPException(status_code=400, detail="Invalid action")
    status_map = {"approve": "approved", "send": "sent", "receive": "received", "cancel": "cancelled"}
    update = {"status": status_map[action], f"{action}dAt": datetime.now(timezone.utc).isoformat()}
    po = await db.purchase_orders.find_one_and_update({"id": po_id}, {"$set": update}, return_document=True)
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    # On receive: increment stock
    if action == "receive":
        for item in po.get("items", []):
            await db.products.update_one({"id": item["productId"]}, {"$inc": {"stock": item.get("orderQty", 0)}})
    po.pop("_id", None)
    return po


# =============================================================================
# F3 — LIVE MENU A/B TESTING
# =============================================================================
@router.get("/ab-tests")
async def get_ab_tests(_: dict = Depends(require_owner_or_manager)):
    tests = await db.ab_tests.find({}, {"_id": 0}).sort("createdAt", -1).to_list(100)
    return tests


@router.post("/ab-tests")
async def create_ab_test(data: dict, _: dict = Depends(require_owner_or_manager)):
    test = {
        "id": f"AB-{str(uuid.uuid4())[:8].upper()}",
        "productId": data.get("productId"),
        "variantA": data.get("variantA", {}),  # { name, price, description }
        "variantB": data.get("variantB", {}),
        "metric": data.get("metric", "conversions"),  # conversions | revenue | aov
        "status": "running",
        "exposures": {"A": 0, "B": 0},
        "conversions": {"A": 0, "B": 0},
        "revenue": {"A": 0.0, "B": 0.0},
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.ab_tests.insert_one(test)
    test.pop("_id", None)
    return test


@router.post("/ab-tests/{test_id}/exposure")
async def record_exposure(test_id: str, data: dict):
    """Public-facing endpoint — table-side QR / public menu calls this."""
    variant = data.get("variant", "A")
    if variant not in ("A", "B"):
        raise HTTPException(status_code=400, detail="variant must be A or B")
    await db.ab_tests.update_one({"id": test_id}, {"$inc": {f"exposures.{variant}": 1}})
    return {"recorded": True}


@router.post("/ab-tests/{test_id}/conversion")
async def record_conversion(test_id: str, data: dict):
    """Called when a customer adds the variant to cart / purchases."""
    variant = data.get("variant", "A")
    revenue = float(data.get("revenue", 0) or 0)
    if variant not in ("A", "B"):
        raise HTTPException(status_code=400, detail="variant must be A or B")
    await db.ab_tests.update_one({"id": test_id}, {"$inc": {f"conversions.{variant}": 1, f"revenue.{variant}": revenue}})
    return {"recorded": True}


@router.post("/ab-tests/{test_id}/conclude")
async def conclude_test(test_id: str, _: dict = Depends(require_owner_or_manager)):
    test = await db.ab_tests.find_one({"id": test_id}, {"_id": 0})
    if not test:
        raise HTTPException(status_code=404, detail="Not found")
    # Winner = higher conversion rate
    ea, eb = max(test["exposures"]["A"], 1), max(test["exposures"]["B"], 1)
    ca, cb = test["conversions"]["A"], test["conversions"]["B"]
    rate_a, rate_b = ca / ea, cb / eb
    winner = "A" if rate_a >= rate_b else "B"
    await db.ab_tests.update_one({"id": test_id}, {"$set": {"status": "concluded", "winner": winner, "concludedAt": datetime.now(timezone.utc).isoformat()}})
    return {"winner": winner, "rates": {"A": rate_a, "B": rate_b}}


# =============================================================================
# F4 — GUEST PREDICTIVE "YOUR USUAL"
# =============================================================================
@router.get("/customers/{customer_id}/your-usual")
async def your_usual(customer_id: str, _: dict = Depends(get_user)):
    # Find customer's most-frequent items from transactions
    tx = await db.transactions.find({"customerId": customer_id}, {"_id": 0, "items": 1, "createdAt": 1}).sort("createdAt", -1).limit(20).to_list(20)
    if not tx:
        return {"items": [], "reason": "no purchase history"}
    counter = Counter()
    prices = {}
    images = {}
    for t in tx:
        for it in t.get("items", []):
            pid = it.get("productId")
            if not pid: continue
            counter[pid] += int(it.get("quantity", 1))
            prices[pid] = it.get("price")
    top_ids = [pid for pid, _ in counter.most_common(3)]
    products = []
    for pid in top_ids:
        p = await db.products.find_one({"id": pid}, {"_id": 0})
        if p:
            products.append({"id": pid, "name": p.get("name"), "price": p.get("price"), "image": p.get("image"), "category": p.get("category"), "frequency": counter[pid]})
    return {"items": products, "basedOn": len(tx), "reason": f"Most-frequent items from last {len(tx)} orders"}


# =============================================================================
# Hook into Ash agent tick — add E+F autonomous rules
# =============================================================================
@router.post("/agent/tick-extended")
async def tick_extended(request: Request, _: dict = Depends(require_owner_or_manager)):
    """Runs Phase E + F autonomous decisions in addition to base tick."""
    cfg = await db.agent_autonomy.find_one({"id": "default"}, {"_id": 0}) or DEFAULT_AUTONOMY
    out = {"decisions": []}

    # 1. Auto-VIP tagging
    promoted = await auto_tag_vips()
    if promoted:
        d = {
            "id": f"AGT-{str(uuid.uuid4())[:8].upper()}",
            "actionType": "vip_promoted",
            "summary": f"Auto-promoted {len(promoted)} customers to VIP",
            "payload": {"promoted": promoted},
            "status": "executed",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        await db.agent_decisions.insert_one(d)
        out["decisions"].append({**d})

    # 2. Auto-confirm SMS for pending reservations
    if cfg.get("autoConfirmSMS", True):
        pending = await db.reservations.find({"confirmationSent": {"$ne": True}, "phone": {"$exists": True, "$ne": ""}}, {"_id": 0}).to_list(50)
        for r in pending:
            try:
                await auto_confirm_reservation(r["id"], request)
            except Exception:
                pass
        if pending:
            d = {
                "id": f"AGT-{str(uuid.uuid4())[:8].upper()}",
                "actionType": "sms_auto_confirmed",
                "summary": f"Queued {len(pending)} reservation confirmation SMS",
                "payload": {"count": len(pending)},
                "status": "executed",
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
            await db.agent_decisions.insert_one(d)
            out["decisions"].append({**d})

    # 3. Auto-PO generation when many low-stock items
    threshold = int(cfg.get("autoReorderThreshold", 5))
    low_count = await db.products.count_documents({"stock": {"$lte": threshold}, "active": {"$ne": False}})
    if low_count >= 3:  # auto-generate when 3+ low
        try:
            r = await generate_po(request)
            out["decisions"].append({"actionType": "po_generated", "summary": f"Auto-generated {r['created']} POs for {low_count} low-stock items"})
        except Exception:
            pass

    return out
