from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
import uuid

class Customer(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    phone: str
    membershipTier: str  # Bronze, Silver, Gold, Platinum
    totalSpent: float = 0.0
    visits: int = 0
    joinDate: datetime = Field(default_factory=datetime.utcnow)
    points: int = 0

class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    membershipTier: str = "Bronze"

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    membershipTier: Optional[str] = None
