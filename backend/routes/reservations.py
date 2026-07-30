from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
from database import db
from models.reservation import Reservation, ReservationCreate, ReservationUpdate
from models.floor_plan import FloorPlan, FloorPlanCreate, FloorPlanUpdate
from models.waitlist import WaitlistEntry, WaitlistEntryCreate, WaitlistEntryUpdate

router = APIRouter()

# ============ RESERVATIONS API ============
@router.get("/reservations", response_model=List[Reservation])
async def get_reservations(date: Optional[str] = None, status: Optional[str] = None, section: Optional[str] = None):
    query = {}
    if date:
        query["date"] = date
    if status:
        query["status"] = status
    if section:
        query["section"] = section
    reservations = await db.reservations.find(query, {"_id": 0}).sort("time", 1).to_list(1000)
    return [Reservation(**r) for r in reservations]


# NOTE: these two GET routes MUST come before /reservations/{reservation_id}
# — otherwise FastAPI treats "day-counts" / "blackouts" as a reservation id.
@router.get("/reservations/day-counts")
async def day_counts(fromDate: str, toDate: str):
    """Return {date: count} for the calendar dots + blackout state per date.
    Range is inclusive; capped at ~120 days to keep the response small."""
    from datetime import date as _date
    d0 = _date.fromisoformat(fromDate); d1 = _date.fromisoformat(toDate)
    if (d1 - d0).days > 120:
        raise HTTPException(status_code=400, detail="Range too wide (max 120 days)")
    reservations = await db.reservations.find(
        {"date": {"$gte": fromDate, "$lte": toDate}},
        {"_id": 0, "date": 1, "status": 1, "partySize": 1},
    ).to_list(5000)
    counts: dict = {}
    covers: dict = {}
    for r in reservations:
        d = r.get("date")
        if not d: continue
        counts[d] = counts.get(d, 0) + 1
        covers[d] = covers.get(d, 0) + int(r.get("partySize") or 0)
    blackouts = await db.booking_blackouts.find(
        {"date": {"$gte": fromDate, "$lte": toDate}},
        {"_id": 0},
    ).to_list(500)
    black_map = {b["date"]: {"reason": b.get("reason"), "blockUntil": b.get("blockUntil")} for b in blackouts}
    return {"counts": counts, "covers": covers, "blackouts": black_map}


@router.get("/reservations/blackouts")
async def list_blackouts(fromDate: Optional[str] = None, toDate: Optional[str] = None):
    q: dict = {}
    if fromDate or toDate:
        q["date"] = {}
        if fromDate: q["date"]["$gte"] = fromDate
        if toDate:   q["date"]["$lte"] = toDate
    docs = await db.booking_blackouts.find(q, {"_id": 0}).sort("date", 1).to_list(1000)
    return docs


@router.get("/reservations/{reservation_id}", response_model=Reservation)
async def get_reservation(reservation_id: str):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return Reservation(**res)

