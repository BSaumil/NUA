from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, time
import uuid

class EmployeeSchedule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    userName: str
    location: str
    dayOfWeek: int  # 0=Monday, 6=Sunday
    startTime: time
    endTime: time
    role: str
    isRecurring: bool = True
    effectiveDate: datetime
    endDate: Optional[datetime] = None

class EmployeeScheduleCreate(BaseModel):
    userId: str
    location: str
    dayOfWeek: int
    startTime: time
    endTime: time
    role: str
    isRecurring: bool = True
    effectiveDate: datetime
    endDate: Optional[datetime] = None

class TimeOffRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    userId: str
    userName: str
    startDate: datetime
    endDate: datetime
    reason: str
    status: str = "pending"  # pending, approved, denied
    approvedBy: Optional[str] = None
    notes: Optional[str] = None

class AgeVerification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transactionId: str
    productName: str
    customerId: Optional[str] = None
    verifiedBy: str
    verificationType: str  # id_check, birthdate_entry
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    approved: bool
