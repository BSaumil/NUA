from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timezone
from database import db
import uuid

router = APIRouter()

# ============ MEMBER PORTAL (EatClub-style) ============

class MemberSignup(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str

class MemberLogin(BaseModel):
    email: EmailStr
    password: str

@router.post("/members/signup")
async def member_signup(req: MemberSignup, response: Response):
    """Public member registration"""
    from routes.auth import hash_password, create_access_token, create_refresh_token
    email = req.email.lower()
    existing = await db.members.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    member = {
        "id": f"MBR-{str(uuid.uuid4())[:8].upper()}",
        "name": req.name, "email": email, "phone": req.phone,
        "password_hash": hash_password(req.password),
        "points": 50,  # Welcome bonus
        "tier": "Bronze",
        "totalSpent": 0, "visits": 0,
        "vouchers": [
            {
                "id": f"VCH-{str(uuid.uuid4())[:8].upper()}",
                "name": "Welcome 15% Off",
                "type": "percentage",
                "value": 15,
                "minSpend": 0,
                "expiresAt": (datetime.now(timezone.utc).replace(month=12, day=31)).isoformat(),
                "status": "active",
                "code": f"WELCOME{str(uuid.uuid4())[:4].upper()}",
            }
        ],
        "referralCode": f"NUVA-{str(uuid.uuid4())[:6].upper()}",
        "joinedAt": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    await db.members.insert_one(member)
    member.pop("_id", None)
    member.pop("password_hash", None)

    # Free base identity layer — a loyalty signup is one of the touchpoints
    # that creates/matches a Customer identity record.
    try:
        from services.customer_identity import record_touchpoint, ensure_loyalty_account, addon_enabled
        identity = await record_touchpoint(
            phone=req.phone, email=email, name=req.name, source="loyalty_signup",
        )
        if identity and await addon_enabled("loyalty.enabled"):
            await ensure_loyalty_account(identity["id"])
    except Exception:
        pass

    access = create_access_token(member["id"], email, "member")
    response.set_cookie("member_token", access, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    return {"member": member, "token": access}

@router.post("/members/login")
async def member_login(req: MemberLogin, response: Response):
    from routes.auth import verify_password, create_access_token
    email = req.email.lower()
    member = await db.members.find_one({"email": email})
    if not member or not verify_password(req.password, member.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    member.pop("_id", None)
    member.pop("password_hash", None)
    access = create_access_token(member["id"], email, "member")
    response.set_cookie("member_token", access, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    return {"member": member, "token": access}

@router.get("/members/me")
async def member_me(token: str = ""):
    import jwt, os
    secret = os.environ["JWT_SECRET"]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        member = await db.members.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        return member
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/members/{member_id}/vouchers")
async def get_member_vouchers(member_id: str):
    member = await db.members.find_one({"id": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member.get("vouchers", [])

# ============ VOUCHER MANAGEMENT (Staff) ============
@router.post("/vouchers/create")
async def create_voucher(data: dict):
    voucher = {
        "id": f"VCH-{str(uuid.uuid4())[:8].upper()}",
        "name": data.get("name", "Promotion"),
        "type": data.get("type", "percentage"),  # percentage, fixed, free_item
        "value": data.get("value", 10),
        "minSpend": data.get("minSpend", 0),
        "maxUses": data.get("maxUses", 100),
        "usedCount": 0,
        "code": data.get("code", f"PROMO{str(uuid.uuid4())[:4].upper()}"),
        "expiresAt": data.get("expiresAt", ""),
        "targetTier": data.get("targetTier"),  # None = all members
        "status": "active",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.vouchers.insert_one(voucher)
    voucher.pop("_id", None)
    return voucher

@router.get("/vouchers")
async def get_all_vouchers():
    vouchers = await db.vouchers.find({}, {"_id": 0}).to_list(1000)
    return vouchers

@router.post("/vouchers/{code}/redeem")
async def redeem_voucher(code: str, member_id: str, order_total: float = 0):
    voucher = await db.vouchers.find_one({"code": code, "status": "active"})
    if not voucher:
        # Also check member's personal vouchers
        member = await db.members.find_one({"id": member_id}, {"_id": 0})
        if member:
            for v in member.get("vouchers", []):
                if v.get("code") == code and v.get("status") == "active":
                    voucher = v
                    break
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher not found or expired")
    if voucher.get("minSpend", 0) > order_total:
        raise HTTPException(status_code=400, detail=f"Minimum spend ${voucher['minSpend']} required")

    discount = 0
    if voucher["type"] == "percentage":
        discount = order_total * (voucher["value"] / 100)
    elif voucher["type"] == "fixed":
        discount = voucher["value"]

    # Update voucher usage
    if voucher.get("id") and voucher.get("maxUses"):
        await db.vouchers.update_one({"id": voucher["id"]}, {"$inc": {"usedCount": 1}})

    return {"discount": round(discount, 2), "voucherName": voucher.get("name", ""), "code": code}

# ============ SOCIAL SHARING ============
@router.get("/members/share-link/{member_id}")
async def get_share_link(member_id: str):
    member = await db.members.find_one({"id": member_id}, {"_id": 0})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    ref_code = member.get("referralCode", "")
    base = "/join"
    return {
        "bookingLink": f"{base}?ref={ref_code}",
        "shareText": f"Join me at NUVA! Sign up with my code {ref_code} and get 15% off your first meal.",
        "referralCode": ref_code,
        "socialLinks": {
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u=nuva.com{base}?ref={ref_code}",
            "twitter": f"https://twitter.com/intent/tweet?text=Join%20me%20at%20NUVA!%20Use%20code%20{ref_code}&url=nuva.com{base}",
            "whatsapp": f"https://wa.me/?text=Join%20me%20at%20NUVA!%20Sign%20up%20with%20code%20{ref_code}%20and%20get%2015%25%20off!",
        }
    }

# ============ MEMBER STATS (Staff view) ============
@router.get("/members/stats")
async def get_member_stats():
    members = await db.members.find({}, {"_id": 0, "password_hash": 0}).to_list(10000)
    total = len(members)
    by_tier = {}
    for m in members:
        t = m.get("tier", "Bronze")
        by_tier[t] = by_tier.get(t, 0) + 1
    total_spent = sum(m.get("totalSpent", 0) for m in members)
    return {
        "totalMembers": total,
        "byTier": by_tier,
        "totalSpent": round(total_spent, 2),
        "avgSpend": round(total_spent / max(total, 1), 2),
        "recentSignups": sorted(members, key=lambda m: m.get("joinedAt", ""), reverse=True)[:10],
    }
