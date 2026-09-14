from fastapi import APIRouter, HTTPException
from datetime import datetime
from database import db
import uuid
import random

router = APIRouter()

# ============ PUBLIC BOOKING PORTAL API ============
@router.get("/public/menu")
async def get_public_menu():
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    categories = {}
    for p in products:
        cat = p.get("category", "Other")
        if cat not in categories:
            categories[cat] = {"name": cat, "items": []}
        categories[cat]["items"].append({
            "name": p["name"], "price": p.get("price", 0),
            "description": p.get("description", ""),
        })
    return {"categories": list(categories.values())}

@router.get("/public/available-slots")
async def get_available_slots(date: str, party_size: int = 2):
    from datetime import date as date_cls
    from services.booking_rules_engine import get_rules, capacity_for_slot, in_time_range

    rules = await get_rules()

    # A whole-day block (blackout or a blocked weekday) means no slot is
    # offered at all — matches what POST /public/book would reject anyway,
    # so the guest sees why up front instead of picking a time and then
    # hitting a 409.
    blackout = await db.booking_blackouts.find_one({"date": date}, {"_id": 0})
    if blackout:
        return {"date": date, "partySize": party_size, "slots": [], "closed": blackout.get("reason") or "closed"}
    try:
        weekday_name = date_cls.fromisoformat(date).strftime("%A")
    except Exception:
        weekday_name = None
    if weekday_name and weekday_name in (rules.get("blockedWeekdays") or []):
        return {"date": date, "partySize": party_size, "slots": [], "closed": f"Closed on {weekday_name}s"}

    floor_plans = await db.floor_plans.find({}, {"_id": 0}).to_list(10)
    all_tables = []
    for fp in floor_plans:
        all_tables.extend(fp.get("tables", []))
    suitable_tables = [t for t in all_tables if t.get("maxCovers", 2) >= party_size and t.get("isActive", True)]
    if not suitable_tables:
        suitable_tables = [{"id": "virtual", "maxCovers": 20}]
    reservations = await db.reservations.find({"date": date}, {"_id": 0}).to_list(500)
    open_t = rules.get("bookingOpenTime") or "00:00"
    close_t = rules.get("bookingCloseTime") or "23:59"
    # If `date` is today, don't offer a time that's already passed — POST
    # /public/book would reject it anyway (see booking_rules_engine's
    # "already passed" check, which uses this same naive datetime.now()
    # convention), so showing it as pickable just sets the guest up for a
    # confirm-time 409 instead of a clean slot list.
    now = datetime.now()
    is_today = date == now.strftime("%Y-%m-%d")
    now_hhmm = now.strftime("%H:%M")
    slots = []
    for hour in range(11, 22):
        for minute in [0, 30]:
            time_str = f"{hour:02d}:{minute:02d}"
            if is_today and time_str <= now_hhmm:
                continue
            if not in_time_range(time_str, open_t, close_t):
                continue
            occupied = len([r for r in reservations if r.get("time") == time_str and r.get("status") in ("confirmed", "seated")])
            available = len(suitable_tables) - occupied
            if available <= 0:
                continue
            if rules.get("enforceCapacity"):
                cap_info = await capacity_for_slot(date, time_str, rules)
                if cap_info["available"] < party_size:
                    continue
            slots.append({"time": time_str, "available": available})
    return {"date": date, "partySize": party_size, "slots": slots}

@router.post("/public/book")
async def public_book_reservation(data: dict):
    """Customer self-service booking — must run through the exact same
    booking_rules_engine as staff's POST /reservations. Previously this path
    had NO rule enforcement at all (not even the blackout-date check the
    staff path already had), so a guest could book straight through a
    closed date or a large-party set-menu requirement just by using the
    public form instead of calling the restaurant."""
    from models.reservation import Reservation
    from services.booking_rules_engine import validate_and_enrich_booking, BookingRuleViolation

    party_size = int(data.get("partySize") or 2)
    date = data.get("date", "")
    time = data.get("time", "")
    experience_id = data.get("experienceId")

    try:
        enrichment = await validate_and_enrich_booking(
            date=date, time=time, party_size=party_size, source="online",
            experience_id=experience_id,
        )
    except BookingRuleViolation as e:
        raise HTTPException(status_code=409, detail=str(e))

    res_obj = Reservation(
        guestName=data.get("guestName", "Guest"),
        guestPhone=data.get("guestPhone", ""),
        guestEmail=data.get("guestEmail", ""),
        partySize=party_size,
        date=date,
        time=time,
        duration=data.get("duration", 90),
        specialRequests=data.get("specialRequests", ""),
        source="online",
        **enrichment,
    )
    await db.reservations.insert_one(res_obj.dict())
    if res_obj.isLargeBooking:
        from services import audit_service
        await audit_service.log_event(
            entity_type="reservation", entity_id=res_obj.id, action="created",
            after=res_obj.dict(), memo=f"Large booking ({res_obj.partySize} guests) via online booking — "
                                        f"tier: {res_obj.bookingTierLabel}",
            severity="notice", tags=["large_booking"],
        )
    message = "Reservation booked successfully!"
    if res_obj.isLargeBooking:
        message = f"Booked with {res_obj.experienceName or res_obj.bookingTierLabel}. " + message
    return {
        "reservationId": res_obj.id, "status": "confirmed", "message": message,
        "isLargeBooking": res_obj.isLargeBooking, "bookingTierLabel": res_obj.bookingTierLabel,
        "experienceName": res_obj.experienceName, "depositRequired": res_obj.depositRequired,
        "preOrderRequired": res_obj.preOrderRequired, "approvalRequired": res_obj.approvalRequired,
    }

