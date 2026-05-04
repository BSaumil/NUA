from fastapi import APIRouter, HTTPException, Request
from database import db
from datetime import datetime, timezone
import uuid

router = APIRouter()

# ============ TABLE COMBINATIONS ============
@router.get("/tables/combinations")
async def get_table_combinations():
    combos = await db.table_combinations.find({}, {"_id": 0}).to_list(200)
    return combos

@router.post("/tables/combinations")
async def create_table_combination(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    combo = {
        "id": f"COMBO-{str(uuid.uuid4())[:8].upper()}",
        "name": data.get("name", f"Combo {data.get('tableIds', [])}"),
        "tableIds": data.get("tableIds", []),
        "maxCovers": data.get("maxCovers", 0),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.table_combinations.insert_one(combo)
    combo.pop("_id", None)
    return combo

@router.delete("/tables/combinations/{combo_id}")
async def delete_table_combination(combo_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    await db.table_combinations.delete_one({"id": combo_id})
    return {"message": "Combination deleted"}

# ============ BOOKING RULES & SETTINGS ============
@router.get("/booking/rules")
async def get_booking_rules():
    s = await db.settings.find_one({"key": "booking_rules"}, {"_id": 0})
    return s.get("value", {}) if s else {
        "maxOnlinePartySize": 10, "maxAdvanceDays": 60,
        "bookingWindowMinutes": 30, "autoConfirm": True,
        "requireDeposit": False, "depositAmount": 0,
        "noShowFee": 0, "cancellationHours": 2,
    }

@router.post("/booking/rules")
async def save_booking_rules(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    await db.settings.update_one({"key": "booking_rules"}, {"$set": {"key": "booking_rules", "value": data}}, upsert=True)
    return {"message": "Booking rules saved"}

# ============ BOOKING SCHEDULE (Shifts) ============
@router.get("/booking/schedule")
async def get_booking_schedule():
    shifts = await db.booking_shifts.find({}, {"_id": 0}).to_list(50)
    if not shifts:
        return [
            {"id": "shift-breakfast", "name": "Breakfast", "startTime": "07:00", "endTime": "11:00", "interval": 30, "tables": [], "enabled": True},
            {"id": "shift-lunch", "name": "Lunch", "startTime": "11:30", "endTime": "15:00", "interval": 30, "tables": [], "enabled": True},
            {"id": "shift-dinner", "name": "Dinner", "startTime": "17:00", "endTime": "22:00", "interval": 30, "tables": [], "enabled": True},
        ]
    return shifts

@router.post("/booking/schedule")
async def save_booking_schedule(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    shifts = data.get("shifts", [])
    await db.booking_shifts.delete_many({})
    for s in shifts:
        if not s.get("id"):
            s["id"] = f"shift-{str(uuid.uuid4())[:8]}"
        await db.booking_shifts.insert_one(s)
    return {"message": f"{len(shifts)} shifts saved"}

# ============ BOOKING EXPERIENCES ============
@router.get("/booking/experiences")
async def get_experiences():
    exps = await db.booking_experiences.find({}, {"_id": 0}).to_list(50)
    return exps

@router.post("/booking/experiences")
async def create_experience(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    exp = {
        "id": f"EXP-{str(uuid.uuid4())[:8].upper()}",
        "name": data.get("name", ""), "description": data.get("description", ""),
        "days": data.get("days", []),  # ["Monday","Friday",...]
        "startDate": data.get("startDate"), "endDate": data.get("endDate"),
        "pricePerPerson": data.get("pricePerPerson", 0),
        "maxBookings": data.get("maxBookings", 50),
        "active": data.get("active", True),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.booking_experiences.insert_one(exp)
    exp.pop("_id", None)
    return exp

@router.put("/booking/experiences/{exp_id}")
async def update_experience(exp_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    result = await db.booking_experiences.find_one_and_update({"id": exp_id}, {"$set": data}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    result.pop("_id", None)
    return result

@router.delete("/booking/experiences/{exp_id}")
async def delete_experience(exp_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    await db.booking_experiences.delete_one({"id": exp_id})
    return {"message": "Experience deleted"}

# ============ CLUBMEMBER OFFERS (EatClub-style) ============
@router.get("/clubmember/offers")
async def get_club_offers():
    offers = await db.club_offers.find({}, {"_id": 0}).to_list(100)
    return offers

@router.post("/clubmember/offers")
async def create_club_offer(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    discount = data.get("discount", 20)
    if discount < 20 or discount > 50:
        raise HTTPException(status_code=400, detail="Discount must be between 20% and 50%")
    offer = {
        "id": f"CLUB-{str(uuid.uuid4())[:8].upper()}",
        "title": data.get("title", ""), "description": data.get("description", ""),
        "discount": discount,
        "startDate": data.get("startDate"), "startTime": data.get("startTime", "00:00"),
        "endDate": data.get("endDate"), "endTime": data.get("endTime", "23:59"),
        "totalSlots": data.get("totalSlots", 10),
        "claimedSlots": 0, "active": data.get("active", True),
        "socialPlatforms": data.get("socialPlatforms", ["instagram", "facebook"]),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.club_offers.insert_one(offer)
    offer.pop("_id", None)
    return offer

@router.put("/clubmember/offers/{offer_id}")
async def update_club_offer(offer_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    allowed = {"title", "description", "discount", "startDate", "startTime", "endDate", "endTime", "totalSlots", "active", "socialPlatforms"}
    update = {k: v for k, v in data.items() if k in allowed}
    result = await db.club_offers.find_one_and_update({"id": offer_id}, {"$set": update}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    result.pop("_id", None)
    return result

@router.delete("/clubmember/offers/{offer_id}")
async def delete_club_offer(offer_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    await db.club_offers.delete_one({"id": offer_id})
    return {"message": "Offer deleted"}

# Public endpoint for members to claim
@router.post("/clubmember/offers/{offer_id}/claim")
async def claim_club_offer(offer_id: str, data: dict):
    offer = await db.club_offers.find_one({"id": offer_id})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if not offer.get("active"):
        raise HTTPException(status_code=400, detail="Offer is no longer active")
    if offer.get("claimedSlots", 0) >= offer.get("totalSlots", 0):
        raise HTTPException(status_code=400, detail="Offer is fully claimed")
    await db.club_offers.update_one({"id": offer_id}, {"$inc": {"claimedSlots": 1}})
    claim = {
        "id": f"CLAIM-{str(uuid.uuid4())[:8].upper()}",
        "offerId": offer_id, "memberName": data.get("name", ""), "memberEmail": data.get("email", ""),
        "discount": offer.get("discount"), "claimedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.club_claims.insert_one(claim)
    claim.pop("_id", None)
    return claim
