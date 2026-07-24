from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from deps import get_user, require_owner, require_owner_or_manager
from database import db
from datetime import datetime, timezone, timedelta, date as _date_cls
from utils.au_payroll import effective_hourly_rate
import uuid

router = APIRouter()

_WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def _resolve_shift_date(day_name: str, week_start: Optional[str]) -> str:
    """Roster shifts store a weekday name (e.g. 'Monday') + a reference weekStart
    (ISO Monday). Resolve the actual calendar date so it can be checked against
    blackout ranges / approved leave, mirroring v15_features.py's auto-roster logic."""
    try:
        base = _date_cls.fromisoformat(week_start) if week_start else _date_cls.today()
        offset = _WEEKDAYS.index(day_name)
        return (base + timedelta(days=offset)).isoformat()
    except Exception:
        return ""


async def _blackout_conflict(staff_id: Optional[str], day_name: Optional[str], week_start: Optional[str]) -> Optional[str]:
    """Reason string if staff_id can't work this roster slot (weekly availability,
    an explicit blackout range, or approved time off) — None if it's clear."""
    if not staff_id or not day_name:
        return None
    date_iso = _resolve_shift_date(day_name, week_start)
    avail = await db.staff_availability.find_one({"staffId": staff_id}, {"_id": 0})
    if avail:
        weekly = avail.get("weeklyAvailable") or []
        if weekly and day_name[:3] not in weekly and day_name not in weekly:
            return f"{day_name} is outside this staff member's weekly availability"
        if date_iso:
            for b in (avail.get("blackoutDates") or []):
                f, t = b.get("from") or "", b.get("to") or b.get("from") or ""
                if f and t and f <= date_iso <= t:
                    return b.get("reason") or "Staff member has a blackout period on this date"
    if date_iso:
        leave = await db.time_off_requests.find_one({
            "userId": staff_id, "status": "approved",
            "startDate": {"$lte": date_iso}, "endDate": {"$gte": date_iso},
        })
        if leave:
            return f"Staff member has approved time off covering {date_iso}"
    return None

# ============ STAFF PIN LOGIN ============
@router.post("/auth/pin-login")
async def pin_login(data: dict):
    """Login with 2-4 digit PIN code"""
    import jwt, os
    pin = str(data.get("pin", ""))
    if not pin or len(pin) < 2 or len(pin) > 4:
        raise HTTPException(status_code=400, detail="PIN must be 2-4 digits")
    user = await db.auth_users.find_one({"pin": pin, "status": "active"})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    user.pop("_id", None)
    user.pop("password_hash", None)
    token = jwt.encode(
        {"sub": user["id"], "email": user["email"], "role": user["role"],
         "exp": datetime.now(timezone.utc) + timedelta(hours=8), "type": "access"},
        os.environ["JWT_SECRET"], algorithm="HS256"
    )
    return {"user": user, "token": token}

@router.post("/auth/staff/{staff_id}/set-pin")
async def set_staff_pin(staff_id: str, data: dict, _: dict = Depends(require_owner)):
    """Owner assigns a PIN to staff member"""
    pin = str(data.get("pin", ""))
    if not pin or len(pin) < 2 or len(pin) > 4 or not pin.isdigit():
        raise HTTPException(status_code=400, detail="PIN must be 2-4 digits")
    existing = await db.auth_users.find_one({"pin": pin, "id": {"$ne": staff_id}})
    if existing:
        raise HTTPException(status_code=400, detail="PIN already in use by another staff member")
    await db.auth_users.update_one({"id": staff_id}, {"$set": {"pin": pin}})
    return {"message": f"PIN set for staff member"}

# ============ TIMECARDS — CLOCK IN/OUT ============
@router.post("/staff/clock-in")
async def clock_in(user: dict = Depends(get_user)):
    active = await db.timecards.find_one({"staffId": user["id"], "clockOut": None}, {"_id": 0})
    if active:
        raise HTTPException(status_code=400, detail="Already clocked in")
    tc = {
        "id": f"TC-{str(uuid.uuid4())[:8].upper()}",
        "staffId": user["id"], "staffName": user["name"], "role": user["role"],
        "clockIn": datetime.now(timezone.utc).isoformat(),
        "clockOut": None, "breakMinutes": 0, "hoursWorked": 0,
        "payRate": user.get("payRate", 0),
        "salaryType": user.get("salaryType", "hourly"),
    }
    await db.timecards.insert_one(tc)
    tc.pop("_id", None)
    return tc

