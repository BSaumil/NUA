from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
from database import db
from models.loyalty import LoyaltyReward, LoyaltyRedemption, Event, EventCreate
import uuid

router = APIRouter()

# ============ LOYALTY PROGRAM API ============
@router.get("/loyalty/rewards")
async def get_loyalty_rewards():
    rewards = await db.loyalty_rewards.find({}, {"_id": 0}).to_list(100)
    return rewards

@router.post("/loyalty/rewards")
async def create_loyalty_reward(reward: dict):
    reward_id = f"REWARD-{str(uuid.uuid4())[:8].upper()}"
    reward_doc = {"id": reward_id, **{k: v for k, v in reward.items() if k != "id"}, "createdAt": datetime.utcnow().isoformat()}
    await db.loyalty_rewards.insert_one(reward_doc)
    reward_doc.pop("_id", None)
    return reward_doc

@router.delete("/loyalty/rewards/{reward_id}")
async def delete_loyalty_reward(reward_id: str):
    await db.loyalty_rewards.delete_one({"id": reward_id})
    return {"message": "Reward deleted"}

@router.post("/loyalty/redeem")
async def redeem_loyalty_reward(customer_id: str, reward_id: str):
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    reward = await db.loyalty_rewards.find_one({"id": reward_id}, {"_id": 0})
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found")
    points_cost = reward.get("pointsCost", 0)
    if customer.get("points", 0) < points_cost:
        raise HTTPException(status_code=400, detail="Insufficient points")
    await db.customers.update_one({"id": customer_id}, {"$inc": {"points": -points_cost}})
    redemption = {
        "id": f"REDEEM-{str(uuid.uuid4())[:8].upper()}", "customerId": customer_id,
        "rewardId": reward_id, "rewardName": reward.get("name", ""), "pointsSpent": points_cost,
        "redeemedAt": datetime.utcnow().isoformat(),
    }
    await db.loyalty_redemptions.insert_one(redemption)
    redemption.pop("_id", None)
    return redemption

@router.get("/loyalty/tiers")
async def get_loyalty_tiers():
    return [
        {"name": "Bronze", "minPoints": 0, "multiplier": 1.0, "perks": ["1x points earning", "Birthday reward"]},
        {"name": "Silver", "minPoints": 500, "multiplier": 1.25, "perks": ["1.25x points", "3% discount", "Priority waitlist"]},
        {"name": "Gold", "minPoints": 2000, "multiplier": 1.5, "perks": ["1.5x points", "Free dessert monthly", "VIP section access", "Early event booking"]},
        {"name": "Platinum", "minPoints": 5000, "multiplier": 2.0, "perks": ["2x points", "10% discount", "Personal host", "Chef's table access", "Complimentary valet"]},
    ]

# ============ EVENTS & EXPERIENCES API ============
@router.get("/events")
async def get_events(active_only: bool = True):
    query = {"isActive": True} if active_only else {}
    events = await db.events.find(query, {"_id": 0}).to_list(100)
    return events

@router.post("/events")
async def create_event(event: EventCreate):
    event_obj = Event(**event.dict())
    await db.events.insert_one(event_obj.dict())
    return event_obj.dict()

@router.put("/events/{event_id}")
async def update_event(event_id: str, update: dict):
    update_data = {k: v for k, v in update.items() if k != "id"}
    result = await db.events.find_one_and_update(
        {"id": event_id}, {"$set": update_data}, return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    result.pop("_id", None)
    return result

@router.post("/events/{event_id}/book")
async def book_event_ticket(event_id: str, customer_id: Optional[str] = None, quantity: int = 1):
    result = await db.events.find_one_and_update(
        {"id": event_id},
        {"$inc": {"ticketsBooked": quantity}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Event not found")
    result.pop("_id", None)
    return {"message": f"{quantity} ticket(s) booked", "event": result}

# ============ QR MENU GENERATOR API ============
@router.get("/menu/qr-data")
async def get_qr_menu_data():
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    categories = {}
    for p in products:
        cat = p.get("category", "Other")
        if cat not in categories:
            categories[cat] = {"name": cat, "items": []}
        categories[cat]["items"].append({
            "name": p["name"], "price": p.get("price", 0),
            "description": p.get("description", ""),
            "dietary": p.get("dietary", []),
            "allergens": p.get("allergens", []),
            "available": p.get("stock", 0) > 0,
        })
    return {"categories": list(categories.values()), "restaurantName": "Ananta", "lastUpdated": datetime.utcnow().isoformat()}
