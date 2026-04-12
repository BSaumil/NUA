from fastapi import APIRouter, HTTPException
from typing import Optional
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
    floor_plans = await db.floor_plans.find({}, {"_id": 0}).to_list(10)
    all_tables = []
    for fp in floor_plans:
        all_tables.extend(fp.get("tables", []))
    suitable_tables = [t for t in all_tables if t.get("maxCovers", 2) >= party_size and t.get("isActive", True)]
    if not suitable_tables:
        suitable_tables = [{"id": "virtual", "maxCovers": 20}]
    reservations = await db.reservations.find({"date": date}, {"_id": 0}).to_list(500)
    slots = []
    for hour in range(11, 22):
        for minute in [0, 30]:
            time_str = f"{hour:02d}:{minute:02d}"
            occupied = len([r for r in reservations if r.get("time") == time_str and r.get("status") in ("confirmed", "seated")])
            available = len(suitable_tables) - occupied
            if available > 0:
                slots.append({"time": time_str, "available": available})
    return {"date": date, "partySize": party_size, "slots": slots}

@router.post("/public/book")
async def public_book_reservation(data: dict):
    from models.reservation import Reservation
    res_obj = Reservation(
        guestName=data.get("guestName", "Guest"),
        guestPhone=data.get("guestPhone", ""),
        guestEmail=data.get("guestEmail", ""),
        partySize=data.get("partySize", 2),
        date=data.get("date", ""),
        time=data.get("time", ""),
        duration=data.get("duration", 90),
        specialRequests=data.get("specialRequests", ""),
        source="online",
    )
    await db.reservations.insert_one(res_obj.dict())
    return {"reservationId": res_obj.id, "status": "confirmed", "message": "Reservation booked successfully!"}

@router.post("/public/join-waitlist")
async def public_join_waitlist(data: dict):
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
    return {"position": next_pos, "estimatedWait": next_pos * random.randint(8, 15)}

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
    merchant_upi = data.get("merchantUpi", "nuva@upi")
    merchant_name = data.get("merchantName", "NUVA Restaurant")
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