@router.post("/staff/clock-out")
async def clock_out(data: dict, user: dict = Depends(get_user)):
    tc = await db.timecards.find_one({"staffId": user["id"], "clockOut": None})
    if not tc:
        raise HTTPException(status_code=400, detail="Not clocked in")
    now = datetime.now(timezone.utc)
    clock_in_time = datetime.fromisoformat(tc["clockIn"])
    if clock_in_time.tzinfo is None:
        clock_in_time = clock_in_time.replace(tzinfo=timezone.utc)
    break_mins = int(data.get("breakMinutes", 0))
    hours = (now - clock_in_time).total_seconds() / 3600 - (break_mins / 60)
    hours = max(hours, 0)
    await db.timecards.update_one({"id": tc["id"]}, {"$set": {
        "clockOut": now.isoformat(), "breakMinutes": break_mins,
        "hoursWorked": round(hours, 2),
    }})
    tc.pop("_id", None)
    tc["clockOut"] = now.isoformat()
    tc["hoursWorked"] = round(hours, 2)
    return tc

@router.get("/staff/my-status")
async def my_clock_status(user: dict = Depends(get_user)):
    active = await db.timecards.find_one({"staffId": user["id"], "clockOut": None}, {"_id": 0})
    return {"clockedIn": active is not None, "currentShift": active}

@router.get("/staff/timecards")
async def get_timecards( staff_id: str = None, period: str = "week", user: dict = Depends(get_user)):
    if user["role"] not in ("owner", "manager"):
        staff_id = user["id"]
    query = {}
    if staff_id:
        query["staffId"] = staff_id
    cards = await db.timecards.find(query, {"_id": 0}).sort("clockIn", -1).to_list(5000)
    return cards

