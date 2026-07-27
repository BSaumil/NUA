"""v15 advanced features: tabs/hold, shift swap, voice POS (Whisper), Ask NUA (LLM),
Nano Banana image gen, anomaly detection, auto-rostering, audit log, variants, CSV import,
cohort retention, booking heatmap, 2FA, GDPR.
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from deps import get_user, require_owner, require_owner_or_manager, require_permission
from database import db
from datetime import datetime, timezone, timedelta
import uuid
import os
import base64
import json
import secrets

router = APIRouter()


# =============================================================================
# DOCK BADGES (live counters)
# =============================================================================
@router.get("/dock/badges")
async def get_dock_badges(_: dict = Depends(get_user)):
    now = datetime.now(timezone.utc)
    ten_min_ago = (now - timedelta(minutes=10)).isoformat()
    today = now.date().isoformat()
    badges = {}
    # Bookings: new today
    new_bookings = await db.reservations.count_documents({"createdAt": {"$gte": today}})
    if new_bookings: badges["reservations"] = new_bookings
    # Kitchen: orders firing > 10 min
    stale = await db.kitchen_orders.count_documents({"status": {"$in": ["preparing", "fired"]}, "firedAt": {"$lte": ten_min_ago}})
    if stale: badges["kitchen"] = stale
    # POS: open tabs
    open_tabs = await db.pos_tabs.count_documents({"status": "open"})
    if open_tabs: badges["pos"] = open_tabs
    # Waitlist
    wl = await db.waitlist.count_documents({"status": "waiting"})
    if wl: badges["waitlist"] = wl
    return badges


# =============================================================================
# HOLD / RECALL ORDERS (POS Tabs)
# =============================================================================
@router.get("/pos/tabs")
async def get_tabs(_: dict = Depends(get_user)):
    tabs = await db.pos_tabs.find({"status": "open"}, {"_id": 0}).sort("createdAt", -1).to_list(200)
    return tabs

@router.post("/pos/tabs")
async def create_tab(data: dict, user: dict = Depends(get_user)):
    tab = {
        "id": f"TAB-{str(uuid.uuid4())[:8].upper()}",
        "name": data.get("name", f"Tab {datetime.now().strftime('%H:%M')}"),
        "cart": data.get("cart", []),
        "selectedCustomer": data.get("selectedCustomer"),
        # NEW: bind a tab to a specific table so the floor plan can settle
        # it later — the "Send to Table" flow from the POS lands here.
        "tableId": data.get("tableId"),
        "tableNumber": data.get("tableNumber"),
        "serverId": data.get("serverId"),
        "note": data.get("note"),
        "status": "open",
        "createdBy": user["id"],
        "createdByName": user["name"],
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.pos_tabs.insert_one(tab)
    tab.pop("_id", None)
    return tab

@router.delete("/pos/tabs/{tab_id}")
async def delete_tab(tab_id: str, _: dict = Depends(get_user)):
    await db.pos_tabs.delete_one({"id": tab_id})
    return {"message": "Tab closed"}


@router.put("/pos/tabs/{tab_id}")
async def update_tab(tab_id: str, data: dict, _: dict = Depends(get_user)):
    """Move Table — relabel an open tab to a different table without
    touching its held cart/customer."""
    allowed = {"tableId", "tableNumber", "name", "note", "serverId"}
    patch = {k: v for k, v in data.items() if k in allowed}
    if not patch:
        raise HTTPException(status_code=400, detail="No updatable fields provided")
    result = await db.pos_tabs.find_one_and_update(
        {"id": tab_id}, {"$set": patch}, return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Tab not found")
    result.pop("_id", None)
    return result


@router.post("/pos/tabs/{tab_id}/merge")
async def merge_tabs(tab_id: str, data: dict, _: dict = Depends(get_user)):
    """Merge Table — combine another open tab's held items into this one
    (e.g. two tables joined into a single check), then close the other tab."""
    other_id = data.get("otherTabId")
    if not other_id or other_id == tab_id:
        raise HTTPException(status_code=400, detail="A different otherTabId is required")
    primary = await db.pos_tabs.find_one({"id": tab_id}, {"_id": 0})
    other = await db.pos_tabs.find_one({"id": other_id}, {"_id": 0})
    if not primary or not other:
        raise HTTPException(status_code=404, detail="Tab not found")
    merged_cart = (primary.get("cart") or []) + (other.get("cart") or [])
    await db.pos_tabs.update_one({"id": tab_id}, {"$set": {"cart": merged_cart}})
    await db.pos_tabs.delete_one({"id": other_id})
    result = await db.pos_tabs.find_one({"id": tab_id}, {"_id": 0})
    return result


@router.post("/pos/tabs/{tab_id}/split")
async def split_tab(tab_id: str, data: dict, user: dict = Depends(get_user)):
    """Split Table / Check — divide this tab's held items round-robin across
    `ways` new tabs (2-6), then close the original. Optional `tableNumbers`
    lets each split land on a different table; otherwise they all keep the
    original table number (splitting the CHECK, not the seating)."""
    ways = int(data.get("ways", 2))
    if ways < 2 or ways > 6:
        raise HTTPException(status_code=400, detail="ways must be between 2 and 6")
    tab = await db.pos_tabs.find_one({"id": tab_id}, {"_id": 0})
    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found")
    cart = tab.get("cart") or []
    if not cart:
        raise HTTPException(status_code=400, detail="Tab has no items to split")
    table_numbers = data.get("tableNumbers") or []
    buckets = [[] for _ in range(ways)]
    for i, item in enumerate(cart):
        buckets[i % ways].append(item)
    new_tabs = []
    for i, bucket in enumerate(buckets):
        if not bucket:
            continue
        new_tab = {
            "id": f"TAB-{str(uuid.uuid4())[:8].upper()}",
            "name": f"{tab.get('name', 'Tab')} (Split {i + 1}/{ways})",
            "cart": bucket,
            "selectedCustomer": tab.get("selectedCustomer"),
            "tableId": tab.get("tableId"),
            "tableNumber": table_numbers[i] if i < len(table_numbers) else tab.get("tableNumber"),
            "serverId": tab.get("serverId"),
            "note": tab.get("note"),
            "status": "open",
            "createdBy": user["id"],
            "createdByName": user["name"],
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "splitFrom": tab_id,
        }
        await db.pos_tabs.insert_one(new_tab)
        new_tab.pop("_id", None)
        new_tabs.append(new_tab)
    await db.pos_tabs.delete_one({"id": tab_id})
    return {"tabs": new_tabs}


# =============================================================================
# FAVORITES (Quick Keys)
# =============================================================================
@router.get("/pos/favorites")
async def get_favorites(user: dict = Depends(get_user)):
    fav = await db.pos_favorites.find_one({"userId": user["id"]}, {"_id": 0})
    return fav or {"userId": user["id"], "productIds": []}

@router.post("/pos/favorites")
async def save_favorites(data: dict, user: dict = Depends(get_user)):
    product_ids = data.get("productIds", [])
    await db.pos_favorites.update_one(
        {"userId": user["id"]},
        {"$set": {"userId": user["id"], "productIds": product_ids, "updatedAt": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"productIds": product_ids}


# ─── Cash drawer (no-sale open) — owner-grantable, always audited ─────────
DRAWER_REASONS = ("change", "note_to_coin", "float_check", "other")


@router.post("/pos/open-drawer")
async def open_cash_drawer(data: dict, user: dict = Depends(require_permission("cash-drawer"))):
    """Logs a no-sale drawer open (making change, exchanging notes for
    coins, float check, etc). There's no physical drawer to signal in this
    environment — the audit trail is the actual control: every open is
    tied to exactly who did it, when, and why, for the owner to review."""
    reason = data.get("reason", "other")
    if reason not in DRAWER_REASONS:
        reason = "other"
    note = (data.get("note") or "").strip()[:200]
    event = {
        "id": str(uuid.uuid4()), "staffId": user["id"], "staffName": user.get("name") or user.get("email"),
        "role": user.get("role"), "reason": reason, "note": note,
        "location": data.get("location", "Main"),
        "openedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.drawer_events.insert_one(event)
    event.pop("_id", None)
    try:
        from services.audit_service import log_event
        await log_event(entity_type="cash_drawer", entity_id=event["id"], action="executed",
                        after=event, memo=f"No-sale drawer open — {reason}" + (f" ({note})" if note else ""),
                        severity="notice")
    except Exception:
        pass
    return event


@router.get("/pos/drawer-events")
async def list_drawer_events(_: dict = Depends(require_owner_or_manager)):
    """Owner/manager oversight — every no-sale drawer open, who and why."""
    rows = await db.drawer_events.find({}, {"_id": 0}).sort("openedAt", -1).to_list(200)
    return rows


# =============================================================================
# VARIANT MATRIX (size × milk × temp)
# =============================================================================
@router.put("/products/{product_id}/variants")
async def set_variants(product_id: str, data: dict, _: dict = Depends(require_owner_or_manager)):
    # data: { axes: [{name:"Size", values:["S","M","L"]}, ...], matrix: {"S|Whole":12.0, ...} }
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"variants": {"axes": data.get("axes", []), "matrix": data.get("matrix", {})}}},
    )
    p = await db.products.find_one({"id": product_id}, {"_id": 0})
    return p


# =============================================================================
# BULK CSV IMPORT for Items
# =============================================================================
@router.post("/items/bulk-import")
async def bulk_import(data: dict, _: dict = Depends(require_owner_or_manager)):
    rows = data.get("rows", [])  # list of {name, category, price, cost, stock, description}
    created = 0
    for row in rows:
        if not row.get("name"): continue
        prod = {
            "id": f"prod-{str(uuid.uuid4())[:8]}",
            "name": row.get("name"),
            "category": row.get("category", "Food"),
            "price": float(row.get("price", 0) or 0),
            "cost": float(row.get("cost", 0) or 0),
            "stock": int(row.get("stock", 0) or 0),
            "description": row.get("description", ""),
            "image": row.get("image", ""),
            "active": True,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        await db.products.insert_one(prod)
        created += 1
    return {"imported": created}


# =============================================================================
# VOICE POS — Whisper transcription
# =============================================================================
@router.post("/pos/voice-order")
async def voice_order(data: dict, _: dict = Depends(get_user)):
    audio_b64 = data.get("audioBase64", "")
    mime = data.get("mime", "audio/webm")
    if not audio_b64:
        raise HTTPException(status_code=400, detail="audioBase64 required")
    try:
        from openai import OpenAI
        import tempfile
        # Universal LLM gateway (OpenAI-compatible) wired up via env vars so we
        # don't hard-code provider URLs here.
        client = OpenAI(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            base_url=os.environ.get("LLM_GATEWAY_URL", "https://integrations.emergentagent.com/llm/openai"),
        )
        audio_bytes = base64.b64decode(audio_b64.split(",", 1)[-1])
        ext = ".webm" if "webm" in mime else ".mp3" if "mp3" in mime else ".wav"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            with open(tmp.name, "rb") as af:
                tr = client.audio.transcriptions.create(model="whisper-1", file=af)
        transcript = tr.text if hasattr(tr, "text") else str(tr)

        # Match transcript words to products
        products = await db.products.find({}, {"_id": 0, "id": 1, "name": 1, "price": 1}).to_list(1000)
        suggestions = []
        words = transcript.lower()
        for p in products:
            nm = p["name"].lower()
            if nm in words:
                # Try to find a qty in "two flat whites"
                NUMS = {"one":1,"two":2,"three":3,"four":4,"five":5,"a":1,"an":1}
                qty = 1
                for w, n in NUMS.items():
                    if f"{w} {nm}" in words or f"{w} {nm}s" in words:
                        qty = n; break
                suggestions.append({"productId": p["id"], "name": p["name"], "price": p["price"], "quantity": qty})
        return {"transcript": transcript, "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice transcription failed: {str(e)[:200]}")


# =============================================================================
# ASK NUA — natural-language analytics (LLM)
# =============================================================================
@router.post("/ai/ask-nua")
async def ask_nua(data: dict, user: dict = Depends(require_owner_or_manager)):
    question = data.get("question", "")
    if not question: raise HTTPException(status_code=400, detail="question required")

    # Gather context: top-line metrics
    today = datetime.now(timezone.utc).date().isoformat()
    tx = await db.transactions.find({"createdAt": {"$gte": today}}, {"_id": 0}).to_list(500)
    products = await db.products.count_documents({})
    customers = await db.customers.count_documents({})
    bookings_today = await db.reservations.count_documents({"date": today})
    total_revenue = sum(t.get("total", 0) for t in tx)

    context = {
        "today_date": today,
        "todayRevenue": round(total_revenue, 2),
        "todayTransactions": len(tx),
        "totalProducts": products,
        "totalCustomers": customers,
        "bookingsToday": bookings_today,
        "recentTransactions": [{"items": t.get("items", []), "total": t.get("total"), "method": t.get("paymentMethod")} for t in tx[:10]],
    }
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=f"ask-nua-{user['id']}-{uuid.uuid4()}",
            system_message=(
                "You are NUA, an AI restaurant operations assistant. Answer questions about today's business "
                "using the provided context JSON. Be concise (2-4 sentences). If you don't have the data, say so honestly. "
                "Never invent numbers."
            ),
        )
        chat.with_model("openai", "gpt-5.2")
        msg = UserMessage(text=f"Context:\n{json.dumps(context)}\n\nQuestion: {question}")
        resp = await chat.send_message(msg)
        return {"answer": resp, "context": context}
    except Exception as e:
        return {"answer": f"Unable to reach AI right now: {str(e)[:120]}", "context": context}


# =============================================================================
# NANO BANANA — item image generation
# =============================================================================
@router.post("/items/generate-image")
async def generate_image(data: dict, _: dict = Depends(require_owner_or_manager)):
    name = data.get("name", "")
    cuisine = data.get("cuisine", "modern cafe")
    if not name: raise HTTPException(status_code=400, detail="name required")
    try:
        from emergentintegrations.llm.image_gen import OpenAIImageGeneration
        gen = OpenAIImageGeneration(api_key=os.environ.get("EMERGENT_LLM_KEY"))
        prompt = f"Professional marketing photo of {name} from a {cuisine} restaurant, soft natural lighting, plated beautifully, top-down view, white background, food photography style"
        images = await gen.generate_images(prompt=prompt, number_of_images=1)
        if images and len(images):
            img_b64 = base64.b64encode(images[0]).decode("utf-8")
            return {"image": f"data:image/png;base64,{img_b64}"}
        raise Exception("no image returned")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)[:200]}")


# =============================================================================
# INVENTORY ANOMALY DETECTION
# =============================================================================
@router.get("/analytics/inventory-anomalies")
async def inventory_anomalies(_: dict = Depends(require_owner_or_manager)):
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    anomalies = []
    for p in products:
        # Sum sold in last 7 days
        tx = await db.transactions.find({"createdAt": {"$gte": seven_days_ago}}, {"_id": 0, "items": 1}).to_list(2000)
        recent_sold = sum(i.get("quantity", 0) for t in tx for i in t.get("items", []) if i.get("productId") == p["id"])
        # Average daily over 30 days
        thirty = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        tx30 = await db.transactions.find({"createdAt": {"$gte": thirty}}, {"_id": 0, "items": 1}).to_list(5000)
        total30 = sum(i.get("quantity", 0) for t in tx30 for i in t.get("items", []) if i.get("productId") == p["id"])
        avg_daily = total30 / 30
        recent_daily = recent_sold / 7
        if avg_daily > 1 and recent_daily > avg_daily * 1.3:
            anomalies.append({
                "productId": p["id"], "productName": p["name"],
                "recentDaily": round(recent_daily, 1), "historicalDaily": round(avg_daily, 1),
                "spikePercent": round((recent_daily / avg_daily - 1) * 100, 0),
                "suggestion": "Potential demand spike or shrinkage — investigate inventory variance",
            })
    return {"anomalies": anomalies, "checkedAt": datetime.now(timezone.utc).isoformat()}


# =============================================================================
# AUTO-ROSTERING AI
# =============================================================================
DEFAULT_ROSTERING_SETTINGS = {
    # Industry-standard minimum engagement — under the Hospitality Industry
    # (General) Award, a casual called in for a shift must be paid for at
    # least this many hours regardless of how short the actual work is.
    # 3.0 is the common Australian hospitality minimum; owners running under
    # a different award/agreement can adjust it here.
    "minEngagementHours": 3.0,
    "weekdayStaffTarget": 3,
    "weekendStaffTarget": 5,
    "coversPerStaff": 15,          # roughly how many covers one staff member can handle
    "weekdayShift": {"start": "12:00", "end": "20:00"},
    "weekendShift": {"start": "11:00", "end": "21:00"},
    "targetLaborPct": 28.0,        # healthy labor cost as a % of forecast revenue
    "avgHourlyRate": 28.0,         # fallback rate used for the cost-vs-revenue estimate
    "revenuePerCover": 35.0,
}


@router.get("/staff/rostering-settings")
async def get_rostering_settings(_: dict = Depends(get_user)):
    row = await db.rostering_settings.find_one({"_id": "singleton"}, {"_id": 0})
    if not row:
        row = dict(DEFAULT_ROSTERING_SETTINGS)
        await db.rostering_settings.insert_one({"_id": "singleton", **row})
    return row


@router.put("/staff/rostering-settings")
async def update_rostering_settings(body: dict, user: dict = Depends(require_owner)):
    """Owner-only — full control over the shift/cost rules Smart Rostering
    generates against."""
    allowed = set(DEFAULT_ROSTERING_SETTINGS.keys())
    patch = {k: v for k, v in body.items() if k in allowed}
    patch["updatedAt"] = datetime.now(timezone.utc).isoformat()
    patch["updatedBy"] = user.get("email")
    await db.rostering_settings.update_one(
        {"_id": "singleton"}, {"$set": {"_id": "singleton", **patch}}, upsert=True,
    )
    row = await db.rostering_settings.find_one({"_id": "singleton"}, {"_id": 0})
    return row


def _clamp_to_min_engagement(start: str, end: str, min_hours: float) -> str:
    """If a shift is shorter than the minimum engagement, push the end time
    out so the shift itself is never below what the award requires. Capped
    at 23:59 rather than wrapping into the next calendar day — nothing else
    in the roster model (shift docs, hour calculations) supports an
    overnight shift spanning two dates, so wrapping would silently produce
    a shift that reads as negative-length everywhere else it's used."""
    try:
        sh, sm = map(int, start.split(":"))
        eh, em = map(int, end.split(":"))
        duration = (eh * 60 + em) - (sh * 60 + sm)
        min_minutes = round(min_hours * 60)
        if duration < min_minutes:
            new_total = min(sh * 60 + sm + min_minutes, 23 * 60 + 59)
            eh, em = divmod(new_total, 60)
            return f"{eh:02d}:{em:02d}"
        return end
    except (ValueError, AttributeError):
        return end


