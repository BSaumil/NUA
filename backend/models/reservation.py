from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import datetime
import uuid


class ReservationCreate(BaseModel):
    guestName: str
    guestPhone: Optional[str] = None
    guestEmail: Optional[str] = None
    customerId: Optional[str] = None
    partySize: int = 2
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    duration: int = 90  # minutes
    tableId: Optional[str] = None
    tableNumber: Optional[str] = None
    floorPlanId: Optional[str] = None
    section: Optional[str] = None
    specialRequests: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []
    depositRequired: float = 0
    depositPaid: bool = False
    serverId: Optional[str] = None
    source: str = "walk_in"  # walk_in, phone, online, app


class ReservationUpdate(BaseModel):
    guestName: Optional[str] = None
    guestPhone: Optional[str] = None
    guestEmail: Optional[str] = None
    customerId: Optional[str] = None
    partySize: Optional[int] = None
    date: Optional[str] = None
    time: Optional[str] = None
    duration: Optional[int] = None
    tableId: Optional[str] = None
    tableNumber: Optional[str] = None
    section: Optional[str] = None
    specialRequests: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    depositRequired: Optional[float] = None
    depositPaid: Optional[bool] = None
    serverId: Optional[str] = None
    noShowFee: Optional[float] = None


class Reservation(BaseModel):
    id: str = ""
    guestName: str
    guestPhone: Optional[str] = None
    guestEmail: Optional[str] = None
    customerId: Optional[str] = None
    partySize: int = 2
    date: str = ""
    time: str = ""
    duration: int = 90
    tableId: Optional[str] = None
    tableNumber: Optional[str] = None
    floorPlanId: Optional[str] = None
    section: Optional[str] = None
    specialRequests: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []
    status: str = "confirmed"  # confirmed, seated, completed, cancelled, no_show
    depositRequired: float = 0
    depositPaid: bool = False
    noShowFee: float = 0
    serverId: Optional[str] = None
    source: str = "walk_in"
    seatedAt: Optional[str] = None
    completedAt: Optional[str] = None
    cancellationReason: Optional[str] = None
    createdAt: str = ""
    updatedAt: str = ""

    @model_validator(mode="before")
    @classmethod
    def _legacy_aliases(cls, data):
        if isinstance(data, dict):
            # Legacy docs may use customerName/customerPhone/phone
            if not data.get("guestName"):
                data["guestName"] = data.get("customerName") or data.get("name") or "Guest"
            if not data.get("guestPhone"):
                data["guestPhone"] = data.get("customerPhone") or data.get("phone")
            if not data.get("guestEmail"):
                data["guestEmail"] = data.get("customerEmail") or data.get("email")
        return data

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = f"RES-{str(uuid.uuid4())[:8].upper()}"
        now = datetime.utcnow().isoformat()
        if not self.createdAt:
            self.createdAt = now
        if not self.updatedAt:
            self.updatedAt = now
