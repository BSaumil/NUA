from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class GiftCard(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    balance: float
    initialValue: float
    customerId: Optional[str] = None
    issuedDate: datetime = Field(default_factory=datetime.utcnow)
    expiryDate: Optional[datetime] = None
    status: str = "active"  # active, redeemed, expired

class GiftCardCreate(BaseModel):
    initialValue: float
    customerId: Optional[str] = None
    expiryDate: Optional[datetime] = None