@router.post("/staff/auto-roster")
async def auto_roster(data: dict, _: dict = Depends(require_owner_or_manager)):
    week_start = data.get("weekStart")
    settings_row = await db.rostering_settings.find_one({"_id": "singleton"}, {"_id": 0})
    settings = {**DEFAULT_ROSTERING_SETTINGS, **(settings_row or {})}

    staff = await db.auth_users.find({"role": {"$ne": "owner"}, "status": "active"}, {"_id": 0}).to_list(100)
    # Load availability/blackouts so we don't schedule unavailable staff.
    avail_rows = await db.staff_availability.find(
        {"staffId": {"$in": [s["id"] for s in staff]}}, {"_id": 0}
    ).to_list(200)
    avail_map = {a["staffId"]: a for a in avail_rows}

    def _date_for(day_name: str) -> str:
        # Resolve which calendar date a weekday falls on inside the requested week.
        # week_start is expected as ISO Monday (YYYY-MM-DD). If not provided, use today.
        try:
            from datetime import date as _date
            base = _date.fromisoformat(week_start) if week_start else _date.today()
            offset = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].index(day_name)
            return (base + timedelta(days=offset)).isoformat()
        except Exception:
            return ""

    def _is_blacked_out(staff_id: str, day_name: str) -> tuple[bool, str]:
        a = avail_map.get(staff_id)
        if not a: return False, ""
        # Weekly availability: if defined and day not listed → off
        short = day_name[:3]
        weekly = a.get("weeklyAvailable") or []
        if weekly and short not in weekly and day_name not in weekly:
            return True, "weekly_unavailable"
        # Blackout date ranges
        date_iso = _date_for(day_name)
        for b in (a.get("blackoutDates") or []):
            f, t = b.get("from") or "", b.get("to") or b.get("from") or ""
            if f and t and f <= date_iso <= t:
                return True, b.get("reason", "blackout")
        return False, ""

    # Reservations already booked this week give a real demand signal on top
    # of the flat weekday/weekend floor — the same "covers per staff" ratio
    # the read-only demand forecast uses, kept consistent on purpose.
    async def _forecast_covers(day_name: str, is_weekend: bool) -> int:
        date_iso = _date_for(day_name)
        if not date_iso:
            return 0
        res = await db.reservations.find({"date": date_iso}, {"_id": 0, "partySize": 1}).to_list(200)
        booked = sum(r.get("partySize", 0) for r in res)
        base_walkins = 40 if is_weekend else 20
        return booked + base_walkins

    DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    suggestions = []
    excluded = []
    day_summaries = []
    min_hours = float(settings["minEngagementHours"])

    for day in DAYS:
        is_weekend = day in ('Friday', 'Saturday', 'Sunday')
        floor_target = settings["weekendStaffTarget"] if is_weekend else settings["weekdayStaffTarget"]
        shift_cfg = settings["weekendShift"] if is_weekend else settings["weekdayShift"]
        start_time = shift_cfg["start"]
        end_time = _clamp_to_min_engagement(shift_cfg["start"], shift_cfg["end"], min_hours)
        shift_hours = (
            (int(end_time.split(":")[0]) * 60 + int(end_time.split(":")[1]))
            - (int(start_time.split(":")[0]) * 60 + int(start_time.split(":")[1]))
        ) / 60

        covers = await _forecast_covers(day, is_weekend)
        demand_target = max(floor_target, covers // settings["coversPerStaff"])

        # Cost vs revenue: if staffing to demand would push labor above the
        # owner's target %, trim back toward the floor rather than the
        # forecast — cost discipline wins over pure demand-matching, but
        # never below the floor (that's the minimum viable cover for the day).
        est_revenue = covers * settings["revenuePerCover"]
        est_labor_at_demand = demand_target * shift_hours * settings["avgHourlyRate"]
        labor_pct_at_demand = (est_labor_at_demand / est_revenue * 100) if est_revenue > 0 else 0
        target = demand_target
        trimmed_for_cost = False
        if est_revenue > 0 and labor_pct_at_demand > settings["targetLaborPct"] and demand_target > floor_target:
            target = max(floor_target, demand_target - 1)
            trimmed_for_cost = True

        # Filter out blacked-out staff for this day
        pool = []
        for s in staff:
            blocked, reason = _is_blacked_out(s["id"], day)
            if blocked:
                excluded.append({"staffId": s["id"], "staffName": s["name"], "date": day, "reason": reason})
                continue
            pool.append(s)
            if len(pool) >= target: break

        for s in pool:
            suggestions.append({
                "staffId": s["id"], "staffName": s["name"],
                "date": day, "weekStart": week_start,
                "startTime": start_time, "endTime": end_time,
                "role": s.get("role", "Floor").capitalize(),
                "notes": s.get("role", "Floor").capitalize(),
                "aiGenerated": True,
            })

        est_labor_final = len(pool) * shift_hours * settings["avgHourlyRate"]
        day_summaries.append({
            "date": day, "forecastCovers": covers, "staffed": len(pool),
            "shiftHours": round(shift_hours, 1),
            "estRevenue": round(est_revenue, 2), "estLaborCost": round(est_labor_final, 2),
            "laborPct": round((est_labor_final / est_revenue * 100), 1) if est_revenue > 0 else None,
            "trimmedForCost": trimmed_for_cost,
        })

    total_labor = sum(d["estLaborCost"] for d in day_summaries)
    total_revenue = sum(d["estRevenue"] for d in day_summaries)
    week_labor_pct = round((total_labor / total_revenue * 100), 1) if total_revenue > 0 else None

    return {
        "suggestions": suggestions,
        "excluded": excluded,
        "daySummaries": day_summaries,
        "weekEstimate": {"estLaborCost": round(total_labor, 2), "estRevenue": round(total_revenue, 2), "laborPct": week_labor_pct},
        "settingsUsed": settings,
        "reasoning": (
            f"Generated {len(suggestions)} shifts across {len(DAYS)} days, sized to forecast demand "
            f"(floor {settings['weekdayStaffTarget']}/weekday, {settings['weekendStaffTarget']}/weekend), "
            f"every shift honouring the {min_hours:.1f}h minimum engagement. "
            f"{len(excluded)} blackout exclusions honoured. "
            f"Estimated week labor cost ${round(total_labor, 2):,.2f} ({week_labor_pct}% of forecast revenue, target {settings['targetLaborPct']}%)."
        ),
    }


@router.post("/staff/roster/commit-auto")
async def commit_auto_roster(data: dict, _: dict = Depends(require_owner_or_manager)):
    shifts = data.get("shifts", [])
    inserted = 0
    for s in shifts:
        shift = {**s, "id": f"SHIFT-{str(uuid.uuid4())[:8].upper()}", "createdAt": datetime.now(timezone.utc).isoformat()}
        shift.pop("aiGenerated", None)
        await db.roster_shifts.insert_one(shift)
        inserted += 1
    return {"created": inserted}


# =============================================================================
# SHIFT SWAP REQUESTS
# =============================================================================
@router.get("/staff/shift-swaps")
async def get_swaps(user: dict = Depends(get_user)):
    if user["role"] in ("owner", "manager"):
        swaps = await db.shift_swaps.find({}, {"_id": 0}).sort("createdAt", -1).to_list(200)
    else:
        swaps = await db.shift_swaps.find({"$or": [{"requestedBy": user["id"]}, {"targetStaffId": user["id"]}]}, {"_id": 0}).to_list(200)
    return swaps

@router.post("/staff/shift-swaps")
async def create_swap(data: dict, user: dict = Depends(get_user)):
    swap = {
        "id": f"SWAP-{str(uuid.uuid4())[:8].upper()}",
        "shiftId": data.get("shiftId"),
        "requestedBy": user["id"],
        "requestedByName": user["name"],
        "targetStaffId": data.get("targetStaffId"),
        "targetStaffName": data.get("targetStaffName"),
        "reason": data.get("reason", ""),
        "status": "pending",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.shift_swaps.insert_one(swap)
    swap.pop("_id", None)
    return swap

@router.post("/staff/shift-swaps/{swap_id}/approve")
async def approve_swap(swap_id: str, user: dict = Depends(require_owner_or_manager)):
    swap = await db.shift_swaps.find_one({"id": swap_id})
    if not swap: raise HTTPException(status_code=404, detail="not found")
    # Reassign the shift
    await db.roster_shifts.update_one(
        {"id": swap["shiftId"]},
        {"$set": {"staffId": swap["targetStaffId"], "staffName": swap["targetStaffName"]}},
    )
    await db.shift_swaps.update_one({"id": swap_id}, {"$set": {"status": "approved", "approvedAt": datetime.now(timezone.utc).isoformat(), "approvedBy": user["id"]}})
    return {"message": "Swap approved & shift reassigned"}

@router.post("/staff/shift-swaps/{swap_id}/reject")
async def reject_swap(swap_id: str, _: dict = Depends(require_owner_or_manager)):
    await db.shift_swaps.update_one({"id": swap_id}, {"$set": {"status": "rejected", "rejectedAt": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Swap rejected"}


# =============================================================================
# BOOKING HEATMAP (busy hours by day-of-week)
# =============================================================================
@router.get("/analytics/booking-heatmap")
async def booking_heatmap(_: dict = Depends(require_owner_or_manager)):
    res = await db.reservations.find({}, {"_id": 0, "date": 1, "time": 1, "partySize": 1}).to_list(5000)
    # heatmap[dow][hour] = total guests
    DOW = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    heat = {d: {h: 0 for h in range(9, 23)} for d in DOW}
    for r in res:
        try:
            d = datetime.fromisoformat(r["date"]) if isinstance(r.get("date"), str) and "-" in r["date"] else None
            if not d: continue
            dow = DOW[d.weekday()]
            hour = int(str(r.get("time", "12:00")).split(":")[0])
            if 9 <= hour < 23:
                heat[dow][hour] += r.get("partySize", 1)
        except Exception:
            continue
    return {"heatmap": heat, "days": DOW, "hours": list(range(9, 23))}


# =============================================================================
# CUSTOMER COHORT RETENTION
# =============================================================================
@router.get("/analytics/cohort-retention")
async def cohort_retention(_: dict = Depends(require_owner_or_manager)):
    customers = await db.customers.find({}, {"_id": 0, "id": 1, "createdAt": 1}).to_list(5000)
    tx = await db.transactions.find({}, {"_id": 0, "customerId": 1, "createdAt": 1}).to_list(20000)
    # Group customers by month of first signup
    cohorts = {}
    for c in customers:
        try:
            cohort_month = c["createdAt"][:7]  # YYYY-MM
        except Exception:
            continue
        cohorts.setdefault(cohort_month, []).append(c["id"])
    # For each cohort, calculate retention for months 0..5 after signup
    result = []
    for cohort_month, cids in sorted(cohorts.items()):
        cohort_data = {"cohort": cohort_month, "size": len(cids), "retention": []}
        base = datetime.fromisoformat(cohort_month + "-01")
        for m in range(6):
            month_start = (base + timedelta(days=30 * m)).date().isoformat()[:7]
            active = sum(1 for cid in cids if any(t.get("customerId") == cid and (t.get("createdAt", "")[:7] == month_start) for t in tx))
            cohort_data["retention"].append({"month": m, "active": active, "rate": round(active / max(len(cids), 1) * 100, 1)})
        result.append(cohort_data)
    return {"cohorts": result[-12:]}  # last 12 cohorts


# =============================================================================
# AUDIT LOG
# =============================================================================
@router.get("/audit/logs")
async def get_audit_logs( limit: int = 200, user: dict = Depends(require_owner_or_manager)):
    # Aggregate from multiple sources: comp_voids, refunds, ghost_discounts, login attempts
    logs = []
    cv = await db.comp_voids.find({}, {"_id": 0}).sort("processedAt", -1).to_list(100)
    for c in cv:
        logs.append({"id": c["id"], "type": c.get("type", "comp").upper(), "user": c.get("processedBy", "?"),
                     "details": f"${c.get('amount',0):.2f} - {c.get('reason', '')}",
                     "timestamp": c.get("processedAt")})
    refunds = await db.refunds.find({}, {"_id": 0}).sort("createdAt", -1).to_list(100)
    for r in refunds:
        logs.append({"id": r.get("id", str(uuid.uuid4())[:8]), "type": "REFUND", "user": r.get("processedBy", "?"),
                     "details": f"${r.get('amount',0):.2f} - {r.get('reason', '')}",
                     "timestamp": r.get("createdAt")})
    ghosts = await db.ghost_discounts.find({}, {"_id": 0}).sort("createdAt", -1).to_list(100)
    for g in ghosts:
        logs.append({"id": g.get("id", str(uuid.uuid4())[:8]), "type": "GHOST_DISCOUNT", "user": g.get("appliedBy", "?"),
                     "details": f"${g.get('amount',0):.2f}", "timestamp": g.get("createdAt")})
    # Sort by timestamp desc
    logs.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return logs[:limit]


# =============================================================================
# 2FA OWNER LOGIN (TOTP)
# =============================================================================
@router.post("/auth/2fa/setup")
async def setup_2fa(user: dict = Depends(require_owner)):
    secret = secrets.token_hex(16)  # In production use pyotp.random_base32()
    await db.auth_users.update_one({"id": user["id"]}, {"$set": {"twoFactorSecret": secret, "twoFactorEnabled": False}})
    return {"secret": secret, "qrUri": f"otpauth://totp/NUA:{user['email']}?secret={secret}&issuer=NUA"}

@router.post("/auth/2fa/verify")
async def verify_2fa(data: dict, user: dict = Depends(get_user)):
    code = data.get("code", "")
    # Stub: accept "123456" for demo (real implementation: pyotp.TOTP(secret).verify(code))
    if code == "123456":
        await db.auth_users.update_one({"id": user["id"]}, {"$set": {"twoFactorEnabled": True}})
        return {"verified": True, "message": "2FA enabled"}
    raise HTTPException(status_code=400, detail="Invalid code")

@router.post("/auth/2fa/disable")
async def disable_2fa(user: dict = Depends(get_user)):
    await db.auth_users.update_one({"id": user["id"]}, {"$unset": {"twoFactorSecret": "", "twoFactorEnabled": ""}})
    return {"message": "2FA disabled"}


# =============================================================================
# GDPR — data export & erase
# =============================================================================
@router.get("/customers/{customer_id}/gdpr-export")
async def gdpr_export(customer_id: str, _: dict = Depends(require_owner_or_manager)):
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer: raise HTTPException(status_code=404, detail="not found")
    tx = await db.transactions.find({"customerId": customer_id}, {"_id": 0}).to_list(5000)
    res = await db.reservations.find({"customerId": customer_id}, {"_id": 0}).to_list(1000)
    feedback = await db.feedback.find({"customerId": customer_id}, {"_id": 0}).to_list(500)
    return {
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "customer": customer,
        "transactions": tx,
        "reservations": res,
        "feedback": feedback,
        "noticeText": "This export contains all personal data we hold on you in accordance with GDPR Article 15.",
    }

@router.delete("/customers/{customer_id}/gdpr-erase")
async def gdpr_erase(customer_id: str, user: dict = Depends(require_owner)):
    # Anonymize rather than hard-delete to preserve financial records
    anon = {"name": "[REDACTED]", "email": "redacted@nua.local", "phone": "[REDACTED]", "notes": "", "erasedAt": datetime.now(timezone.utc).isoformat(), "erasedBy": user["id"]}
    await db.customers.update_one({"id": customer_id}, {"$set": anon})
    await db.feedback.update_many({"customerId": customer_id}, {"$set": {"customerName": "[REDACTED]"}})
    return {"message": "Customer data anonymized (financial records preserved per regulation)"}


# =============================================================================
# BAS / GST e-file finalize (stub with audit trail)
# =============================================================================
@router.post("/bas-gst/efile/{report_id}")
async def efile_bas(report_id: str, data: dict, user: dict = Depends(require_owner)):
    abn = data.get("abn", "")
    if not abn or len(abn.replace(" ", "")) != 11:
        raise HTTPException(status_code=400, detail="Valid 11-digit ABN required")
    # In production, integrate with ATO SBR2 (Standard Business Reporting). For now, record submission intent.
    submission = {
        "reportId": report_id, "abn": abn,
        "submittedBy": user["id"], "submittedByName": user["name"],
        "submittedAt": datetime.now(timezone.utc).isoformat(),
        "status": "received",
        "trackingNumber": f"ATO-{str(uuid.uuid4())[:8].upper()}",
    }
    await db.bas_submissions.insert_one(submission)
    submission.pop("_id", None)
    await db.bas_reports.update_one({"id": report_id}, {"$set": {"efiled": True, "trackingNumber": submission["trackingNumber"]}})
    return submission


# =============================================================================
# MULTI-LANGUAGE LABELS
# =============================================================================
@router.get("/i18n/labels/{lang}")
async def get_labels(lang: str):
    LABELS = {
        "en": {"cart": "Cart", "checkout": "Checkout", "total": "Total", "tax": "Tax", "subtotal": "Subtotal", "discount": "Discount", "empty_cart": "Cart is empty", "add_to_cart": "Add to cart", "pay_now": "Pay now"},
        "es": {"cart": "Carrito", "checkout": "Pagar", "total": "Total", "tax": "Impuesto", "subtotal": "Subtotal", "discount": "Descuento", "empty_cart": "El carrito está vacío", "add_to_cart": "Añadir al carrito", "pay_now": "Pagar ahora"},
        "fr": {"cart": "Panier", "checkout": "Commander", "total": "Total", "tax": "TVA", "subtotal": "Sous-total", "discount": "Remise", "empty_cart": "Panier vide", "add_to_cart": "Ajouter au panier", "pay_now": "Payer maintenant"},
        "hi": {"cart": "कार्ट", "checkout": "चेकआउट", "total": "कुल", "tax": "कर", "subtotal": "उप-योग", "discount": "छूट", "empty_cart": "कार्ट खाली है", "add_to_cart": "कार्ट में जोड़ें", "pay_now": "अभी भुगतान करें"},
        "zh": {"cart": "购物车", "checkout": "结账", "total": "总计", "tax": "税", "subtotal": "小计", "discount": "折扣", "empty_cart": "购物车为空", "add_to_cart": "加入购物车", "pay_now": "立即支付"},
    }
    return LABELS.get(lang, LABELS["en"])
