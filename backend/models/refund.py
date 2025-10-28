from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class Refund(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    originalTransactionId: str
    amount: float
    reason: str
    refundMethod: str  # original_payment, store_credit, cash
    processedBy: str
    customerId: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = "completed"

class RefundCreate(BaseModel):
    originalTransactionId: str
    amount: float
    reason: str
    refundMethod: str
    processedBy: str
