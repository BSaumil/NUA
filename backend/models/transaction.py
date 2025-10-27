from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class TransactionItem(BaseModel):
    productId: str
    productName: str
    quantity: int
    price: float

class Transaction(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    items: List[TransactionItem]
    subtotal: float
    gst: float
    total: float
    paymentMethod: str
    customerId: Optional[str] = None
    customerName: Optional[str] = None
    location: str
    cashier: str
    status: str = "completed"

class TransactionCreate(BaseModel):
    items: List[TransactionItem]
    paymentMethod: str
    customerId: Optional[str] = None
    location: str
    cashier: str
