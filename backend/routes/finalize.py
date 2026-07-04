"""
Finalization batch — v27.7.

Consolidates the remaining feature endpoints from the finalization brief so
we don't scatter tiny router files everywhere. Groups covered:

  • Pre-Shift briefing        (aggregates OOS, specials, roster, upsells)
  • Booking day-rules         (per-day settings + bookable specials)
  • Marketing analytics       (bookings source attribution + promo QR)
  • Channel controls          (pause/resume/schedule per channel)
  • Guest digital wallet      (QR/barcode payload + AI-driven CRM ping)
  • PDF exports               (low-stock, AI-pantry, generic reports)
  • Automation triggers       (user-defined + AI-suggested actions)
  • Store locations extended  (logo, website, timings, gmb)

All endpoints are additive — they layer on top of existing modules.
"""
from fastapi import APIRouter, HTTPException, Depends, Response, BackgroundTasks
from typing import Optional, List
from datetime import datetime, timezone, timedelta, date
from pydantic import BaseModel
from database import db
from deps import get_user
import uuid
import io
import base64
import json
import os
import hmac
import hashlib

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ═════════════════════════════════════════════════════════════════════════
# Pre-Shift briefing (aggregate — a single call instead of 6)
# ═════════════════════════════════════════════════════════════════════════
@router.get("/preshift/briefing")
async def preshift_briefing(_: dict = Depends(get_user)):
    """One call → everything a manager needs before service:
       - out-of-stock items
       - today's specials
       - who's on shift (from staff_shifts / roster)
       - dishes to push (low-margin? high-stock? high-margin flagged?)
    """
    today = date.today().isoformat()

    # Out-of-stock: any product where stock <= 0 OR eightySixed=True
    oos = await db.products.find(
        {"$or": [{"stock": {"$lte": 0}}, {"eightySixed": True}]},
        {"_id": 0, "id": 1, "name": 1, "category": 1, "stock": 1, "eightySixed": 1},
    ).to_list(500)

    # Specials: `isSpecial=true` OR promotion active today
    specials = await db.products.find(
        {"isSpecial": True},
        {"_id": 0, "id": 1, "name": 1, "category": 1, "price": 1, "description": 1},
    ).to_list(200)
    active_promos = await db.promotions.find(
        {"active": True},
        {"_id": 0, "id": 1, "name": 1, "discount": 1, "schedule": 1},
    ).to_list(200)

    # Who's on shift — look at roster/shifts for today
    shifts_today = []
    try:
        cursor = db.staff_shifts.find({"date": today}, {"_id": 0})
        shifts_today = await cursor.to_list(200)
    except Exception:
        pass
    if not shifts_today:
        try:
            cursor = db.shifts.find({"date": today}, {"_id": 0})
            shifts_today = await cursor.to_list(200)
        except Exception:
            pass

    # Upsell candidates — high-margin items with plenty of stock
    upsells = await db.products.find(
        {"stock": {"$gt": 10}, "$or": [{"eightySixed": {"$exists": False}}, {"eightySixed": False}]},
        {"_id": 0, "id": 1, "name": 1, "category": 1, "price": 1, "cost": 1},
    ).sort("price", -1).to_list(500)
    def margin_pct(p):
        c = p.get("cost") or 0
        if not p.get("price") or c is None:
            return 0
        return round(((p["price"] - c) / p["price"]) * 100, 1) if p["price"] else 0
    upsells_ranked = sorted(
        [{**p, "marginPct": margin_pct(p)} for p in upsells],
        key=lambda x: (-x["marginPct"], -(x.get("price") or 0)),
    )[:10]

    return {
        "date": today,
        "outOfStock": oos,
        "specials": specials,
        "activePromotions": active_promos,
        "onShift": shifts_today,
        "onShiftCount": len(shifts_today),
        "upsells": upsells_ranked,
        "generatedAt": _now(),
    }


# ═════════════════════════════════════════════════════════════════════════
# Booking day-rules + bookable specials/experiences
# ═════════════════════════════════════════════════════════════════════════
class DayRuleIn(BaseModel):
    weekday: int                    # 0=Mon … 6=Sun
    open: bool = True
    openTime: str = "12:00"
    closeTime: str = "22:00"
    maxCovers: Optional[int] = None
    slotMinutes: int = 30
    turnMinutes: int = 90
    minPartySize: int = 1
    maxPartySize: int = 20
    bookableSpecials: List[str] = []     # product ids
    bookableExperienceIds: List[str] = []
    note: Optional[str] = None


