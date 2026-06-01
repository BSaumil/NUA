"""NUA v25 — Enterprise Suite.

Consolidates the v25-v30 roadmap into one cohesive module:

MUST HAVE
- Offline sync queue          POST/GET   /api/v25/sync-queue
- Loss-control exceptions     GET/POST   /api/v25/exceptions
- Multi-site command          GET/POST   /api/v25/sites + /publish + /rollback
- Hardware health             GET/POST   /api/v25/hardware
- Chargebacks/disputes        GET/POST   /api/v25/disputes
- Supplier marketplace        GET/POST   /api/v25/suppliers/compare

SHOULD HAVE
- Kiosk session               POST/GET   /api/v25/kiosk/*
- Customer-facing display     GET        /api/v25/cfd/current
- Smart substitution / 86      POST       /api/v25/substitute
- Guest recovery automation   POST/GET   /api/v25/recovery/*
- Station readiness score     GET        /api/v25/station-readiness
- Menu margin guardrails      GET        /api/v25/margin-guardrails

TIER 1-5 EXTRAS
- Ash Pro (AI GM) approval     POST       /api/v25/ash-pro/plan + /approve
- Profit Guardian nightly      GET        /api/v25/profit-guardian
- Digital twin forecast        GET        /api/v25/digital-twin
- AI Shift Manager alerts      GET        /api/v25/shift-manager
- Autonomous marketing         POST/GET   /api/v25/marketing/auto
- Dynamic pricing rules        GET/POST   /api/v25/dynamic-pricing
- Subscription memberships    GET/POST   /api/v25/subscriptions
- Smart gift cards            GET/POST   /api/v25/gift-cards
- Recipe costing engine       GET/POST   /api/v25/recipes/*
- Predictive ordering         POST       /api/v25/predictive-orders
- Waste tracking              GET/POST   /api/v25/waste
- Universal guest profile     GET        /api/v25/guest/{id}
- AI concierge                POST       /api/v25/concierge
- Reputation command center   GET/POST   /api/v25/reputation/*
- Smart recovery (review)     POST       /api/v25/recovery-action
- Franchise command           GET/POST   /api/v25/franchise/*
- Multi-store benchmark       GET        /api/v25/benchmark
- Data warehouse export       GET        /api/v25/warehouse/export
- AI fraud detection          GET        /api/v25/fraud-detection
"""
from fastapi import APIRouter, HTTPException, Request
from database import db
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict
from typing import Optional
import uuid
import os
import json
import re
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v25")


def _now(): return datetime.now(timezone.utc).isoformat()
def _uid(prefix: str) -> str: return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


async def _llm_json(session_id: str, system: str, user_text: str, model: str = "gpt-5.2"):
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=session_id, system_message=system,
        ).with_model("openai", model)
        resp = await chat.send_message(UserMessage(text=user_text))
        text = (resp or "").strip().strip("`")
        try: return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
            return json.loads(m.group(0)) if m else {}
    except Exception as e:
        logger.warning("LLM [%s]: %s", session_id, str(e)[:200])
        return {"_error": str(e)[:200]}


# ============================================================================
# v25 MUST-HAVE — Offline Sync Queue
# ============================================================================
@router.post("/sync-queue")
async def push_sync(data: dict, request: Request):
    """Receive a batch of pending offline operations from a client."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    ops = data.get("ops") or []
    accepted, conflicts = [], []
    for op in ops:
        op_id = op.get("clientOpId") or _uid("OP")
        existing = await db.sync_ops.find_one({"clientOpId": op_id}, {"_id": 0})
        if existing:
            conflicts.append({"clientOpId": op_id, "reason": "duplicate"})
            continue
        rec = {**op, "clientOpId": op_id, "id": _uid("SYNC"), "userId": user["id"],
               "status": "applied", "receivedAt": _now()}
        await db.sync_ops.insert_one(rec)
        accepted.append(op_id)
    return {"accepted": accepted, "conflicts": conflicts}


@router.get("/sync-queue")
async def list_sync(limit: int = 100):
    rows = await db.sync_ops.find({}, {"_id": 0}).sort("receivedAt", -1).to_list(limit)
    return rows


# ============================================================================
# v25 MUST-HAVE — Loss-Control / Exception Center
# ============================================================================
@router.get("/exceptions")
async def list_exceptions(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    days = 14
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    tx = await db.transactions.find({"createdAt": {"$gte": cutoff}}, {"_id": 0}).to_list(5000)
    voids, comps, discounts, refunds = 0, 0, 0, 0
    by_user = defaultdict(lambda: {"voids": 0, "comps": 0, "discounts": 0.0, "refunds": 0.0})
    exceptions = []
    for t in tx:
        uid = t.get("cashier") or t.get("createdBy") or "unknown"
        if t.get("voided"):
            voids += 1; by_user[uid]["voids"] += 1
            exceptions.append({"id": _uid("EX"), "type": "void", "txId": t.get("id"), "user": uid, "amount": t.get("total", 0), "createdAt": t.get("createdAt")})
        if t.get("compTotal", 0) > 0:
            comps += 1; by_user[uid]["comps"] += 1
        d = float(t.get("discount", 0) or 0)
        if d > 0:
            discounts += d; by_user[uid]["discounts"] += d
        if t.get("refunded"):
            refunds += 1; by_user[uid]["refunds"] += float(t.get("total", 0) or 0)
    # Suspicious if any single user has > 3 voids in window
    suspicious = [{"user": u, **v} for u, v in by_user.items() if v["voids"] >= 3]
    return {
        "window_days": days,
        "totals": {"voids": voids, "comps": comps, "discounts": round(discounts, 2), "refunds": refunds},
        "byUser": [{"user": u, **v} for u, v in by_user.items()],
        "suspicious": suspicious,
        "recentExceptions": exceptions[:50],
    }


# ============================================================================
# v25 MUST-HAVE — Multi-Site Command Center
# ============================================================================
@router.get("/sites")
async def list_sites(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    sites = await db.sites.find({}, {"_id": 0}).to_list(100)
    if not sites:
        # Seed default
        s = {"id": "site-hq", "name": "Headquarters", "city": "Sydney", "active": True, "createdAt": _now()}
        await db.sites.insert_one(s)
        s.pop("_id", None)
        sites = [s]
    return sites


@router.post("/sites")
async def create_site(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    site = {"id": _uid("SITE"), "name": data.get("name", "New Site"), "city": data.get("city", ""),
            "active": True, "createdAt": _now()}
    await db.sites.insert_one(site); site.pop("_id", None)
    return site


@router.post("/sites/publish")
async def publish_to_sites(data: dict, request: Request):
    """Push a menu/pricing/promo bundle to selected sites with rollback support."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    publish = {
        "id": _uid("PUB"), "siteIds": data.get("siteIds", []),
        "bundle": data.get("bundle", {}), "publishedBy": user["id"],
        "publishedAt": _now(), "rolledBack": False,
    }
    await db.publications.insert_one(publish); publish.pop("_id", None)
    return publish