@router.post("/reservations", response_model=Reservation)
async def create_reservation(reservation: ReservationCreate):
    # Refuse if the target date is under an active blackout (unless the
    # blackout has an expiry that has already passed).
    if reservation.date:
        b = await db.booking_blackouts.find_one({"date": reservation.date}, {"_id": 0})
        if b:
            block_until = b.get("blockUntil")
            expired = False
            if block_until:
                try:
                    exp = datetime.fromisoformat(block_until.replace("Z", "+00:00"))
                    from datetime import timezone as _tz
                    if datetime.now(_tz.utc) > exp: expired = True
                except Exception:
                    pass
            if not expired:
                raise HTTPException(
                    status_code=409,
                    detail=f"Bookings paused for {reservation.date}: {b.get('reason') or 'closed'}",
                )
    res_obj = Reservation(**reservation.dict())
    doc = res_obj.dict()
    await db.reservations.insert_one(doc)
    if reservation.tableId:
        await db.floor_tables.update_one(
            {"id": reservation.tableId},
            {"$set": {"status": "reserved", "currentReservationId": res_obj.id}}
        )
    if reservation.customerId:
        await db.customers.update_one(
            {"id": reservation.customerId},
            {"$inc": {"visits": 0}, "$push": {"reservationIds": res_obj.id}}
        )
    # Rules engine emit
    try:
        from services.rules_engine import safe_emit
        rd = res_obj.dict()
        safe_emit("booking.created", {
            "id": rd.get("id"), "partySize": rd.get("partySize"),
            "time": (rd.get("dateTime") or rd.get("time") or ""),
            "customerId": rd.get("customerId"),
        })
    except Exception:
        pass
    # Mirror to the standalone Bookings platform (nua-native partner) — no-op
    # unless the integration env vars are configured.
    try:
        from services.bookings_partner_client import mirror_reservation_created
        mirror_reservation_created(res_obj.dict())
    except Exception:
        pass
    # Free base identity layer: recognize this guest across modules.
    try:
        from services.customer_identity import record_touchpoint
        await record_touchpoint(
            phone=reservation.guestPhone, email=reservation.guestEmail,
            name=reservation.guestName, source="booking",
        )
    except Exception:
        pass
    return res_obj

@router.put("/reservations/{reservation_id}", response_model=Reservation)
async def update_reservation(reservation_id: str, update: ReservationUpdate):
    existing = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Reservation not found")
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    update_data["updatedAt"] = datetime.utcnow().isoformat()
    # Newly linking (or re-linking) a CRM guest during an edit — same bookkeeping
    # create_reservation does, so this reservation shows up on the guest's profile.
    new_customer_id = update_data.get("customerId")
    if new_customer_id and new_customer_id != existing.get("customerId"):
        await db.customers.update_one(
            {"id": new_customer_id}, {"$push": {"reservationIds": reservation_id}}
        )
    result = await db.reservations.find_one_and_update(
        {"id": reservation_id}, {"$set": update_data}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Reservation not found")
    result.pop("_id", None)
    return Reservation(**result)

@router.delete("/reservations/{reservation_id}")
async def delete_reservation(reservation_id: str):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if res.get("tableId"):
        await db.floor_tables.update_one(
            {"id": res["tableId"]},
            {"$set": {"status": "available", "currentReservationId": None}}
        )
    await db.reservations.delete_one({"id": reservation_id})
    try:
        from services.bookings_partner_client import mirror_reservation_status
        mirror_reservation_status(res, "cancelled")
    except Exception:
        pass
    return {"message": "Reservation deleted"}

@router.post("/reservations/{reservation_id}/seat")
async def seat_reservation(reservation_id: str, table_id: Optional[str] = None):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    tid = table_id or res.get("tableId")
    update_data = {"status": "seated", "seatedAt": datetime.utcnow().isoformat(), "updatedAt": datetime.utcnow().isoformat()}
    if tid:
        update_data["tableId"] = tid
        await db.floor_tables.update_one(
            {"id": tid}, {"$set": {"status": "occupied", "currentReservationId": reservation_id}}
        )
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_data})
    return {"message": "Guest seated", "tableId": tid}

@router.post("/reservations/{reservation_id}/complete")
async def complete_reservation(reservation_id: str):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {"status": "completed", "completedAt": datetime.utcnow().isoformat(), "updatedAt": datetime.utcnow().isoformat()}}
    )
    if res.get("tableId"):
        await db.floor_tables.update_one(
            {"id": res["tableId"]}, {"$set": {"status": "cleaning", "currentReservationId": None}}
        )
    return {"message": "Reservation completed"}

@router.post("/reservations/{reservation_id}/no-show")
async def mark_no_show(reservation_id: str, fee: float = 0):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {"status": "no_show", "noShowFee": fee, "updatedAt": datetime.utcnow().isoformat()}}
    )
    if res.get("customerId"):
        await db.customers.update_one({"id": res["customerId"]}, {"$inc": {"noShowCount": 1}})
    if res.get("tableId"):
        await db.floor_tables.update_one(
            {"id": res["tableId"]}, {"$set": {"status": "available", "currentReservationId": None}}
        )
    return {"message": "Marked as no-show"}