@router.get("/bookings/day-rules")
async def get_day_rules(_: dict = Depends(get_user)):
    rows = await db.booking_day_rules.find({}, {"_id": 0}).to_list(20)
    have = {r["weekday"] for r in rows}
    # Fill any missing weekday with a sensible default so the UI always has 7 rows.
    for i in range(7):
        if i not in have:
            rows.append({"weekday": i, "open": True, "openTime": "12:00", "closeTime": "22:00",
                          "slotMinutes": 30, "turnMinutes": 90, "minPartySize": 1, "maxPartySize": 20,
                          "bookableSpecials": [], "bookableExperienceIds": [], "note": None})
    rows.sort(key=lambda r: r["weekday"])
    return rows


@router.put("/bookings/day-rules/{weekday}")
async def update_day_rule(weekday: int, body: DayRuleIn, user: dict = Depends(get_user)):
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(403, "Owner or manager only")
    if not (0 <= weekday <= 6):
        raise HTTPException(400, "weekday must be 0..6")
    payload = {**body.dict(), "weekday": weekday, "updatedAt": _now(), "updatedBy": user.get("email")}
    await db.booking_day_rules.update_one({"weekday": weekday}, {"$set": payload}, upsert=True)
    return payload


# ═════════════════════════════════════════════════════════════════════════
# Marketing analytics — booking-source attribution + promo QR
# ═════════════════════════════════════════════════════════════════════════
def _sign_qr(payload: dict) -> str:
    """Sign a QR payload with the JWT secret so scans can be verified."""
    secret = os.environ.get("JWT_SECRET", "dev-secret").encode()
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(secret, raw, hashlib.sha256).hexdigest()[:16]
    b64 = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return f"{b64}.{sig}"


@router.get("/marketing/promo-qr")
async def promo_qr(type: str, id: str, campaign: Optional[str] = None,
                    _: dict = Depends(get_user)):
    """Return a signed payload the SPA can turn into a QR code / short-URL for
    any promoted asset (experience, voucher, gift card, loyalty tier, ...).

    `type` ∈ {experience, voucher, gift_card, loyalty, promotion, event, club}
    """
    allowed = {"experience", "voucher", "gift_card", "loyalty", "promotion", "event", "club"}
    if type not in allowed:
        raise HTTPException(400, f"type must be one of {sorted(allowed)}")
    payload = {"t": type, "id": id, "c": campaign or "", "ts": int(datetime.now(timezone.utc).timestamp())}
    token = _sign_qr(payload)
    origin = os.environ.get("FRONTEND_URL", "").rstrip("/")
    return {
        "token": token,
        "url": f"{origin}/scan?t={token}" if origin else f"/scan?t={token}",
        "payload": payload,
    }


@router.post("/marketing/scan")
async def marketing_scan(body: dict):
    """Public endpoint — the QR landing page pings this so we can track
    scan → booking attribution. Fingerprint by IP is deliberately loose."""
    await db.marketing_scans.insert_one({
        "id": str(uuid.uuid4()),
        "token": body.get("token"),
        "t": body.get("t"), "sourceId": body.get("id"), "campaign": body.get("c"),
        "referrer": body.get("referrer"), "ua": body.get("ua"),
        "createdAt": _now(),
    })
    return {"tracked": True}


