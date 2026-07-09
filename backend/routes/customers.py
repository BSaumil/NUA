from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
from database import db
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
