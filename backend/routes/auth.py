from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone, timedelta
from database import db
import bcrypt
import jwt
import os
import secrets

router = APIRouter(prefix="/auth")

JWT_ALGORITHM = "HS256"
ROLES_HIERARCHY = {"owner": 4, "manager": 3, "cashier": 2, "kitchen": 1}

ROLE_PERMISSIONS = {
    "owner": ["*"],
    "manager": ["pos", "tables", "customers", "reservations", "kitchen", "floor-plan", "waitlist",
                "products", "inventory", "promotions", "analytics", "automation", "loyalty",
                "forecasting", "menu-engineering", "what-if", "pre-shift", "command-center",
                "integrations", "ai-pantry", "members", "feedback", "reports"],
    "cashier": ["pos", "tables", "customers", "reservations", "waitlist", "products"],
    "kitchen": ["kitchen", "pre-shift"],
}

def _secret():
    return os.environ["JWT_SECRET"]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {"sub": user_id, "email": email, "role": role,
               "exp": datetime.now(timezone.utc) + timedelta(hours=8), "type": "access"}
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.auth_users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(*roles):
    async def checker(request: Request):
        user = await get_current_user(request)
        if user["role"] not in roles and user["role"] != "owner":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

def _set_tokens(response: Response, access: str, refresh: str):
    response.set_cookie("access_token", access, httponly=True, secure=False, samesite="lax", max_age=28800, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")

# Models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "cashier"
    businessId: Optional[str] = None
    payRate: Optional[float] = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

# --- Endpoints ---
@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    email = req.email.lower()
    # Brute force check
    identifier = f"{request.client.host}:{email}"
    attempts = await db.login_attempts.find_one({"identifier": identifier})
    if attempts and attempts.get("count", 0) >= 5:
        locked_until = attempts.get("locked_until")
        if locked_until and datetime.now(timezone.utc) < locked_until:
            raise HTTPException(status_code=429, detail="Account locked. Try again in 15 minutes.")
        else:
            await db.login_attempts.delete_one({"identifier": identifier})

    user = await db.auth_users.find_one({"email": email})
    if not user or not verify_password(req.password, user.get("password_hash", "")):
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$inc": {"count": 1}, "$set": {"locked_until": datetime.now(timezone.utc) + timedelta(minutes=15)}},
            upsert=True
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await db.login_attempts.delete_one({"identifier": identifier})
    access = create_access_token(user["id"], email, user["role"])
    refresh = create_refresh_token(user["id"])
    _set_tokens(response, access, refresh)
    user.pop("_id", None)
    user.pop("password_hash", None)
    return {"user": user, "token": access}

@router.post("/register")
async def register(req: RegisterRequest, response: Response):
    email = req.email.lower()
    existing = await db.auth_users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    import uuid
    user_doc = {
        "id": str(uuid.uuid4()),
        "name": req.name, "email": email,
        "password_hash": hash_password(req.password),
        "role": req.role, "businessId": req.businessId or "default",
        "payRate": req.payRate or 0,
        "status": "active",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.auth_users.insert_one(user_doc)
    user_doc.pop("_id", None)
    user_doc.pop("password_hash", None)
    access = create_access_token(user_doc["id"], email, user_doc["role"])
    refresh = create_refresh_token(user_doc["id"])
    _set_tokens(response, access, refresh)
    return {"user": user_doc, "token": access}

@router.get("/me")
async def me(request: Request):
    user = await get_current_user(request)
    # Custom permissions override default role permissions
    custom = user.get("customPermissions", [])
    if custom:
        user["permissions"] = custom
    else:
        user["permissions"] = ROLE_PERMISSIONS.get(user["role"], [])
    return user

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}

@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.auth_users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(user["id"], user["email"], user["role"])
        response.set_cookie("access_token", access, httponly=True, secure=False, samesite="lax", max_age=28800, path="/")
        return {"message": "Token refreshed"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# --- Staff Management (Owner only) ---
@router.get("/staff")
async def get_staff(request: Request):
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    staff = await db.auth_users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    if user["role"] == "manager":
        for s in staff:
            s.pop("payRate", None)
    return staff

@router.put("/staff/{staff_id}")
async def update_staff(staff_id: str, data: dict, request: Request):
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    allowed = {"name", "role", "status", "payRate", "businessId"}
    update_data = {k: v for k, v in data.items() if k in allowed}
    result = await db.auth_users.find_one_and_update(
        {"id": staff_id}, {"$set": update_data}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Staff not found")
    result.pop("_id", None)
    result.pop("password_hash", None)
    return result

@router.delete("/staff/{staff_id}")
async def delete_staff(staff_id: str, request: Request):
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    if staff_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    await db.auth_users.delete_one({"id": staff_id})
    return {"message": "Staff deleted"}

# --- Owner-Only Reports ---
@router.get("/reports/labor-cost")
async def get_labor_cost_report(request: Request):
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    staff = await db.auth_users.find({"role": {"$ne": "owner"}}, {"_id": 0}).to_list(1000)
    txns = await db.transactions.find({}, {"_id": 0}).to_list(10000)
    total_revenue = sum(t.get("total", 0) for t in txns)
    expenses = await db.expenses.find({}, {"_id": 0}).to_list(10000)
    total_expenses = sum(e.get("amount", 0) for e in expenses)
    total_cogs = sum(e.get("amount", 0) for e in expenses if e.get("category") in ("Ingredients", "Food Supplies", "Beverages"))
    roster_cost = sum(s.get("payRate", 0) * 38 for s in staff)  # 38 hrs/week estimate
    return {
        "staff": [{"name": s["name"], "role": s["role"], "payRate": s.get("payRate", 0), "weeklyEstimate": s.get("payRate", 0) * 38} for s in staff],
        "totalRosterCost": round(roster_cost, 2),
        "totalRevenue": round(total_revenue, 2),
        "cogs": round(total_cogs, 2),
        "otherExpenses": round(total_expenses - total_cogs, 2),
        "grossProfit": round(total_revenue - total_cogs, 2),
        "netProfit": round(total_revenue - total_cogs - (total_expenses - total_cogs) - roster_cost, 2),
        "laborPct": round((roster_cost / max(total_revenue, 1)) * 100, 1),
        "cogsPct": round((total_cogs / max(total_revenue, 1)) * 100, 1),
    }

# --- Seeding ---
async def seed_admin():
    email = os.environ.get("ADMIN_EMAIL", "owner@nuva.com")
    password = os.environ.get("ADMIN_PASSWORD", "NuvaOwner2026!")
    existing = await db.auth_users.find_one({"email": email})
    if not existing:
        import uuid
        await db.auth_users.insert_one({
            "id": str(uuid.uuid4()), "name": "Owner", "email": email,
            "password_hash": hash_password(password),
            "role": "owner", "businessId": "default", "payRate": 0,
            "status": "active", "createdAt": datetime.now(timezone.utc).isoformat(),
        })
    elif not verify_password(password, existing.get("password_hash", "")):
        await db.auth_users.update_one({"email": email}, {"$set": {"password_hash": hash_password(password)}})
    # Seed demo staff
    demo_staff = [
        {"name": "Sarah Manager", "email": "manager@nuva.com", "role": "manager", "payRate": 35},
        {"name": "Tom Cashier", "email": "cashier@nuva.com", "role": "cashier", "payRate": 25},
        {"name": "Chef Kim", "email": "kitchen@nuva.com", "role": "kitchen", "payRate": 30},
    ]
    for s in demo_staff:
        exists = await db.auth_users.find_one({"email": s["email"]})
        if not exists:
            import uuid
            await db.auth_users.insert_one({
                "id": str(uuid.uuid4()), "name": s["name"], "email": s["email"],
                "password_hash": hash_password("Staff2026!"),
                "role": s["role"], "businessId": "default", "payRate": s["payRate"],
                "status": "active", "createdAt": datetime.now(timezone.utc).isoformat(),
            })
    await db.auth_users.create_index("email", unique=True)