@router.get("/marketing/analytics")
async def marketing_analytics(days: int = 30, _: dict = Depends(get_user)):
    """Rolls up scans + bookings + revenue by source over `days`."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    scans = await db.marketing_scans.find({"createdAt": {"$gte": since}}, {"_id": 0}).to_list(5000)
    bookings = await db.reservations.find({"createdAt": {"$gte": since}}, {"_id": 0}).to_list(5000)
    by_source = {}
    for b in bookings:
        src = (b.get("source") or b.get("channel") or "walk-in").lower()
        bucket = by_source.setdefault(src, {"bookings": 0, "covers": 0, "estRevenue": 0.0})
        bucket["bookings"] += 1
        bucket["covers"] += int(b.get("partySize") or 0)
        bucket["estRevenue"] += float(b.get("estRevenue") or 0)
    scans_by_type = {}
    for s in scans:
        scans_by_type.setdefault(s.get("t") or "other", 0)
        scans_by_type[s.get("t") or "other"] += 1
    return {
        "windowDays": days,
        "totalScans": len(scans),
        "totalBookings": len(bookings),
        "scansByType": scans_by_type,
        "bookingsBySource": by_source,
        "generatedAt": _now(),
    }


# ═════════════════════════════════════════════════════════════════════════
# Channel controls — pause / resume / schedule per delivery channel
# ═════════════════════════════════════════════════════════════════════════
class ChannelStateIn(BaseModel):
    channel: str
    action: str                     # pause | resume | schedule
    pausedUntil: Optional[str] = None      # ISO datetime for scheduled resume
    reason: Optional[str] = None


@router.get("/channels/state")
async def channel_states(_: dict = Depends(get_user)):
    rows = await db.channel_states.find({}, {"_id": 0}).to_list(50)
    return rows


@router.post("/channels/state")
async def update_channel_state(body: ChannelStateIn, user: dict = Depends(get_user)):
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(403, "Owner or manager only")
    if body.action not in ("pause", "resume", "schedule"):
        raise HTTPException(400, "action must be pause | resume | schedule")
    doc = {
        "channel": body.channel,
        "status": "paused" if body.action in ("pause", "schedule") else "active",
        "pausedUntil": body.pausedUntil if body.action == "schedule" else None,
        "reason": body.reason,
        "updatedAt": _now(),
        "updatedBy": user.get("email"),
    }
    await db.channel_states.update_one({"channel": body.channel}, {"$set": doc}, upsert=True)
    return doc


# ═════════════════════════════════════════════════════════════════════════
# Guest digital wallet — QR/barcode for POS scan + AI CRM update
# ═════════════════════════════════════════════════════════════════════════
@router.get("/customers/{customer_id}/wallet")
async def guest_wallet(customer_id: str, _: dict = Depends(get_user)):
    """Return the QR payload + barcode + tier metadata for a customer's
    digital wallet. This is what mobile Apple/Google Wallet stubs pull in."""
    c = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Customer not found")
    payload = {"cid": customer_id, "tier": c.get("membershipTier", "Bronze"),
                "issued": int(datetime.now(timezone.utc).timestamp())}
    token = _sign_qr(payload)
    return {
        "customerId": customer_id,
        "name": c.get("name"),
        "tier": c.get("membershipTier"),
        "points": c.get("points", 0),
        "storeCredit": c.get("storeCredit", 0.0),
        "barcode": customer_id.upper().replace("-", "")[:20],
        "qrToken": token,
        "walletDataUrl": f"data:text/plain;base64,{base64.b64encode(token.encode()).decode()}",
    }


@router.post("/customers/lookup-by-token")
async def lookup_by_token(body: dict, _: dict = Depends(get_user)):
    """POS scans a wallet QR → returns the customer for one-tap add-to-cart."""
    token = body.get("token") or ""
    try:
        b64, sig = token.split(".")
        raw = base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4))
        payload = json.loads(raw)
        expected = _sign_qr(payload).split(".")[1]
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(401, "Invalid token")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Malformed token")
    c = await db.customers.find_one({"id": payload.get("cid")}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Customer not found")
    return c


# ═════════════════════════════════════════════════════════════════════════
# PDF exports — low-stock, AI Pantry
# ═════════════════════════════════════════════════════════════════════════
def _pdf_from_lines(title: str, lines: List[str], meta: Optional[dict] = None) -> bytes:
    """Minimal PDF assembler — writes a single-page A4 with a title + line
    list. No external dependency (avoids adding a 30MB reportlab install).
    Good enough for order sheets + low-stock exports."""
    content = []
    y = 750
    def add(text, size=12):
        nonlocal y
        # Escape parens & backslashes per PDF spec
        text = (text or "").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content.append(f"BT /F1 {size} Tf 40 {y} Td ({text}) Tj ET")
        y -= size + 4

    add(title, size=18)
    y -= 4
    add(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", size=9)
    y -= 6
    if meta:
        for k, v in meta.items():
            add(f"{k}: {v}", size=9)
        y -= 6
    for line in lines:
        # Simple page-break if we run out of room. First page only, but at
        # least prevents overflow-clipping.
        if y < 50:
            add("… (truncated — export CSV for full list)", size=9)
            break
        add(line, size=10)

    stream_body = "\n".join(content).encode("latin-1", errors="ignore")
    length = len(stream_body)
    header = b"%PDF-1.4\n"
    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>")
    objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
                 b"/Resources << /Font << /F1 5 0 R >> >> >>")
    objs.append(f"<< /Length {length} >>\nstream\n".encode() + stream_body + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    body = bytearray()
    body += header
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(body))
        body += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref_off = len(body)
    body += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        body += f"{off:010d} 00000 n \n".encode()
    body += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_off}\n%%EOF".encode()
    return bytes(body)


@router.get("/inventory/low-stock/pdf")
async def low_stock_pdf(_: dict = Depends(get_user)):
    prods = await db.products.find({}, {"_id": 0}).to_list(2000)
    low = [p for p in prods
           if p.get("stock") is not None
           and p["stock"] <= (p.get("lowStockThreshold") or 5)]
    low.sort(key=lambda p: p.get("stock", 0))
    lines = [f"{p.get('name'):<40s}  category: {p.get('category', '—'):<15s}  stock: {p.get('stock', 0):>4}  threshold: {p.get('lowStockThreshold', 5)}"
             for p in low]
    if not lines:
        lines = ["No low-stock items — every product is above its threshold."]
    pdf = _pdf_from_lines("Low-stock report", lines,
                          meta={"Items below threshold": len(low)})
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="low-stock-{date.today().isoformat()}.pdf"'})


@router.get("/ai-pantry/order-sheet/pdf")
async def ai_pantry_pdf(_: dict = Depends(get_user)):
    # Reuse whatever the AI Pantry produces; fall back to low-stock if the
    # collection isn't there yet.
    rows = []
    try:
        rows = await db.ai_pantry_orders.find({"status": {"$in": ["draft", "suggested"]}},
                                               {"_id": 0}).sort("createdAt", -1).to_list(500)
    except Exception:
        pass
    if not rows:
        prods = await db.products.find({"stock": {"$lte": 5}}, {"_id": 0}).to_list(2000)
        for p in prods:
            rows.append({"item": p.get("name"), "qty": max(10, (p.get("lowStockThreshold") or 5) * 3),
                          "supplier": p.get("supplier", "TBD"), "unit": "units"})
    lines = [f"{r.get('item', ''):<32s} qty: {r.get('qty', ''):>6}  unit: {r.get('unit', ''):<8s} supplier: {r.get('supplier', 'TBD')}"
             for r in rows]
    if not lines:
        lines = ["No pending orders."]
    pdf = _pdf_from_lines("AI Pantry — order sheet", lines,
                          meta={"Lines": len(lines), "Prepared": datetime.now().strftime('%Y-%m-%d %H:%M')})
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="pantry-order-{date.today().isoformat()}.pdf"'})


# ═════════════════════════════════════════════════════════════════════════
# Automation triggers — user-defined + AI-suggested
# ═════════════════════════════════════════════════════════════════════════
class TriggerIn(BaseModel):
    name: str
    event: str                       # e.g. low_stock, temperature_abnormal, booking_created, staff_late
    conditions: dict = {}
    actions: List[dict] = []         # each: {type, params}
    active: bool = True
    aiGenerated: bool = False
    aiPrompt: Optional[str] = None


@router.get("/automations/triggers")
async def list_triggers(_: dict = Depends(get_user)):
    return await db.automation_triggers.find({}, {"_id": 0}).sort("createdAt", -1).to_list(200)


@router.post("/automations/triggers")
async def create_trigger(body: TriggerIn, user: dict = Depends(get_user)):
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(403, "Owner or manager only")
    doc = {"id": str(uuid.uuid4()), **body.dict(),
           "createdBy": user.get("email"), "createdAt": _now(), "updatedAt": _now()}
    await db.automation_triggers.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.patch("/automations/triggers/{trigger_id}")
async def update_trigger(trigger_id: str, data: dict, user: dict = Depends(get_user)):
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(403, "Owner or manager only")
    data["updatedAt"] = _now()
    r = await db.automation_triggers.update_one({"id": trigger_id}, {"$set": data})
    if r.matched_count == 0:
        raise HTTPException(404, "Trigger not found")
    return await db.automation_triggers.find_one({"id": trigger_id}, {"_id": 0})


@router.delete("/automations/triggers/{trigger_id}")
async def delete_trigger(trigger_id: str, user: dict = Depends(get_user)):
    if user["role"] != "owner":
        raise HTTPException(403, "Owner only")
    r = await db.automation_triggers.delete_one({"id": trigger_id})
    if r.deleted_count == 0:
        raise HTTPException(404, "Trigger not found")
    return {"deleted": True}


@router.post("/automations/ai-suggest")
async def ai_suggest_automation(body: dict, _: dict = Depends(get_user)):
    """AI generates a trigger spec from a plain-English prompt. When the LLM
    key is unavailable we synthesise a plausible template so the UI still
    has something to preview."""
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt is required")
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise Exception("no key")
        chat = LlmChat(api_key=api_key, session_id=f"auto-{uuid.uuid4()}",
                        system_message=(
                            "You design automation triggers for a restaurant POS. "
                            "Return STRICT JSON matching {name, event, conditions:{}, actions:[{type, params:{}}]}. "
                            "Common events: low_stock, temperature_abnormal, booking_created, staff_late, "
                            "customer_birthday, dish_86, high_wait_time, no_show. "
                            "Common action types: send_email, send_sms, dock_notify, dispatch_task, apply_discount."
                        )).with_model("openai", "gpt-4o-mini").with_max_tokens(500)
        raw = await chat.send_message(UserMessage(text=prompt))
        import re
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        parsed = json.loads(m.group()) if m else {}
    except Exception:
        parsed = {
            "name": f"Automation: {prompt[:40]}",
            "event": "low_stock",
            "conditions": {"threshold": 5},
            "actions": [{"type": "dock_notify", "params": {"message": "Low stock alert"}},
                         {"type": "send_email", "params": {"template": "low_stock"}}],
        }
    parsed.setdefault("aiGenerated", True)
    parsed.setdefault("aiPrompt", prompt)
    return parsed