@router.get("/reservations/auto-assign/{reservation_id}")
async def auto_assign_table(reservation_id: str):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    party = res.get("partySize", 2)
    section_pref = res.get("section")
    query = {"status": "available", "isActive": True, "maxCovers": {"$gte": party}}
    if section_pref:
        query["section"] = section_pref
    tables = await db.floor_tables.find(query, {"_id": 0}).sort("maxCovers", 1).to_list(100)
    if not tables:
        return {"assigned": False, "message": "No suitable tables available"}
    best = tables[0]
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {"tableId": best["id"], "tableNumber": best.get("number", ""), "updatedAt": datetime.utcnow().isoformat()}}
    )
    await db.floor_tables.update_one(
        {"id": best["id"]}, {"$set": {"status": "reserved", "currentReservationId": reservation_id}}
    )
    return {"assigned": True, "table": best}


# ============ BOOKING BLACKOUTS ============
# Stops new incoming reservations for a date (or a range of dates) — e.g. a
# private event, staff training day, storm closure, or a fully-booked day the
# owner wants to lock down. Existing reservations are untouched.
#
# Collection: booking_blackouts  { id, date (YYYY-MM-DD), reason, blockUntil? }
# `blockUntil` is optional — when set, the blackout auto-expires (used for
# "pause bookings for the rest of today" style toggles).
# GET endpoints for /blackouts and /day-counts are defined above the
# /reservations/{id} route to avoid FastAPI catch-all path conflict.


@router.post("/reservations/blackouts")
async def create_blackout(data: dict):
    """Create a blackout for a single date OR a `fromDate`→`toDate` inclusive range."""
    import uuid
    reason = str(data.get("reason") or "Bookings paused").strip()
    now_iso = datetime.utcnow().isoformat()
    from datetime import date as _date, timedelta as _td
    def _parse(s):
        return _date.fromisoformat(s)
    if data.get("fromDate") and data.get("toDate"):
        d0 = _parse(data["fromDate"]); d1 = _parse(data["toDate"])
        if d1 < d0:
            raise HTTPException(status_code=400, detail="toDate must be on/after fromDate")
        created = []
        cur = d0
        while cur <= d1:
            doc = {"id": str(uuid.uuid4()), "date": cur.isoformat(), "reason": reason, "blockUntil": data.get("blockUntil"), "createdAt": now_iso}
            await db.booking_blackouts.update_one(
                {"date": cur.isoformat()},
                {"$set": {k: v for k, v in doc.items() if k != "id"},
                 "$setOnInsert": {"id": doc["id"]}},
                upsert=True,
            )
            created.append(cur.isoformat())
            cur += _td(days=1)
        return {"created": created, "count": len(created), "reason": reason}
    single = str(data.get("date") or "").strip()
    if not single:
        raise HTTPException(status_code=400, detail="Provide 'date' or 'fromDate'+'toDate'")
    doc = {"id": str(uuid.uuid4()), "date": single, "reason": reason, "blockUntil": data.get("blockUntil"), "createdAt": now_iso}
    await db.booking_blackouts.update_one(
        {"date": single},
        {"$set": {k: v for k, v in doc.items() if k != "id"},
         "$setOnInsert": {"id": doc["id"]}},
        upsert=True,
    )
    return {"created": [single], "count": 1, "reason": reason}


@router.delete("/reservations/blackouts/{date}")
async def delete_blackout(date: str):
    r = await db.booking_blackouts.delete_one({"date": date})
    return {"deleted": r.deleted_count, "date": date}


# ============ FLOOR PLANS API ============
@router.get("/floor-plans", response_model=List[FloorPlan])
async def get_floor_plans():
    plans = await db.floor_plans.find({}, {"_id": 0}).to_list(100)
    return [FloorPlan(**p) for p in plans]

@router.get("/floor-plans/{plan_id}", response_model=FloorPlan)
async def get_floor_plan(plan_id: str):
    plan = await db.floor_plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Floor plan not found")
    return FloorPlan(**plan)