@router.put("/staff/timecards/{timecard_id}")
async def edit_timecard(timecard_id: str, data: dict, user: dict = Depends(require_owner_or_manager)):
    """Owner/manager fix-up for a clocked timecard — a missed clock-out, wrong
    break, etc. Self-service clock-in/out never lets this happen automatically,
    so this is the only path to correct it after the fact. Keeps the original
    values + who/when it was edited for audit."""
    existing = await db.timecards.find_one({"id": timecard_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Timecard not found")

    update = {}
    if "clockIn" in data:
        update["clockIn"] = data["clockIn"]
    if "clockOut" in data:
        update["clockOut"] = data["clockOut"]
    if "breakMinutes" in data:
        update["breakMinutes"] = int(data["breakMinutes"])

    clock_in = update.get("clockIn", existing.get("clockIn"))
    clock_out = update.get("clockOut", existing.get("clockOut"))
    break_mins = update.get("breakMinutes", existing.get("breakMinutes", 0))
    if clock_in and clock_out:
        start = datetime.fromisoformat(clock_in)
        end = datetime.fromisoformat(clock_out)
        if end <= start:
            raise HTTPException(status_code=400, detail="Clock-out must be after clock-in")
        hours = (end - start).total_seconds() / 3600 - (break_mins / 60)
        update["hoursWorked"] = round(max(hours, 0), 2)

    update["editedBy"] = user["name"]
    update["editedAt"] = datetime.now(timezone.utc).isoformat()
    update.setdefault("originalValues", {
        "clockIn": existing.get("clockIn"), "clockOut": existing.get("clockOut"),
        "breakMinutes": existing.get("breakMinutes"), "hoursWorked": existing.get("hoursWorked"),
    })
    # Don't clobber originalValues on a second edit — keep the FIRST pre-edit state.
    if existing.get("originalValues"):
        update["originalValues"] = existing["originalValues"]

    result = await db.timecards.find_one_and_update({"id": timecard_id}, {"$set": update}, return_document=True)
    result.pop("_id", None)
    return result

# ============ STAFF ROSTER ============
@router.get("/staff/roster")
async def get_roster( week_start: str = None, user: dict = Depends(get_user)):
    # Owner/manager see the full roster; everyone else only sees their own
    # shifts — same scoping rule GET /staff/timecards already uses.
    query = {}
    if week_start:
        query["weekStart"] = week_start
    if user["role"] not in ("owner", "manager"):
        query["staffId"] = user["id"]
    shifts = await db.roster_shifts.find(query, {"_id": 0}).sort("date", 1).to_list(5000)
    return shifts

@router.post("/staff/roster")
async def create_roster_shift(data: dict, _: dict = Depends(require_owner_or_manager)):
    conflict = await _blackout_conflict(data.get("staffId"), data.get("date"), data.get("weekStart"))
    if conflict and not data.get("overrideBlackout"):
        raise HTTPException(status_code=409, detail=conflict)
    shift = {
        "id": f"SHIFT-{str(uuid.uuid4())[:8].upper()}",
        "staffId": data.get("staffId"), "staffName": data.get("staffName"),
        "date": data.get("date"), "weekStart": data.get("weekStart"),
        "startTime": data.get("startTime", "09:00"), "endTime": data.get("endTime", "17:00"),
        "role": data.get("role", ""), "notes": data.get("notes", ""),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "blackoutOverridden": bool(conflict),
        "blackoutOverrideReason": conflict,
    }
    await db.roster_shifts.insert_one(shift)
    shift.pop("_id", None)
    try:
        from services import realtime
        await realtime.broadcast({"type": "roster.updated", "shiftId": shift["id"], "staffId": shift["staffId"]})
    except Exception:
        pass
    return shift

@router.put("/staff/roster/{shift_id}")
async def update_roster_shift(shift_id: str, data: dict, _: dict = Depends(require_owner_or_manager)):
    existing = await db.roster_shifts.find_one({"id": shift_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Shift not found")
    staff_id = data.get("staffId", existing.get("staffId"))
    day = data.get("date", existing.get("date"))
    week_start = data.get("weekStart", existing.get("weekStart"))
    conflict = await _blackout_conflict(staff_id, day, week_start)
    if conflict and not data.get("overrideBlackout"):
        raise HTTPException(status_code=409, detail=conflict)
    allowed = {"date", "startTime", "endTime", "role", "notes", "staffId", "staffName", "weekStart"}
    update = {k: v for k, v in data.items() if k in allowed}
    update["blackoutOverridden"] = bool(conflict)
    update["blackoutOverrideReason"] = conflict
    result = await db.roster_shifts.find_one_and_update({"id": shift_id}, {"$set": update}, return_document=True)
    result.pop("_id", None)
    try:
        from services import realtime
        await realtime.broadcast({"type": "roster.updated", "shiftId": shift_id, "staffId": result.get("staffId")})
    except Exception:
        pass
    return result

@router.delete("/staff/roster/{shift_id}")
async def delete_roster_shift(shift_id: str, _: dict = Depends(require_owner_or_manager)):
    await db.roster_shifts.delete_one({"id": shift_id})
    return {"message": "Shift deleted"}

# ============ TIME OFF / LEAVE REQUESTS ============
class TimeOffRequestCreate(BaseModel):
    startDate: str  # YYYY-MM-DD
    endDate: str    # YYYY-MM-DD
    reason: str
    staffId: Optional[str] = None  # owner/manager filing on someone else's behalf

@router.post("/staff/time-off")
async def request_time_off(data: TimeOffRequestCreate, user: dict = Depends(get_user)):
    if data.endDate < data.startDate:
        raise HTTPException(status_code=400, detail="End date must be on or after start date")
    target_id = data.staffId if (data.staffId and user["role"] in ("owner", "manager")) else user["id"]
    target = user if target_id == user["id"] else await db.auth_users.find_one({"id": target_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="Staff member not found")
    doc = {
        "id": f"TOFF-{str(uuid.uuid4())[:8].upper()}",
        "userId": target_id, "userName": target.get("name", ""),
        "startDate": data.startDate, "endDate": data.endDate, "reason": data.reason,
        "status": "pending", "approvedBy": None, "notes": None,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.time_off_requests.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc

@router.get("/staff/time-off")
async def list_time_off(staff_id: str = None, status: str = None, user: dict = Depends(get_user)):
    query = {}
    if user["role"] not in ("owner", "manager"):
        query["userId"] = user["id"]
    elif staff_id:
        query["userId"] = staff_id
    if status:
        query["status"] = status
    rows = await db.time_off_requests.find(query, {"_id": 0}).sort("createdAt", -1).to_list(2000)
    return rows

@router.post("/staff/time-off/{request_id}/approve")
async def approve_time_off(request_id: str, user: dict = Depends(require_owner_or_manager)):
    result = await db.time_off_requests.find_one_and_update(
        {"id": request_id}, {"$set": {"status": "approved", "approvedBy": user["name"]}}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Request not found")
    result.pop("_id", None)
    # Surface any already-scheduled shifts that now conflict with the leave —
    # approving doesn't auto-remove them, the owner/manager decides.
    conflicts = []
    async for shift in db.roster_shifts.find({"staffId": result["userId"]}, {"_id": 0}):
        shift_date = _resolve_shift_date(shift.get("date", ""), shift.get("weekStart"))
        if shift_date and result["startDate"] <= shift_date <= result["endDate"]:
            conflicts.append(shift)
    result["conflictingShifts"] = conflicts
    return result

@router.post("/staff/time-off/{request_id}/reject")
async def reject_time_off(request_id: str, data: dict, user: dict = Depends(require_owner_or_manager)):
    result = await db.time_off_requests.find_one_and_update(
        {"id": request_id},
        {"$set": {"status": "denied", "approvedBy": user["name"], "notes": data.get("notes")}},
        return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Request not found")
    result.pop("_id", None)
    return result

@router.delete("/staff/time-off/{request_id}")
async def cancel_time_off(request_id: str, user: dict = Depends(get_user)):
    existing = await db.time_off_requests.find_one({"id": request_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Request not found")
    is_owner_of_request = existing["userId"] == user["id"]
    if not is_owner_of_request and user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Not your request")
    if existing["status"] != "pending" and user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=400, detail="Only pending requests can be cancelled")
    await db.time_off_requests.delete_one({"id": request_id})
    return {"message": "Request cancelled"}

# ============ PAYRUN ============
@router.get("/payrun/calculate")
async def calculate_payrun( period: str = "week", _: dict = Depends(require_owner)):

    now = datetime.now(timezone.utc)
    if period == "week":
        start = (now - timedelta(days=7))
    elif period == "fortnight":
        start = (now - timedelta(days=14))
    elif period == "month":
        start = now.replace(day=1)
    elif period == "quarter":
        q = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=q, day=1)
    elif period == "year":
        start = now.replace(month=1, day=1)
    else:
        start = (now - timedelta(days=7))

    staff = await db.auth_users.find({"role": {"$ne": "owner"}, "status": "active"}, {"_id": 0, "password_hash": 0}).to_list(100)
    timecards = await db.timecards.find({"clockOut": {"$ne": None}}, {"_id": 0}).to_list(50000)

    payroll = []
    total_gross = 0
    total_super = 0
    total_tax = 0
    total_net = 0

    for s in staff:
        cards = [tc for tc in timecards if tc.get("staffId") == s["id"]]
        total_hours = sum(tc.get("hoursWorked", 0) for tc in cards)
        rate = effective_hourly_rate(s.get("payRate", 0), s.get("salaryType"))
        gross = round(total_hours * rate, 2)
        super_amount = round(gross * 0.115, 2)  # 11.5% super in AU
        tax = round(gross * 0.20, 2)  # Approx withholding
        net = round(gross - tax, 2)

        payroll.append({
            "staffId": s["id"], "name": s["name"], "role": s["role"],
            "payRate": rate, "totalHours": round(total_hours, 2),
            "grossPay": gross, "super": super_amount, "tax": tax, "netPay": net,
            "timecardCount": len(cards),
        })
        total_gross += gross
        total_super += super_amount
        total_tax += tax
        total_net += net

    return {
        "period": period,
        "dateRange": {"start": start.isoformat(), "end": now.isoformat()},
        "staffPayroll": payroll,
        "totals": {
            "grossPay": round(total_gross, 2), "super": round(total_super, 2),
            "tax": round(total_tax, 2), "netPay": round(total_net, 2),
            "totalStaff": len(payroll),
        }
    }

@router.post("/payrun/process")
async def process_payrun(data: dict, user: dict = Depends(require_owner)):

    payrun = {
        "id": f"PAY-{str(uuid.uuid4())[:8].upper()}",
        "period": data.get("period", "week"),
        "processedBy": user["id"],
        "staffPayroll": data.get("staffPayroll", []),
        "totals": data.get("totals", {}),
        "status": "processed",
        "processedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.payruns.insert_one(payrun)
    payrun.pop("_id", None)

    # Create expense record for Accounting
    await db.expenses.insert_one({
        "id": f"EXP-{str(uuid.uuid4())[:8].upper()}",
        "category": "Wages",
        "description": f"Payrun {payrun['id']} - {data.get('period', 'week')}",
        "amount": data.get("totals", {}).get("grossPay", 0),
        "gstAmount": 0,
        "date": datetime.now(timezone.utc).isoformat(),
        "payrunId": payrun["id"],
    })
    # Super expense
    await db.expenses.insert_one({
        "id": f"EXP-{str(uuid.uuid4())[:8].upper()}",
        "category": "Superannuation",
        "description": f"Super for payrun {payrun['id']}",
        "amount": data.get("totals", {}).get("super", 0),
        "gstAmount": 0,
        "date": datetime.now(timezone.utc).isoformat(),
        "payrunId": payrun["id"],
    })

    return payrun

@router.get("/payrun/history")
async def get_payrun_history(_: dict = Depends(require_owner)):
    runs = await db.payruns.find({}, {"_id": 0}).sort("processedAt", -1).to_list(100)
    return runs

# ============ STAFF REPORTS ============
@router.get("/staff/reports")
async def get_staff_reports( period: str = "week", _: dict = Depends(require_owner_or_manager)):

    staff = await db.auth_users.find({"status": "active"}, {"_id": 0, "password_hash": 0}).to_list(100)
    timecards = await db.timecards.find({}, {"_id": 0}).to_list(50000)
    payruns = await db.payruns.find({}, {"_id": 0}).to_list(100)

    staff_stats = []
    for s in staff:
        if s["role"] == "owner":
            continue
        cards = [tc for tc in timecards if tc.get("staffId") == s["id"]]
        completed = [tc for tc in cards if tc.get("clockOut")]
        total_hours = sum(tc.get("hoursWorked", 0) for tc in completed)
        total_shifts = len(completed)
        avg_hours = total_hours / max(total_shifts, 1)
        rate = effective_hourly_rate(s.get("payRate", 0), s.get("salaryType"))
        total_wages = round(total_hours * rate, 2)

        staff_stats.append({
            "id": s["id"], "name": s["name"], "role": s["role"],
            "payRate": rate,
            "totalShifts": total_shifts, "totalHours": round(total_hours, 2),
            "avgHoursPerShift": round(avg_hours, 2), "totalWages": total_wages,
            "currentlyClockedIn": any(tc.get("clockOut") is None for tc in cards),
        })

    total_wages = sum(s["totalWages"] for s in staff_stats)
    total_hours = sum(s["totalHours"] for s in staff_stats)

    return {
        "period": period,
        "staffStats": staff_stats,
        "summary": {
            "totalStaff": len(staff_stats),
            "totalHours": round(total_hours, 2),
            "totalWages": round(total_wages, 2),
            "totalPayruns": len(payruns),
        }
    }

# ============ RECEIPT SETTINGS ============
@router.get("/receipt/settings")
async def get_receipt_settings():
    s = await db.settings.find_one({"key": "receipt_config"}, {"_id": 0})
    return s.get("value", {}) if s else {
        "logoUrl": "", "showPaymentQR": True, "showSocialQR": True,
        "showPromoQR": True, "socialMediaUrl": "", "promoText": "",
        "businessName": "NUA", "businessAddress": "", "businessPhone": "",
    }

@router.post("/receipt/settings")
async def save_receipt_settings(data: dict, _: dict = Depends(require_owner_or_manager)):
    await db.settings.update_one(
        {"key": "receipt_config"},
        {"$set": {"key": "receipt_config", "value": data}},
        upsert=True
    )
    return {"message": "Receipt settings saved"}
