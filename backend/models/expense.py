from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class Expense(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str  # rent, utilities, supplies, wages, etc
    amount: float
    description: str
    vendor: Optional[str] = None
    paymentMethod: str
    receiptNumber: Optional[str] = None
    location: str
    date: datetime = Field(default_factory=datetime.utcnow)
    createdBy: str
    businessId: Optional[str] = None

class ExpenseCreate(BaseModel):
    category: str
    amount: float
    description: str
    vendor: Optional[str] = None
    paymentMethod: str
    receiptNumber: Optional[str] = None
    location: str
    createdBy: str