@router.post("/public/join-waitlist")
async def public_join_waitlist(data: dict):
    # Deliberately unscoped, same category as table_ordering.py's public
    # endpoints: this form carries no business/table signal at all (no
    # slug, no header, nothing in `data`) to resolve a businessId from, so
    # the created entry is untagged — it still surfaces correctly to every
    # business's staff waitlist view via tenant_scope_filter's safe
    # default (untagged docs always match), it just isn't excluded from
    # any OTHER business's view either. Not attempted here; would need a
    # venue-identifying param threaded through from the caller first.
    from models.waitlist import WaitlistEntry
    last = await db.waitlist.find({"status": "waiting"}).sort("position", -1).to_list(1)
    next_pos = (last[0]["position"] + 1) if last else 1
    entry = WaitlistEntry(
        guestName=data.get("guestName", "Guest"),
        guestPhone=data.get("guestPhone", ""),
        partySize=data.get("partySize", 2),
        preferences=data.get("preferences", ""),
        position=next_pos,
    )
    await db.waitlist.insert_one(entry.dict())
    # id is the guest's tracking code for GET /waitlist/track/{id} — without
    # it there was no way to hand the guest anything to check their status
    # with later, only the one-time position/estimate from this response.
    return {"id": entry.id, "position": next_pos, "estimatedWait": next_pos * random.randint(8, 15)}

@router.get("/public/events")
async def get_public_events():
    events = await db.events.find({"isActive": True}, {"_id": 0}).to_list(50)
    return events

# ============ QR PAYMENT API ============
@router.post("/payments/generate-qr")
async def generate_payment_qr(data: dict):
    amount = data.get("amount", 0)
    transaction_id = data.get("transactionId", f"TXN-{str(uuid.uuid4())[:8].upper()}")
    method = data.get("method", "upi")
    merchant_upi = data.get("merchantUpi", "nua@upi")
    merchant_name = data.get("merchantName", "NUA Restaurant")
    note = data.get("note", f"Payment for order {transaction_id}")
    upi_string = f"upi://pay?pa={merchant_upi}&pn={merchant_name}&am={amount:.2f}&tn={note}&tr={transaction_id}"
    payment_record = {
        "id": f"PAY-{str(uuid.uuid4())[:8].upper()}", "transactionId": transaction_id,
        "amount": amount, "method": method, "status": "pending",
        "upiString": upi_string, "merchantUpi": merchant_upi,
        "createdAt": datetime.utcnow().isoformat(),
    }
    await db.payments.insert_one(payment_record)
    payment_record.pop("_id", None)
    return {
        "paymentId": payment_record["id"], "upiString": upi_string,
        "amount": amount, "transactionId": transaction_id,
        "qrData": upi_string, "status": "pending", "merchantUpi": merchant_upi,
    }

@router.post("/payments/split")
async def create_split_payment(data: dict):
    total = data.get("totalAmount", 0)
    splits = data.get("splits", [])
    transaction_id = data.get("transactionId", f"TXN-{str(uuid.uuid4())[:8].upper()}")
    split_records = []
    for i, split in enumerate(splits):
        record = {
            "id": f"SPLIT-{str(uuid.uuid4())[:8].upper()}", "transactionId": transaction_id,
            "splitIndex": i + 1, "amount": split.get("amount", 0),
            "method": split.get("method", "card"),
            "payerName": split.get("payerName", f"Guest {i + 1}"),
            "status": "pending", "createdAt": datetime.utcnow().isoformat(),
        }
        split_records.append(record)
    if split_records:
        await db.split_payments.insert_many(split_records)
        for r in split_records:
            r.pop("_id", None)
    return {"transactionId": transaction_id, "totalAmount": total, "splits": split_records, "splitCount": len(split_records)}

@router.post("/payments/{payment_id}/confirm")
async def confirm_payment(payment_id: str):
    result = await db.payments.find_one_and_update(
        {"id": payment_id},
        {"$set": {"status": "confirmed", "confirmedAt": datetime.utcnow().isoformat()}},
        return_document=True
    )
    if not result:
        result = await db.split_payments.find_one_and_update(
            {"id": payment_id},
            {"$set": {"status": "confirmed", "confirmedAt": datetime.utcnow().isoformat()}},
            return_document=True
        )
    if not result:
        raise HTTPException(status_code=404, detail="Payment not found")
    result.pop("_id", None)
    return result
