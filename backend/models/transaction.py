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

class PaymentSplit(BaseModel):
    method: str  # card, cash, gift_card, store_credit
    amount: float
    reference: Optional[str] = None  # gift card code, transaction ref

class Transaction(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    items: List[TransactionItem]
    subtotal: float
    discount: Optional[TransactionDiscount] = None
    discountAmount: float = 0.0
    tipAmount: float = 0.0
    gst: float
    total: float
    paymentMethod: str  # For single payment
    paymentSplits: List[PaymentSplit] = []  # For split payments
    isSplitPayment: bool = False
    customerId: Optional[str] = None
    customerName: Optional[str] = None
    location: str
    cashier: str
    status: str = "completed"
    printed: bool = False
    emailReceipt: Optional[str] = None
    smsReceipt: Optional[str] = None
    tableNumber: Optional[int] = None
    orderType: str = "retail"  # retail, dine_in, takeaway, delivery

class TransactionCreate(BaseModel):
    items: List[TransactionItem]
    paymentMethod: str
    paymentSplits: List[PaymentSplit] = []
    isSplitPayment: bool = False
    tipAmount: float = 0.0
    customerId: Optional[str] = None
    location: str
    cashier: str
    discount: Optional[TransactionDiscount] = None
    emailReceipt: Optional[str] = None
    smsReceipt: Optional[str] = None
    tableNumber: Optional[int] = None
    orderType: str = "retail"
