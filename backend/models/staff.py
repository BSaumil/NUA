from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class StaffCommission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    userName: str
    period: str  # "2025-01"
    totalSales: float
    commissionRate: float  # percentage
    commissionEarned: float
    status: str = "pending"  # pending, paid
    paidDate: Optional[datetime] = None

class StaffShift(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    userName: str
    location: str
    clockIn: datetime
    clockOut: Optional[datetime] = None
    breakMinutes: int = 0
    totalHours: float = 0.0
    status: str = "active"  # active, completed
