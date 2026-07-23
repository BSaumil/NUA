from fastapi import APIRouter, HTTPException, Request, Depends
from deps import get_user, require_owner, require_owner_or_manager
from database import db
from datetime import datetime, timezone, timedelta
from utils.au_payroll import effective_hourly_rate
import uuid

router = APIRouter()

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

# ============ STAFF ROSTER ============
@router.get("/staff/roster")
async def get_roster( week_start: str = None, _: dict = Depends(require_owner_or_manager)):
    query = {}
    if week_start:
        query["weekStart"] = week_start
    shifts = await db.roster_shifts.find(query, {"_id": 0}).sort("date", 1).to_list(5000)
    return shifts

@router.post("/staff/roster")
async def create_roster_shift(data: dict, _: dict = Depends(require_owner_or_manager)):
    shift = {
        "id": f"SHIFT-{str(uuid.uuid4())[:8].upper()}",
        "staffId": data.get("staffId"), "staffName": data.get("staffName"),
        "date": data.get("date"), "weekStart": data.get("weekStart"),
        "startTime": data.get("startTime", "09:00"), "endTime": data.get("endTime", "17:00"),
        "role": data.get("role", ""), "notes": data.get("notes", ""),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.roster_shifts.insert_one(shift)
    shift.pop("_id", None)
    return shift

@router.put("/staff/roster/{shift_id}")
async def update_roster_shift(shift_id: str, data: dict, _: dict = Depends(require_owner_or_manager)):
    allowed = {"date", "startTime", "endTime", "role", "notes", "staffId", "staffName", "weekStart"}
    update = {k: v for k, v in data.items() if k in allowed}
    result = await db.roster_shifts.find_one_and_update({"id": shift_id}, {"$set": update}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Shift not found")
    result.pop("_id", None)
    return result

@router.delete("/staff/roster/{shift_id}")
async def delete_roster_shift(shift_id: str, _: dict = Depends(require_owner_or_manager)):
    await db.roster_shifts.delete_one({"id": shift_id})
    return {"message": "Shift deleted"}

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