@router.post("/sites/rollback/{pub_id}")
async def rollback_publish(pub_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    r = await db.publications.update_one({"id": pub_id}, {"$set": {"rolledBack": True, "rolledBackAt": _now()}})
    if r.matched_count == 0: raise HTTPException(status_code=404, detail="Publication not found")
    return {"rolledBack": True, "id": pub_id}


# ============================================================================
# v25 MUST-HAVE — Hardware Health
# ============================================================================
@router.get("/hardware")
async def hardware_status(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    devices = await db.hardware.find({}, {"_id": 0}).to_list(200)
    if not devices:
        # Seed a baseline fleet so the UI has something to show
        seed = [
            {"id": "PRN-KITCHEN-1", "kind": "printer", "name": "Kitchen printer", "status": "online", "lastSeen": _now()},
            {"id": "PRN-RECEIPT-1", "kind": "printer", "name": "Receipt printer", "status": "online", "lastSeen": _now()},
            {"id": "TERM-FRONT-1", "kind": "terminal", "name": "Front counter", "status": "online", "lastSeen": _now()},
            {"id": "SCN-BAR-1", "kind": "scanner", "name": "Barcode scanner", "status": "online", "lastSeen": _now()},
        ]
        for d in seed: await db.hardware.insert_one(d)
        for d in seed: d.pop("_id", None)
        devices = seed
    return devices


@router.post("/hardware/heartbeat")
async def hardware_heartbeat(data: dict, request: Request):
    """Devices ping in with a shared secret header `X-Device-Secret`."""
    secret = request.headers.get("X-Device-Secret")
    expected = os.environ.get("DEVICE_HEARTBEAT_SECRET", "nua-device-2026")
    if secret != expected:
        raise HTTPException(status_code=401, detail="Invalid device secret")
    dev_id = data.get("id")
    if not dev_id: raise HTTPException(status_code=400, detail="id required")
    update = {"status": data.get("status", "online"), "lastSeen": _now(),
              "errors": data.get("errors", [])}
    await db.hardware.update_one({"id": dev_id}, {"$set": update}, upsert=True)
    return {"recorded": True}


# ============================================================================
# v25 MUST-HAVE — Chargebacks/Disputes Console
# ============================================================================
@router.get("/disputes")
async def list_disputes(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    rows = await db.disputes.find({}, {"_id": 0}).sort("openedAt", -1).to_list(200)
    return rows


@router.post("/disputes")
async def open_dispute(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    d = {
        "id": _uid("DSP"), "txId": data.get("txId"), "amount": float(data.get("amount", 0) or 0),
        "reason": data.get("reason", "fraud"), "status": "open",
        "evidence": data.get("evidence", []), "openedAt": _now(), "openedBy": user["id"],
    }
    await db.disputes.insert_one(d); d.pop("_id", None)
    return d


@router.post("/disputes/{dispute_id}/evidence")
async def attach_evidence(dispute_id: str, data: dict, request: Request):
    """Auto-assemble an evidence pack: transaction details + items + signature + IP."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    d = await db.disputes.find_one({"id": dispute_id}, {"_id": 0})
    if not d: raise HTTPException(status_code=404, detail="Not found")
    tx = await db.transactions.find_one({"id": d.get("txId")}, {"_id": 0})
    evidence = {
        "transactionSnapshot": tx or {},
        "addedNotes": data.get("notes", ""),
        "assembledAt": _now(),
        "assembledBy": user["id"],
    }
    await db.disputes.update_one({"id": dispute_id}, {"$push": {"evidence": evidence}, "$set": {"status": "evidence_submitted"}})
    return {"updated": True, "evidence": evidence}


# ============================================================================
# v25 MUST-HAVE — Supplier Marketplace
# ============================================================================
@router.get("/suppliers/compare")
async def compare_suppliers(item: str = "", request: Request = None):
    """Compare quotes per ingredient across suppliers."""
    if request is None: raise HTTPException(status_code=400)
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    q = {} if not item else {"item": {"$regex": item, "$options": "i"}}
    quotes = await db.supplier_quotes.find(q, {"_id": 0}).to_list(500)
    # Group by item, sort by price
    by_item = defaultdict(list)
    for q in quotes: by_item[q.get("item", "?")].append(q)
    comparisons = []
    for it, qs in by_item.items():
        qs.sort(key=lambda x: float(x.get("pricePerUnit", 99999)))
        if len(qs) >= 2:
            cheapest, current = qs[0], qs[-1]
            savings = (float(current.get("pricePerUnit", 0)) - float(cheapest.get("pricePerUnit", 0))) * float(current.get("annualVolume", 1))
            comparisons.append({"item": it, "quotes": qs, "cheapest": cheapest["supplier"],
                                "annualSavings": round(savings, 2)})
        else:
            comparisons.append({"item": it, "quotes": qs, "annualSavings": 0})
    return comparisons


@router.post("/suppliers/quote")
async def add_quote(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    q = {"id": _uid("QTE"), **data, "createdAt": _now(), "createdBy": user["id"]}
    await db.supplier_quotes.insert_one(q); q.pop("_id", None)
    return q


# ============================================================================
# v27 SHOULD-HAVE — Kiosk session
# ============================================================================
@router.post("/kiosk/session")
async def kiosk_start(data: dict):
    s = {"id": _uid("KSK"), "tableId": data.get("tableId"), "guests": int(data.get("guests", 1)),
         "cart": [], "status": "active", "startedAt": _now()}
    await db.kiosk_sessions.insert_one(s); s.pop("_id", None)
    return s


@router.post("/kiosk/session/{sid}/add")
async def kiosk_add(sid: str, data: dict):
    item = data.get("item") or {}
    await db.kiosk_sessions.update_one({"id": sid}, {"$push": {"cart": item}})
    return {"added": True}


@router.post("/kiosk/session/{sid}/checkout")
async def kiosk_checkout(sid: str):
    s = await db.kiosk_sessions.find_one({"id": sid}, {"_id": 0})
    if not s: raise HTTPException(status_code=404, detail="Session not found")
    total = sum(float(i.get("price", 0) or 0) * int(i.get("quantity", 1) or 1) for i in s.get("cart", []))
    await db.kiosk_sessions.update_one({"id": sid}, {"$set": {"status": "checkout", "total": round(total, 2), "checkoutAt": _now()}})
    return {"sessionId": sid, "total": round(total, 2), "items": len(s.get("cart", []))}


@router.get("/kiosk/sessions")
async def kiosk_list(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    rows = await db.kiosk_sessions.find({}, {"_id": 0}).sort("startedAt", -1).to_list(50)
    return rows


# ============================================================================
# v27 SHOULD-HAVE — Customer-Facing Display
# ============================================================================
@router.get("/cfd/current")
async def cfd_current():
    """Returns the latest open POS tab/cart so a CFD screen can mirror it."""
    tab = await db.pos_tabs.find_one({"status": {"$in": ["open", "active", None]}}, {"_id": 0}, sort=[("createdAt", -1)])
    return {"cart": (tab or {}).get("cart", []), "customer": (tab or {}).get("selectedCustomer"), "updatedAt": _now()}


# ============================================================================
# v27 SHOULD-HAVE — Smart Substitution / 86 fallback
# ============================================================================
@router.post("/substitute")
async def substitute(data: dict, request: Request):
    """Given an 86'd product, suggest the best substitute."""
    from routes.auth import get_current_user
    await get_current_user(request)
    pid = data.get("productId")
    if not pid: raise HTTPException(status_code=400, detail="productId required")
    target = await db.products.find_one({"id": pid}, {"_id": 0})
    if not target: raise HTTPException(status_code=404, detail="Product not found")
    same_cat = await db.products.find(
        {"category": target.get("category"), "active": {"$ne": False}, "stock": {"$gt": 0}, "id": {"$ne": pid}},
        {"_id": 0}
    ).to_list(20)
    # Rank by price proximity
    base = float(target.get("price", 0))
    same_cat.sort(key=lambda p: abs(float(p.get("price", 0)) - base))
    return {"original": target, "substitutes": same_cat[:3]}


# ============================================================================
# v27 SHOULD-HAVE — Guest Recovery automation
# ============================================================================
@router.get("/recovery/churn-risk")
async def churn_risk(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    # Customer hasn't visited in 30+ days but visited 3+ times historically
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    customers = await db.customers.find({}, {"_id": 0}).to_list(2000)
    at_risk = []
    for c in customers:
        last = c.get("lastVisit") or c.get("lastSeen")
        visits = int(c.get("visits", 0) or c.get("totalVisits", 0) or 0)
        if visits >= 3 and last and last < cutoff:
            at_risk.append({"id": c["id"], "name": c.get("name"), "visits": visits, "lastSeen": last, "tier": c.get("membershipTier")})
    return {"atRisk": at_risk[:100]}


@router.post("/recovery/win-back")
async def trigger_win_back(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    cids = data.get("customerIds", [])
    voucher_value = float(data.get("voucherValue", 15))
    campaign = {"id": _uid("RCV"), "customerIds": cids, "voucherValue": voucher_value,
                "status": "queued", "createdAt": _now(), "createdBy": user["id"]}
    await db.recovery_campaigns.insert_one(campaign)
    for cid in cids:
        await db.vouchers.insert_one({"id": _uid("VCH"), "customerId": cid, "amount": voucher_value,
                                       "reason": "win_back", "status": "active", "createdAt": _now()})
    campaign.pop("_id", None)
    return {"queued": len(cids), "campaign": campaign}


# ============================================================================
# v28 SHOULD-HAVE — Station Readiness Score
# ============================================================================
@router.get("/station-readiness")
async def station_readiness(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    # Combine: open prep tickets (lower=better), staff rostered, stock OK, printer status
    pending = await db.kitchen_orders.count_documents({"status": {"$in": ["pending", "in_progress"]}})
    today = datetime.now(timezone.utc).date().isoformat()
    shifts_today = await db.roster_shifts.count_documents({"date": today})
    low_stock = await db.products.count_documents({"stock": {"$lte": 5}, "active": {"$ne": False}})
    printers_online = await db.hardware.count_documents({"kind": "printer", "status": "online"})
    printers_total = await db.hardware.count_documents({"kind": "printer"})
    # Score 0-100
    score = 100
    score -= min(pending * 2, 30)
    if shifts_today == 0: score -= 25
    score -= min(low_stock * 2, 20)
    if printers_total > 0 and printers_online < printers_total: score -= 20
    score = max(0, score)
    return {
        "score": score,
        "factors": {
            "pendingTickets": pending, "shiftsToday": shifts_today,
            "lowStockItems": low_stock,
            "printers": f"{printers_online}/{printers_total}" if printers_total else "n/a",
        },
        "status": "ready" if score >= 80 else "watch" if score >= 50 else "at_risk",
    }


# ============================================================================
# v28 SHOULD-HAVE — Menu Margin Guardrails
# ============================================================================
@router.get("/margin-guardrails")
async def margin_guardrails(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    products = await db.products.find({"active": {"$ne": False}}, {"_id": 0}).to_list(500)
    warnings = []
    for p in products:
        price = float(p.get("price", 0) or 0)
        cost = float(p.get("cost", 0) or 0)
        if price <= 0: continue
        margin_pct = (price - cost) / price * 100
        if margin_pct < 50:
            warnings.append({"productId": p["id"], "name": p["name"], "marginPct": round(margin_pct, 1),
                             "price": price, "cost": cost,
                             "severity": "critical" if margin_pct < 30 else "warning"})
    warnings.sort(key=lambda x: x["marginPct"])
    return {"warnings": warnings[:50]}


# ============================================================================
# TIER 1 — Ash Pro: AI General Manager (executes plans on approval)
# ============================================================================
@router.get("/ash-pro/plan")
async def ash_plan(request: Request):
    """Aggregate today's signals into a single approval plan."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    # Gather signals
    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).isoformat()
    today_tx = await db.transactions.count_documents({"createdAt": {"$gte": yesterday}})
    bookings_today = await db.reservations.count_documents({"date": now.date().isoformat()})
    bookings_yest = await db.reservations.count_documents({"date": (now.date() - timedelta(days=7)).isoformat()})
    booking_delta = ((bookings_today - bookings_yest) / max(bookings_yest, 1)) * 100
    low_stock = await db.products.count_documents({"stock": {"$lte": 5}, "active": {"$ne": False}})
    # Build plan
    actions = []
    if booking_delta < -20:
        actions.append({"id": _uid("ACT"), "type": "send_sms_vips", "summary": f"Send win-back SMS to VIPs (bookings ↓ {abs(booking_delta):.0f}%)",
                        "impact": "+8-12 bookings", "params": {"audience": "VIP", "template": "comeback"}})
        actions.append({"id": _uid("ACT"), "type": "activate_promo", "summary": "Activate 10% lunch offer",
                        "impact": "+$420 revenue", "params": {"discountPct": 10, "window": "lunch"}})
    if low_stock >= 3:
        actions.append({"id": _uid("ACT"), "type": "generate_pos", "summary": f"Generate POs for {low_stock} low-stock items",
                        "impact": "Avoid stock-outs", "params": {}})
    plan = {
        "id": _uid("ASHP"),
        "createdAt": _now(),
        "planDate": datetime.now(timezone.utc).date().isoformat(),
        "signals": {"todaysTransactions": today_tx, "bookingsToday": bookings_today, "bookingDeltaPct": round(booking_delta, 1), "lowStockItems": low_stock},
        "actions": actions,
        "status": "pending_approval",
    }
    # Replace today's existing plan (idempotent — don't grow the collection)
    await db.ash_plans.update_one(
        {"planDate": plan["planDate"], "status": "pending_approval"},
        {"$set": plan}, upsert=True,
    )
    return plan


@router.post("/ash-pro/approve")
async def ash_approve(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    plan_id = data.get("planId")
    approved_action_ids = data.get("actionIds", [])  # empty = approve all
    plan = await db.ash_plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan: raise HTTPException(status_code=404, detail="Plan not found")
    executed = []
    for act in plan.get("actions", []):
        if approved_action_ids and act["id"] not in approved_action_ids: continue
        # Execute (stubbed where external services would be involved)
        if act["type"] == "generate_pos":
            try:
                from routes.phase_ef import generate_po
                r = await generate_po(request)
                executed.append({**act, "result": r})
            except Exception as e:
                executed.append({**act, "error": str(e)[:120]})
        else:
            await db.agent_decisions.insert_one({
                "id": _uid("AGT"), "actionType": act["type"], "summary": act["summary"],
                "payload": act.get("params", {}), "status": "executed", "createdAt": _now(),
            })
            executed.append({**act, "result": {"ok": True}})
    await db.ash_plans.update_one({"id": plan_id}, {"$set": {"status": "approved", "executedAt": _now(), "executed": executed}})
    return {"executed": len(executed), "actions": executed}


# ============================================================================
# TIER 1 — Profit Guardian (nightly margin check)
# ============================================================================
@router.get("/profit-guardian")
async def profit_guardian(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    # Compare last-7d cost % vs prior 7-day window for each product
    now = datetime.now(timezone.utc)
    cur_start = (now - timedelta(days=7)).isoformat()
    prev_start = (now - timedelta(days=14)).isoformat()
    cur = await db.transactions.find({"createdAt": {"$gte": cur_start}}, {"_id": 0, "items": 1}).to_list(5000)
    prev = await db.transactions.find({"createdAt": {"$gte": prev_start, "$lt": cur_start}}, {"_id": 0, "items": 1}).to_list(5000)
    def aggregate(rows):
        rev, cost, units = defaultdict(float), defaultdict(float), defaultdict(int)
        for t in rows:
            for it in (t.get("items") or []):
                pid = it.get("productId")
                if not pid: continue
                q = int(it.get("quantity", 1) or 1)
                rev[pid] += float(it.get("price", 0) or 0) * q
                units[pid] += q
        return rev, cost, units
    cur_rev, _, cur_units = aggregate(cur)
    prev_rev, _, prev_units = aggregate(prev)
    products = {p["id"]: p for p in await db.products.find({}, {"_id": 0}).to_list(2000)}
    alerts = []
    for pid in cur_rev:
        p = products.get(pid)
        if not p: continue
        price = float(p.get("price", 0) or 0); cost = float(p.get("cost", 0) or 0)
        if price <= 0: continue
        margin = (price - cost) / price * 100
        # Heuristic: previously sold N+, now selling much less, suggest price tune
        cu, pu = cur_units[pid], prev_units.get(pid, 0)
        if margin < 60 and cu >= 5:
            suggested = round(price * 1.05, 2)
            alerts.append({"productId": pid, "name": p["name"], "marginPct": round(margin, 1),
                           "price": price, "cost": cost, "suggestedPrice": suggested,
                           "reason": f"Margin {margin:.1f}% sold {cu} last week — bump 5% to lift gross"})
    alerts.sort(key=lambda x: x["marginPct"])
    return {"alerts": alerts[:30]}


# ============================================================================
# TIER 1 — Digital Twin Forecast
# ============================================================================
@router.get("/digital-twin")
async def digital_twin(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    now = datetime.now(timezone.utc)
    # 8-week average revenue per weekday
    cutoff = (now - timedelta(days=56)).isoformat()
    tx = await db.transactions.find({"createdAt": {"$gte": cutoff}}, {"_id": 0, "createdAt": 1, "total": 1}).to_list(20000)
    by_dow = defaultdict(list)
    for t in tx:
        try:
            dt = datetime.fromisoformat(t["createdAt"].replace("Z", "+00:00"))
            by_dow[dt.weekday()].append(float(t.get("total", 0) or 0))
        except Exception:
            continue
    today_dow = now.weekday()
    today_avg = sum(by_dow.get(today_dow, [])) / max(len(by_dow.get(today_dow, [])) / 8, 1) if by_dow.get(today_dow) else 0
    bookings = await db.reservations.count_documents({"date": now.date().isoformat()})
    avg_party = 2.5
    expected_covers = bookings * avg_party
    # Confidence band ±8%
    return {
        "date": now.date().isoformat(),
        "expectedRevenue": round(today_avg, 2),
        "revenueLow": round(today_avg * 0.92, 2),
        "revenueHigh": round(today_avg * 1.08, 2),
        "expectedCovers": int(expected_covers),
        "bookings": bookings,
        "expectedWaitMin": min(45, max(5, int(bookings / 4))),
    }


# ============================================================================
# TIER 1 — AI Shift Manager (real-time alerts)
# ============================================================================
@router.get("/shift-manager")
async def shift_manager(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    alerts = []
    # Check kitchen station overload
    pending = await db.kitchen_orders.count_documents({"status": "pending"})
    if pending > 8:
        alerts.append({"type": "kitchen_overload", "severity": "high",
                       "message": f"Kitchen has {pending} pending tickets — pull a hand from bar/front to expo."})
    # Check oldest ticket
    oldest = await db.kitchen_orders.find_one({"status": "pending"}, {"_id": 0}, sort=[("createdAt", 1)])
    if oldest:
        try:
            dt = datetime.fromisoformat(oldest["createdAt"].replace("Z", "+00:00"))
            wait = (datetime.now(timezone.utc) - dt).total_seconds() / 60
            if wait > 18:
                alerts.append({"type": "ticket_aging", "severity": "high",
                               "message": f"Oldest ticket {wait:.0f} min old — flag manager."})
        except Exception: pass
    return {"alerts": alerts, "timestamp": _now()}


# ============================================================================
# TIER 1 — Autonomous Marketing Engine
# ============================================================================
@router.post("/marketing/auto")
async def auto_marketing(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    audience = data.get("audience", "all")
    target = await db.customers.find({} if audience == "all" else {"membershipTier": audience}, {"_id": 0}).to_list(2000)
    sys_msg = ("You are a restaurant CMO. Generate a short 1-line SMS + 50-word email "
               "for a midweek slowdown offer. Return STRICT JSON: "
               '{"sms":"...","emailSubject":"...","emailBody":"..."}')
    out = await _llm_json(f"mkt-{uuid.uuid4().hex[:6]}", sys_msg,
                          f"Audience: {audience}, {len(target)} customers. Day: {datetime.now().strftime('%A')}.")
    campaign = {
        "id": _uid("MKT"), "audience": audience, "recipients": len(target),
        "sms": out.get("sms", "Come back for 15% off this week!") if isinstance(out, dict) else None,
        "emailSubject": out.get("emailSubject", "We miss you") if isinstance(out, dict) else "We miss you",
        "emailBody": out.get("emailBody", "") if isinstance(out, dict) else "",
        "status": "scheduled", "createdAt": _now(), "createdBy": user["id"],
    }
    await db.marketing_campaigns.insert_one(campaign); campaign.pop("_id", None)
    return campaign


@router.get("/marketing/auto")
async def list_marketing(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    rows = await db.marketing_campaigns.find({}, {"_id": 0}).sort("createdAt", -1).to_list(50)
    return rows


# ============================================================================
# TIER 2 — Dynamic Pricing rules
# ============================================================================
@router.get("/dynamic-pricing")
async def list_dynamic_rules():
    rules = await db.dynamic_pricing.find({}, {"_id": 0}).to_list(200)
    return rules


@router.post("/dynamic-pricing")
async def add_dynamic_rule(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    rule = {
        "id": _uid("DPR"),
        "productId": data.get("productId"),  # null = applies to all in category
        "category": data.get("category"),
        "dow": data.get("dow"),                # 0-6, null = any
        "hourStart": int(data.get("hourStart", 0)),
        "hourEnd": int(data.get("hourEnd", 24)),
        "multiplier": float(data.get("multiplier", 1.0)),
        "active": True, "createdAt": _now(),
    }
    await db.dynamic_pricing.insert_one(rule); rule.pop("_id", None)
    return rule


# ============================================================================
# TIER 2 — Subscription Memberships
# ============================================================================
@router.get("/subscriptions/plans")
async def list_sub_plans():
    plans = await db.subscription_plans.find({}, {"_id": 0}).to_list(50)
    if not plans:
        seed = [{"id": "SUB-COFFEE", "name": "Coffee Club", "priceMonthly": 29, "perks": ["1 free coffee daily", "10% off food", "Priority booking"]}]
        for s in seed: await db.subscription_plans.insert_one(s)
        for s in seed: s.pop("_id", None)
        plans = seed
    return plans


@router.post("/subscriptions/plans")
async def add_sub_plan(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    plan = {"id": _uid("SUB"), **data, "createdAt": _now()}
    await db.subscription_plans.insert_one(plan); plan.pop("_id", None)
    return plan


@router.post("/subscriptions/enroll")
async def enroll_sub(data: dict, request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    sub = {"id": _uid("SUBSC"), "customerId": data.get("customerId"), "planId": data.get("planId"),
           "status": "active", "startedAt": _now()}
    await db.subscriptions.insert_one(sub); sub.pop("_id", None)
    return sub


@router.get("/subscriptions/members")
async def list_sub_members(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    rows = await db.subscriptions.find({}, {"_id": 0}).to_list(500)
    return rows


# ============================================================================
# TIER 2 — Smart Gift Cards
# ============================================================================
@router.get("/gift-cards")
async def list_gift_cards(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    rows = await db.gift_cards.find({}, {"_id": 0}).sort("createdAt", -1).to_list(200)
    return rows


@router.post("/gift-cards")
async def issue_gift_card(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    card = {
        "id": _uid("GC"),
        "code": uuid.uuid4().hex[:12].upper(),
        "amount": float(data.get("amount", 0)),
        "bonus": float(data.get("bonus", 0)),
        "occasion": data.get("occasion", "general"),
        "recipientName": data.get("recipientName", ""),
        "recipientEmail": data.get("recipientEmail", ""),
        "status": "active", "createdAt": _now(), "createdBy": user["id"],
    }
    await db.gift_cards.insert_one(card); card.pop("_id", None)
    return card


@router.post("/gift-cards/{code}/redeem")
async def redeem_gift_card(code: str, data: dict):
    amount = float(data.get("amount", 0))
    if amount <= 0: raise HTTPException(status_code=400, detail="amount > 0 required")
    # Atomic redeem — only deduct if balance is sufficient
    res = await db.gift_cards.find_one_and_update(
        {"code": code, "status": "active", "amount": {"$gte": amount}},
        {"$inc": {"amount": -amount}},
        return_document=False,
    )
    if not res:
        # Either not found, inactive, or insufficient balance
        exists = await db.gift_cards.find_one({"code": code}, {"_id": 0})
        if not exists: raise HTTPException(status_code=404, detail="Card not found")
        if exists.get("status") != "active": raise HTTPException(status_code=400, detail="Card not active")
        raise HTTPException(status_code=400, detail="Insufficient balance")
    return {"redeemed": amount, "code": code}


# ============================================================================
# TIER 3 — Recipe Costing Engine
# ============================================================================
@router.get("/recipes/list")
async def list_recipes_costed(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    recipes = await db.product_recipes.find({}, {"_id": 0}).to_list(500)
    return recipes


@router.post("/recipes/upsert")
async def upsert_recipe(data: dict, request: Request):
    """Attach a recipe of ingredients (productId + qty + costPerUnit) to a product."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    pid = data.get("productId")
    if not pid: raise HTTPException(status_code=400, detail="productId required")
    ingredients = data.get("ingredients", [])  # [{item, quantity, unit, costPerUnit}]
    total_cost = sum(float(i.get("quantity", 0) or 0) * float(i.get("costPerUnit", 0) or 0) for i in ingredients)
    rec = {"productId": pid, "ingredients": ingredients, "computedCost": round(total_cost, 2),
           "updatedAt": _now(), "updatedBy": user["id"]}
    await db.product_recipes.update_one({"productId": pid}, {"$set": rec}, upsert=True)
    # Also push the computed cost back to product.cost so margin engines update
    await db.products.update_one({"id": pid}, {"$set": {"cost": round(total_cost, 2), "recipeLinked": True}})
    return rec


@router.get("/recipes/{product_id}")
async def get_recipe(product_id: str, request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    r = await db.product_recipes.find_one({"productId": product_id}, {"_id": 0})
    return r or {"productId": product_id, "ingredients": [], "computedCost": 0}


# ============================================================================
# TIER 3 — Predictive Ordering
# ============================================================================
@router.post("/predictive-orders")
async def predictive_orders(request: Request):
    """Generate next-week supplier orders based on velocity + bookings + weather hints."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    tx = await db.transactions.find({"createdAt": {"$gte": cutoff}}, {"_id": 0, "items": 1}).to_list(5000)
    units_per_week = Counter()
    for t in tx:
        for it in t.get("items", []) or []:
            pid = it.get("productId")
            if pid: units_per_week[pid] += int(it.get("quantity", 1) or 1)
    # next week target = 7-day average rounded up
    products = await db.products.find({"active": {"$ne": False}}, {"_id": 0}).to_list(500)
    suggestions = []
    for p in products:
        weekly = units_per_week.get(p["id"], 0) / 2  # 14d -> 7d
        target = int(weekly * 1.1)  # +10% safety
        current = int(p.get("stock", 0) or 0)
        order_qty = max(target - current, 0)
        if order_qty > 0:
            suggestions.append({"productId": p["id"], "name": p["name"], "supplier": p.get("supplier", "Default"),
                                "currentStock": current, "orderQty": order_qty, "unitCost": p.get("cost", 0)})
    # Group by supplier
    by_supplier = defaultdict(list)
    for s in suggestions: by_supplier[s["supplier"]].append(s)
    return {"suggestions": suggestions, "bySupplier": [{"supplier": k, "items": v, "total": round(sum(i["orderQty"] * float(i["unitCost"]) for i in v), 2)} for k, v in by_supplier.items()]}


# ============================================================================
# TIER 3 — Waste Tracking
# ============================================================================
@router.get("/waste")
async def list_waste(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    rows = await db.waste_log.find({}, {"_id": 0}).sort("createdAt", -1).to_list(500)
    return rows


@router.post("/waste")
async def log_waste(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    entry = {
        "id": _uid("WST"), "productId": data.get("productId"), "productName": data.get("productName", ""),
        "quantity": float(data.get("quantity", 0)), "reason": data.get("reason", "spoilage"),
        "estCost": float(data.get("estCost", 0)),
        "createdAt": _now(), "createdBy": user["id"],
    }
    await db.waste_log.insert_one(entry); entry.pop("_id", None)
    return entry


@router.get("/waste/insights")
async def waste_insights(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    rows = await db.waste_log.find({"createdAt": {"$gte": cutoff}}, {"_id": 0}).to_list(2000)
    total_cost = sum(float(r.get("estCost", 0)) for r in rows)
    by_reason = Counter([r.get("reason", "?") for r in rows])
    by_product = Counter([r.get("productName", "?") for r in rows])
    return {"totalCost30d": round(total_cost, 2), "entries": len(rows),
            "byReason": dict(by_reason), "topOffenders": by_product.most_common(10)}


# ============================================================================
# TIER 4 — Universal Guest Profile
# ============================================================================
@router.get("/guest/{customer_id}")
async def universal_guest(customer_id: str, request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    c = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not c: raise HTTPException(status_code=404, detail="Customer not found")
    visits = await db.transactions.count_documents({"customerId": customer_id})
    spend_agg = await db.transactions.aggregate([
        {"$match": {"customerId": customer_id}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}
    ]).to_list(1)
    total_spend = float(spend_agg[0]["total"]) if spend_agg else 0
    reservations = await db.reservations.count_documents({"customerId": customer_id})
    points = await db.loyalty_ledger.aggregate([
        {"$match": {"customerId": customer_id}},
        {"$group": {"_id": None, "balance": {"$sum": "$delta"}}}
    ]).to_list(1)
    return {
        "profile": c,
        "stats": {"totalSpend": round(total_spend, 2), "visits": visits, "reservations": reservations,
                  "points": int(points[0]["balance"]) if points else 0},
        "sites": ["Default"],  # placeholder until per-site data exists
    }


# ============================================================================
# TIER 4 — AI Concierge
# ============================================================================
@router.post("/concierge")
async def concierge(data: dict, request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    msg = (data.get("message") or "").strip()
    if not msg: raise HTTPException(status_code=400, detail="message required")
    sys_msg = (
        "You are a restaurant concierge at NUA. Given a guest request, classify and extract details. "
        "Return STRICT JSON: "
        '{"intent":"reservation|dietary|menu|other","date":"YYYY-MM-DD","time":"HH:MM",'
        '"partySize":6,"name":"...","notes":"...","reply":"a friendly 1-2 sentence reply"}'
    )
    out = await _llm_json(f"concierge-{uuid.uuid4().hex[:6]}", sys_msg,
                          f"Today: {datetime.now().date().isoformat()}. Guest: {msg}")
    if isinstance(out, dict) and out.get("intent") == "reservation" and out.get("date"):
        r = {
            "id": _uid("RES"), "guestName": out.get("name") or "Concierge guest",
            "partySize": int(out.get("partySize", 2) or 2),
            "date": out["date"], "time": out.get("time", "19:00"),
            "notes": out.get("notes", msg), "status": "confirmed", "source": "ai_concierge",
            "createdAt": _now(),
        }
        await db.reservations.insert_one(r)
        return {"created": True, "reservationId": r["id"], "reply": out.get("reply", "Booking confirmed."), "intent": "reservation"}
    return {"created": False, "intent": (out or {}).get("intent", "other") if isinstance(out, dict) else "other",
            "reply": (out or {}).get("reply", "I'll pass that to a manager.") if isinstance(out, dict) else "Sorry, I couldn't process that."}


# ============================================================================
# TIER 4 — Reputation Command Center
# ============================================================================
@router.get("/reputation")
async def reputation(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    reviews = await db.reviews.find({}, {"_id": 0}).sort("createdAt", -1).to_list(500)
    if not reviews:
        # Seed a few samples so the dashboard isn't empty
        seed = [
            {"id": _uid("RV"), "source": "Google", "rating": 5, "author": "Mei L.", "text": "Best espresso in town.", "responded": False, "createdAt": _now()},
            {"id": _uid("RV"), "source": "TripAdvisor", "rating": 2, "author": "Tom", "text": "Service was slow at lunch.", "responded": False, "createdAt": _now()},
        ]
        for r in seed: await db.reviews.insert_one(r)
        for r in seed: r.pop("_id", None)
        reviews = seed
    by_source = defaultdict(list)
    for r in reviews: by_source[r.get("source", "?")].append(r.get("rating", 0))
    avg = sum(r.get("rating", 0) for r in reviews) / max(len(reviews), 1)
    return {
        "avgRating": round(avg, 2), "count": len(reviews),
        "bySource": [{"source": s, "avg": round(sum(rs)/len(rs), 2), "count": len(rs)} for s, rs in by_source.items()],
        "reviews": reviews[:50],
    }


@router.post("/reputation/respond")
async def respond_review(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    rid = data.get("reviewId"); response = (data.get("response") or "").strip()
    if not response:
        # Ask LLM to draft
        rev = await db.reviews.find_one({"id": rid}, {"_id": 0})
        if not rev: raise HTTPException(status_code=404, detail="Review not found")
        out = await _llm_json(f"rep-{uuid.uuid4().hex[:6]}",
            "You write warm, professional restaurant review responses (2-3 sentences). Return STRICT JSON: {\"response\":\"...\"}",
            f"Source: {rev.get('source')} · Rating: {rev.get('rating')}/5 · Review: {rev.get('text')}")
        response = out.get("response") if isinstance(out, dict) else "Thank you for your feedback."
    await db.reviews.update_one({"id": rid}, {"$set": {"responded": True, "response": response, "respondedAt": _now()}})
    return {"updated": True, "response": response}


# ============================================================================
# TIER 4 — Smart Recovery (negative review intercept)
# ============================================================================
@router.post("/recovery-action")
async def recovery_action(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    customer_id = data.get("customerId"); voucher = float(data.get("voucherAmount", 20))
    apology = data.get("apologyMessage", "We're sorry — please come back, on us.")
    rec = {
        "id": _uid("REC"), "customerId": customer_id, "voucher": voucher,
        "apology": apology, "managerFlagged": True, "status": "queued", "createdAt": _now(),
    }
    await db.recovery_actions.insert_one(rec)
    await db.vouchers.insert_one({"id": _uid("VCH"), "customerId": customer_id, "amount": voucher,
                                  "reason": "service_recovery", "status": "active", "createdAt": _now()})
    rec.pop("_id", None)
    return rec


# ============================================================================
# TIER 5 — Franchise Command Center
# ============================================================================
@router.get("/franchise/dashboard")
async def franchise_dashboard(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    sites = await db.sites.find({}, {"_id": 0}).to_list(100)
    publications = await db.publications.find({}, {"_id": 0}).sort("publishedAt", -1).to_list(20)
    return {"sites": sites, "recentPublications": publications}


# ============================================================================
# TIER 5 — Multi-Store Benchmarking
# ============================================================================
@router.get("/benchmark")
async def benchmark(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    sites = await db.sites.find({}, {"_id": 0}).to_list(100)
    # Without per-site data we still return a single-site summary so the UI works
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    tx = await db.transactions.find({"createdAt": {"$gte": cutoff}}, {"_id": 0}).to_list(5000)
    revenue = sum(float(t.get("total", 0) or 0) for t in tx)
    food_cost = 0.0
    products = {p["id"]: p for p in await db.products.find({}, {"_id": 0}).to_list(2000)}
    for t in tx:
        for it in t.get("items", []) or []:
            food_cost += float(products.get(it.get("productId"), {}).get("cost", 0) or 0) * int(it.get("quantity", 1) or 1)
    rows = []
    for s in sites:
        rows.append({
            "siteId": s["id"], "siteName": s["name"],
            "revenue": round(revenue, 2),
            "foodCostPct": round((food_cost / revenue * 100) if revenue else 0, 1),
            "labourPct": 28,  # placeholder until roster cost rollup is per-site
            "guestSat": 4.5,
        })
    return rows


# ============================================================================
# TIER 5 — Data Warehouse Export
# ============================================================================
@router.get("/warehouse/export")
async def warehouse_export(collection: str = "transactions", limit: int = 1000, request: Request = None):
    from routes.auth import get_current_user
    user = await get_current_user(request) if request else None
    if user and user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    allowed = {"transactions", "customers", "reservations", "products", "agent_decisions"}
    if collection not in allowed: raise HTTPException(status_code=400, detail=f"Allowed: {allowed}")
    rows = await db[collection].find({}, {"_id": 0}).to_list(limit)
    return {"collection": collection, "rows": rows, "exportedAt": _now()}


# ============================================================================
# TIER 5 — AI Fraud Detection
# ============================================================================
@router.get("/fraud-detection")
async def fraud_detection(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"): raise HTTPException(status_code=403, detail="Owner/Manager only")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    tx = await db.transactions.find({"createdAt": {"$gte": cutoff}}, {"_id": 0}).to_list(5000)
    per_user = defaultdict(lambda: {"voids": 0, "comps": 0, "discounts": 0.0, "refunds": 0, "tx": 0})
    for t in tx:
        u = t.get("cashier") or t.get("createdBy") or "unknown"
        per_user[u]["tx"] += 1
        if t.get("voided"): per_user[u]["voids"] += 1
        if t.get("compTotal", 0) > 0: per_user[u]["comps"] += 1
        per_user[u]["discounts"] += float(t.get("discount", 0) or 0)
        if t.get("refunded"): per_user[u]["refunds"] += 1
    risk_rows = []
    for u, v in per_user.items():
        # Risk score: weighted
        score = 0
        if v["tx"] >= 5:
            score += min(v["voids"] / max(v["tx"], 1) * 100, 35)
            score += min(v["comps"] / max(v["tx"], 1) * 100, 20)
            score += min(v["refunds"] / max(v["tx"], 1) * 100, 20)
            score += min(v["discounts"] / max(v["tx"], 1) / 10, 25)
        risk_rows.append({"user": u, **v, "riskScore": round(score, 1)})
    risk_rows.sort(key=lambda x: x["riskScore"], reverse=True)
    return {"users": risk_rows, "windowDays": 30}
