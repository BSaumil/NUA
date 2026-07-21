from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from database import db
from deps import get_user, require_owner_or_manager
from models.customer import Customer, CustomerCreate, CustomerUpdate
from models.feedback import Feedback, FeedbackCreate
from utils.mongo_safe import safe_parse_list

router = APIRouter()


def _customer_fallback(c: dict, _err):
    """Legacy rows with invalid email — surface with a placeholder rather than drop."""
    try:
        return Customer(**{**c, "email": "invalid@unknown.local"})
    except Exception:
        return None


# ============ CUSTOMERS API ============
@router.get("/customers")
async def get_customers(search: Optional[str] = None):
    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    customers = await db.customers.find(query, {"_id": 0}).to_list(1000)
    return safe_parse_list(customers, Customer, fallback=_customer_fallback, where="customers")

@router.post("/customers", response_model=Customer)
async def create_customer(customer: CustomerCreate):
    from services.entity_service import stamped_insert
    customer_dict = customer.dict()
    customer_obj = Customer(**customer_dict)
    doc = await stamped_insert("customers", customer_obj.dict(), entity_type="customer")
    # Rules engine emit
    try:
        from services.rules_engine import safe_emit
        safe_emit("customer.created", {"id": doc.get("id"), "name": doc.get("name"), "email": doc.get("email")})
    except Exception:
        pass
    return doc

@router.put("/customers/{customer_id}", response_model=Customer)
async def update_customer(customer_id: str, customer_update: CustomerUpdate):
    from services.entity_service import stamped_update
    update_data = {k: v for k, v in customer_update.dict().items() if v is not None}
    result = await stamped_update("customers", customer_id, update_data, entity_type="customer")
    if not result:
        raise HTTPException(status_code=404, detail="Customer not found")
    return Customer(**result)

# ============ CUSTOMER PROFILE (360 Guest CRM) ============
@router.get("/customers/{customer_id}/profile")
async def get_customer_profile(customer_id: str):
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    reservations = await db.reservations.find(
        {"$or": [{"customerId": customer_id}, {"guestEmail": customer.get("email", "")}]},
        {"_id": 0}
    ).sort("date", -1).to_list(50)
    feedbacks = await db.feedback.find({"customerId": customer_id}, {"_id": 0}).sort("createdAt", -1).to_list(50)
    transactions = await db.transactions.find({"customerId": customer_id}, {"_id": 0}).sort("timestamp", -1).to_list(50)
    return {
        **customer,
        "reservationHistory": reservations,
        "feedbackHistory": feedbacks,
        "transactionHistory": transactions,
    }

# ============ CUSTOMER WALLET ============
@router.get("/customers/{customer_id}/wallet")
async def get_customer_wallet(customer_id: str):
    """Store credit + points + active vouchers + occasion offers in one view.
    Reading the wallet also lazily issues any due occasion vouchers
    (e.g. birthday month), so offers always show up without a cron job."""
    from services.wallet_service import get_wallet
    wallet = await get_wallet(customer_id)
    if wallet is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return wallet

# ============ STORE CREDIT (as a POS tender) ============
@router.post("/customers/{customer_id}/store-credit/redeem")
async def redeem_store_credit(customer_id: str, data: dict, _user: dict = Depends(get_user)):
    """Atomic balance-checked decrement — used when store credit is applied
    as a payment tender at checkout. Mirrors the gift-card redeem pattern so
    two terminals can't double-spend the same customer's credit."""
    amount = round(float(data.get("amount", 0) or 0), 2)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")
    customer = await db.customers.find_one_and_update(
        {"id": customer_id, "storeCredit": {"$gte": amount}},
        {"$inc": {"storeCredit": -amount}},
        return_document=True,
    )
    if not customer:
        exists = await db.customers.find_one({"id": customer_id}, {"_id": 0, "storeCredit": 1})
        if not exists:
            raise HTTPException(status_code=404, detail="Customer not found")
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient store credit (${exists.get('storeCredit', 0):.2f} available)"
        )
    return {"redeemed": amount, "remainingCredit": round(float(customer.get("storeCredit", 0)), 2)}

# ============ WALLET OFFER SETTINGS (Owner/Manager) ============
@router.get("/customers/wallet-offers")
async def get_wallet_offer_settings(_user: dict = Depends(require_owner_or_manager)):
    from services.wallet_service import get_offer_settings
    return await get_offer_settings()


@router.post("/customers/wallet-offers")
async def save_wallet_offer_settings(data: dict, _user: dict = Depends(require_owner_or_manager)):
    cfg = {
        "birthdayEnabled": bool(data.get("birthdayEnabled", True)),
        "birthdayAmount": max(float(data.get("birthdayAmount", 10) or 0), 0),
    }
    await db.settings.update_one(
        {"key": "wallet_offers"}, {"$set": {"key": "wallet_offers", "value": cfg}}, upsert=True
    )
    return cfg

# ============ FEEDBACK API ============
@router.get("/feedback", response_model=List[Feedback])
async def get_feedback(customer_id: Optional[str] = None, status: Optional[str] = None):
    query = {}
    if customer_id:
        query["customerId"] = customer_id
    if status:
        query["status"] = status
    items = await db.feedback.find(query, {"_id": 0}).sort("createdAt", -1).to_list(1000)
    return [Feedback(**f) for f in items]

@router.post("/feedback", response_model=Feedback)
async def create_feedback(fb: FeedbackCreate):
    fb_obj = Feedback(**fb.dict())
    await db.feedback.insert_one(fb_obj.dict())
    if fb.customerId:
        customer = await db.customers.find_one({"id": fb.customerId}, {"_id": 0})
        if customer:
            count = customer.get("feedbackCount", 0)
            avg = customer.get("feedbackRating", 0)
            new_count = count + 1
            new_avg = ((avg * count) + fb.rating) / new_count
            await db.customers.update_one(
                {"id": fb.customerId},
                {"$set": {"feedbackRating": round(new_avg, 1), "feedbackCount": new_count}}
            )
    return fb_obj

@router.put("/feedback/{feedback_id}/respond")
async def respond_to_feedback(feedback_id: str, response: str = ""):
    result = await db.feedback.find_one_and_update(
        {"id": feedback_id},
        {"$set": {"status": "responded", "response": response}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Feedback not found")
    result.pop("_id", None)
    return Feedback(**result)
