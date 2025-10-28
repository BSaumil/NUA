from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class SelectedModifier(BaseModel):
    modifierId: str
    modifierName: str
    optionId: str
    optionName: str
    price: float

class TransactionItem(BaseModel):
    productId: str
    productName: str
    quantity: int
    price: float
    modifiers: List[SelectedModifier] = []

class TransactionDiscount(BaseModel):
    type: str  # percentage, fixed, custom
    value: float
    reason: Optional[str] = None

class Transaction(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    items: List[TransactionItem]
    subtotal: float
    discount: Optional[TransactionDiscount] = None
    discountAmount: float = 0.0
    gst: float
    total: float
    paymentMethod: str
    customerId: Optional[str] = None
    customerName: Optional[str] = None
    location: str
    cashier: str
    status: str = "completed"
    printed: bool = False

class TransactionCreate(BaseModel):
    items: List[TransactionItem]
    paymentMethod: str
    customerId: Optional[str] = None
    location: str
    cashier: str
    discount: Optional[TransactionDiscount] = None
