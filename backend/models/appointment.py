from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class AppointmentCreate(BaseModel):
    customerName: str
    customerPhone: Optional[str] = None
    customerId: Optional[str] = None
    staffId: str
    serviceId: str
    date: str    # YYYY-MM-DD
    time: str    # HH:MM
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    customerName: Optional[str] = None
    customerPhone: Optional[str] = None
    customerId: Optional[str] = None
    staffId: Optional[str] = None
    serviceId: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: f"APT-{str(uuid.uuid4())[:8].upper()}")
    customerName: str
    customerPhone: Optional[str] = None
    customerId: Optional[str] = None
    staffId: str
    staffName: str = ""
    serviceId: str
    serviceName: str = ""
    date: str = ""
    time: str = ""
    # Snapshotted from the service at booking time — same reasoning as the
    # bill-split feature's line pricing this session: if the service's
    # price/duration changes later, an appointment already booked shouldn't
    # silently reprice or resize itself.
    durationMinutes: int = 30
    price: float = 0.0
    status: str = "confirmed"  # confirmed, completed, cancelled, no_show
    notes: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    businessId: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        now = datetime.utcnow().isoformat()
        if not self.createdAt:
            self.createdAt = now
        if not self.updatedAt:
            self.updatedAt = now
