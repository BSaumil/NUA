from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid


class LoyaltyTier(BaseModel):
    name: str  # Bronze, Silver, Gold, Platinum
    minPoints: int
    multiplier: float = 1.0  # points multiplier
    perks: List[str] = []


class LoyaltyReward(BaseModel):
    id: str = ""
    name: str
    description: str = ""
    pointsCost: int = 100
    rewardType: str = "discount"  # discount, free_item, experience
    discountAmount: float = 0
    discountPercent: float = 0
    freeItemId: Optional[str] = None
    isActive: bool = True
    createdAt: str = ""

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = f"RWD-{str(uuid.uuid4())[:8].upper()}"
        if not self.createdAt:
            self.createdAt = datetime.utcnow().isoformat()


class LoyaltyRedemption(BaseModel):
    id: str = ""
    customerId: str
    rewardId: str
    pointsSpent: int
    status: str = "redeemed"  # redeemed, used, expired
    createdAt: str = ""

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = f"RED-{str(uuid.uuid4())[:8].upper()}"
        if not self.createdAt:
            self.createdAt = datetime.utcnow().isoformat()


class EventCreate(BaseModel):
    name: str
    description: str = ""
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    duration: int = 120  # minutes
    capacity: int = 50
    ticketPrice: float = 0
    eventType: str = "dining"  # dining, wine_pairing, cooking_class, live_music, private
    menuId: Optional[str] = None
    imageUrl: Optional[str] = None
    isActive: bool = True


class Event(BaseModel):
    id: str = ""
    name: str
    description: str = ""
    date: str = ""
    time: str = ""
    duration: int = 120
    capacity: int = 50
    ticketsBooked: int = 0
    ticketPrice: float = 0
    eventType: str = "dining"
    menuId: Optional[str] = None
    imageUrl: Optional[str] = None
    isActive: bool = True
    createdAt: str = ""

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = f"EVT-{str(uuid.uuid4())[:8].upper()}"
        if not self.createdAt:
            self.createdAt = datetime.utcnow().isoformat()
