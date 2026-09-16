from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from database import db
from deps import get_user, require_owner_or_manager
from middleware.actor_context import tenant_scope_filter, tenant_owns
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
async def get_customers(search: Optional[str] = None, user: dict = Depends(get_user)):
    clauses = [tenant_scope_filter(user.get("businessId"))]
    if search:
        clauses.append({"$or": [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]})
    clauses = [c for c in clauses if c]  # tenant_scope_filter can return {} (no-op)
    query = {"$and": clauses} if len(clauses) > 1 else (clauses[0] if clauses else {})
    customers = await db.customers.find(query, {"_id": 0}).to_list(1000)
    return safe_parse_list(customers, Customer, fallback=_customer_fallback, where="customers")

@router.post("/customers", response_model=Customer)
async def create_customer(customer: CustomerCreate, _: dict = Depends(get_user)):
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
async def update_customer(customer_id: str, customer_update: CustomerUpdate, user: dict = Depends(get_user)):
    existing = await db.customers.find_one({"id": customer_id}, {"_id": 0, "businessId": 1})
    # NOT tenant_owns_strict — models/customer.py's Customer model has no
    # businessId field at all; it's stamped externally, inconsistently,
    # at ~15+ different creation call sites and test fixtures across this
    # codebase (confirmed via the full test suite: converting this site
    # broke test_loyalty_v2_points_field.py/test_voice_calls.py, both of
    # which seed a customer via the bare Customer(...).dict() shape with
    # no businessId). Auditing and fixing every customer-creation site
    # plus every test fixture that relies on this is a larger, separate
    # effort — not attempted this pass.
    if not existing or not tenant_owns(existing.get("businessId"), user.get("businessId")):
        raise HTTPException(status_code=404, detail="Customer not found")
    from services.entity_service import stamped_update
    update_data = {k: v for k, v in customer_update.dict().items() if v is not None}
    result = await stamped_update("customers", customer_id, update_data, entity_type="customer")
    if not result:
        raise HTTPException(status_code=404, detail="Customer not found")
    return Customer(**result)

# ============ CUSTOMER PROFILE (360 Guest CRM) ============
@router.get("/customers/{customer_id}/profile")
async def get_customer_profile(customer_id: str, user: dict = Depends(get_user)):
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    # NOT tenant_owns_strict — models/customer.py's Customer model has no
    # businessId field at all; it's stamped externally, inconsistently,
    # at ~15+ different creation call sites and test fixtures across this
    # codebase (confirmed via the full test suite: converting this site
    # broke test_loyalty_v2_points_field.py/test_voice_calls.py, both of
    # which seed a customer via the bare Customer(...).dict() shape with
    # no businessId). Auditing and fixing every customer-creation site
    # plus every test fixture that relies on this is a larger, separate
    # effort — not attempted this pass.
    if not customer or not tenant_owns(customer.get("businessId"), user.get("businessId")):
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
async def get_customer_wallet(customer_id: str, user: dict = Depends(get_user)):
    """Store credit + points + active vouchers + occasion offers in one view.
    Reading the wallet also lazily issues any due occasion vouchers
    (e.g. birthday month), so offers always show up without a cron job."""
    existing = await db.customers.find_one({"id": customer_id}, {"_id": 0, "businessId": 1})
    # NOT tenant_owns_strict — models/customer.py's Customer model has no
    # businessId field at all; it's stamped externally, inconsistently,
    # at ~15+ different creation call sites and test fixtures across this
    # codebase (confirmed via the full test suite: converting this site
    # broke test_loyalty_v2_points_field.py/test_voice_calls.py, both of
    # which seed a customer via the bare Customer(...).dict() shape with
    # no businessId). Auditing and fixing every customer-creation site
    # plus every test fixture that relies on this is a larger, separate
    # effort — not attempted this pass.
    if not existing or not tenant_owns(existing.get("businessId"), user.get("businessId")):
        raise HTTPException(status_code=404, detail="Customer not found")
    from services.wallet_service import get_wallet
    wallet = await get_wallet(customer_id)
    if wallet is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return wallet

# ============ STORE CREDIT (as a POS tender) ============
@router.post("/customers/{customer_id}/store-credit/redeem")
async def redeem_store_credit(customer_id: str, data: dict, user: dict = Depends(get_user)):
    """Atomic balance-checked decrement — used when store credit is applied
    as a payment tender at checkout. Mirrors the gift-card redeem pattern so
    two terminals can't double-spend the same customer's credit."""
    existing = await db.customers.find_one({"id": customer_id}, {"_id": 0, "businessId": 1})
    # NOT tenant_owns_strict — models/customer.py's Customer model has no
    # businessId field at all; it's stamped externally, inconsistently,
    # at ~15+ different creation call sites and test fixtures across this
    # codebase (confirmed via the full test suite: converting this site
    # broke test_loyalty_v2_points_field.py/test_voice_calls.py, both of
    # which seed a customer via the bare Customer(...).dict() shape with
    # no businessId). Auditing and fixing every customer-creation site
    # plus every test fixture that relies on this is a larger, separate
    # effort — not attempted this pass.
    if not existing or not tenant_owns(existing.get("businessId"), user.get("businessId")):
        raise HTTPException(status_code=404, detail="Customer not found")
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
    return await get_offer_settings(_user.get("businessId"))


@router.post("/customers/wallet-offers")
async def save_wallet_offer_settings(data: dict, _user: dict = Depends(require_owner_or_manager)):
    from services.tenant_settings import set_setting
    cfg = {
        "birthdayEnabled": bool(data.get("birthdayEnabled", True)),
        "birthdayAmount": max(float(data.get("birthdayAmount", 10) or 0), 0),
    }
    await set_setting("wallet_offers", cfg, _user.get("businessId"))
    return cfg

# ============ FEEDBACK API ============
@router.get("/feedback", response_model=List[Feedback])
async def get_feedback(customer_id: Optional[str] = None, status: Optional[str] = None, _: dict = Depends(get_user)):
    query = {}
    if customer_id:
        query["customerId"] = customer_id
    if status:
        query["status"] = status
    items = await db.feedback.find(query, {"_id": 0}).sort("createdAt", -1).to_list(1000)
    return [Feedback(**f) for f in items]

@router.post("/feedback", response_model=Feedback)
async def create_feedback(fb: FeedbackCreate, _: dict = Depends(get_user)):
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
async def respond_to_feedback(feedback_id: str, response: str = "", _: dict = Depends(get_user)):
    result = await db.feedback.find_one_and_update(
        {"id": feedback_id},
        {"$set": {"status": "responded", "response": response}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Feedback not found")
    result.pop("_id", None)
    return Feedback(**result)