@router.post("/floor-plans", response_model=FloorPlan)
async def create_floor_plan(plan: FloorPlanCreate):
    plan_obj = FloorPlan(**plan.dict())
    await db.floor_plans.insert_one(plan_obj.dict())
    return plan_obj

@router.put("/floor-plans/{plan_id}", response_model=FloorPlan)
async def update_floor_plan(plan_id: str, update: FloorPlanUpdate):
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    update_data["updatedAt"] = datetime.utcnow().isoformat()
    result = await db.floor_plans.find_one_and_update(
        {"id": plan_id}, {"$set": update_data}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Floor plan not found")
    result.pop("_id", None)
    return FloorPlan(**result)

@router.delete("/floor-plans/{plan_id}")
async def delete_floor_plan(plan_id: str):
    result = await db.floor_plans.delete_one({"id": plan_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Floor plan not found")
    return {"message": "Floor plan deleted"}

@router.post("/floor-plans/tables/{table_id}/status")
async def update_table_status(table_id: str, status: str, plan_id: Optional[str] = None):
    if plan_id:
        plan = await db.floor_plans.find_one({"id": plan_id}, {"_id": 0})
        if plan:
            tables = plan.get("tables", [])
            for t in tables:
                if t.get("id") == table_id:
                    t["status"] = status
                    break
            await db.floor_plans.update_one(
                {"id": plan_id}, {"$set": {"tables": tables, "updatedAt": datetime.utcnow().isoformat()}}
            )
    return {"message": f"Table {table_id} status updated to {status}"}

@router.post("/floor-plans/sections/{section_id}/assign")
async def assign_server_to_section(section_id: str, server_id: str, plan_id: str):
    plan = await db.floor_plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Floor plan not found")
    sections = plan.get("sections", [])
    for s in sections:
        if s.get("id") == section_id:
            s["serverId"] = server_id
            break
    await db.floor_plans.update_one(
        {"id": plan_id}, {"$set": {"sections": sections, "updatedAt": datetime.utcnow().isoformat()}}
    )
    return {"message": "Server assigned to section"}

# ============ WAITLIST API ============
@router.get("/waitlist", response_model=List[WaitlistEntry])
async def get_waitlist(status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    else:
        query["status"] = {"$in": ["waiting", "notified"]}
    entries = await db.waitlist.find(query, {"_id": 0}).sort("position", 1).to_list(1000)
    return [WaitlistEntry(**e) for e in entries]

@router.post("/waitlist", response_model=WaitlistEntry)
async def add_to_waitlist(entry: WaitlistEntryCreate):
    last = await db.waitlist.find({"status": "waiting"}).sort("position", -1).to_list(1)
    next_pos = (last[0]["position"] + 1) if last else 1
    entry_obj = WaitlistEntry(**entry.dict(), position=next_pos)
    doc = entry_obj.dict()
    await db.waitlist.insert_one(doc)
    return entry_obj

@router.put("/waitlist/{entry_id}", response_model=WaitlistEntry)
async def update_waitlist_entry(entry_id: str, update: WaitlistEntryUpdate):
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    result = await db.waitlist.find_one_and_update(
        {"id": entry_id}, {"$set": update_data}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    result.pop("_id", None)
    return WaitlistEntry(**result)

@router.post("/waitlist/{entry_id}/seat")
async def seat_waitlist_guest(entry_id: str, table_id: Optional[str] = None):
    entry = await db.waitlist.find_one({"id": entry_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    update_data = {"status": "seated", "seatedTime": datetime.utcnow().isoformat()}
    if table_id:
        update_data["tableId"] = table_id
    await db.waitlist.update_one({"id": entry_id}, {"$set": update_data})
    return {"message": "Guest seated from waitlist"}

@router.delete("/waitlist/{entry_id}")
async def remove_from_waitlist(entry_id: str):
    result = await db.waitlist.delete_one({"id": entry_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Removed from waitlist"}


# ============ AI TABLE AUTO-ASSIGN ============
@router.post("/reservations/{reservation_id}/ai-assign-table")
async def ai_assign_table(reservation_id: str):
    """Auto-pick the best table for a reservation based on:
      • party size fits seats (smallest fit wins to save large tables for big parties)
      • current table status (prefer available > reserved-for-different-party > occupied later)
      • section preference if set on reservation
      • time conflict avoidance (skip tables booked within ±90min of this slot)
    """
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    party = int(res.get("partySize", 2) or 2)

    tables = await db.floor_tables.find({}, {"_id": 0}).to_list(500)
    if not tables:
        return {"assigned": False, "reason": "No floor tables defined yet"}

    # Time window check — pull same-day reservations conflicting with this slot
    same_day = await db.reservations.find({"date": res.get("date"), "id": {"$ne": reservation_id}}, {"_id": 0}).to_list(500)
    def conflicts(table_id: str) -> bool:
        for r in same_day:
            if r.get("tableId") != table_id:
                continue
            try:
                t1 = datetime.fromisoformat(f"{res['date']}T{res['time']}:00")
                t2 = datetime.fromisoformat(f"{r['date']}T{r['time']}:00")
                if abs((t1 - t2).total_seconds()) < 90 * 60:
                    return True
            except Exception:
                continue
        return False

    preferred_section = (res.get("section") or "").lower()
    candidates = []
    for t in tables:
        capacity = int(t.get("capacity", 0) or 0)
        if capacity < party:
            continue
        if conflicts(t["id"]):
            continue
        score = capacity - party                     # smaller fit wins
        if preferred_section and (t.get("section") or "").lower() == preferred_section:
            score -= 5                               # boost section match
        if t.get("status") == "available":
            score -= 2
        candidates.append((score, t))

    if not candidates:
        return {"assigned": False, "reason": "No table fits this party / time slot"}

    candidates.sort(key=lambda x: x[0])
    chosen = candidates[0][1]
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {"tableId": chosen["id"], "tableNumber": chosen.get("number") or chosen.get("name"), "updatedAt": datetime.utcnow().isoformat()}}
    )
    await db.floor_tables.update_one(
        {"id": chosen["id"]},
        {"$set": {"status": "reserved", "currentReservationId": reservation_id}}
    )
    return {
        "assigned": True,
        "tableId": chosen["id"],
        "tableName": chosen.get("name") or chosen.get("number"),
        "section": chosen.get("section"),
        "score": candidates[0][0],
    }

@router.post("/walkins/ai-assign")
async def ai_assign_walkin(body: dict):
    """Walk-in helper: pick a table NOW for an unscheduled walk-in.
    body: { partySize, section?, customerId? }
    """
    party = int(body.get("partySize", 1) or 1)
    section = (body.get("section") or "").lower()
    tables = await db.floor_tables.find({}, {"_id": 0}).to_list(500)
    if not tables:
        raise HTTPException(status_code=404, detail="No floor tables defined")
    candidates = []
    for t in tables:
        if t.get("status") not in (None, "available", "cleaning"):
            continue
        cap = int(t.get("capacity", 0) or 0)
        if cap < party:
            continue
        score = cap - party
        if section and (t.get("section") or "").lower() == section:
            score -= 5
        if t.get("status") == "available":
            score -= 1
        candidates.append((score, t))
    if not candidates:
        return {"assigned": False, "reason": "No suitable table free right now"}
    candidates.sort(key=lambda x: x[0])
    chosen = candidates[0][1]
    walkin_id = f"WALK-{datetime.utcnow().strftime('%H%M%S')}"
    await db.floor_tables.update_one(
        {"id": chosen["id"]},
        {"$set": {"status": "occupied", "currentReservationId": walkin_id}}
    )
    return {
        "assigned": True, "walkinId": walkin_id,
        "tableId": chosen["id"], "tableName": chosen.get("name") or chosen.get("number"),
        "section": chosen.get("section"), "score": candidates[0][0],
    }
