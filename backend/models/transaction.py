from pydantic import BaseModel, Field
from typing import List, Optional, Any
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

class AppliedDiscount(BaseModel):
    """A voucher/promotion discount applied at the POS, in dollars."""
    label: str = ""
    amount: float = 0.0
    promotionId: Optional[str] = None
    voucherId: Optional[str] = None
    code: Optional[str] = None

class PaymentSplit(BaseModel):
    method: str  # card, cash, gift_card, store_credit
    amount: float
    reference: Optional[str] = None  # gift card code, transaction ref

class SplitDetailItem(BaseModel):
    name: str
    quantity: int = 1

class SplitDetail(BaseModel):
    """One guest's share of a split-payment sale — who paid, how much, by
    what method, and (for a 'by item'/'by seat' split) which items were
    actually theirs, so a receipt can be itemized per guest instead of just
    showing one undifferentiated bill.

    customerId/pointsRedeemed let EACH guest redeem against their OWN
    loyalty balance rather than only the one customer attached to the whole
    sale — a split used to only ever earn/redeem against transaction-level
    customerId, so guests other than whoever the cashier had selected got no
    loyalty benefit (or cost) from their own payment at all."""
    payerName: str
    amount: float
    method: str
    items: List[SplitDetailItem] = []
    customerId: Optional[str] = None
    pointsRedeemed: int = 0

class Transaction(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    items: List[TransactionItem]
    subtotal: float
    discount: Any = None
    discountAmount: float = 0.0
    appliedDiscounts: List[AppliedDiscount] = []
    pointsRedeemed: int = 0
    pointsDiscount: float = 0.0
    tipAmount: float = 0.0
    surchargeAmount: float = 0.0
    surchargePercent: float = 0.0
    surchargeReason: Optional[str] = None
    gratuityAmount: float = 0.0
    gratuityPercent: float = 0.0
    gratuityLabel: Optional[str] = None
    covers: Optional[int] = None
    gst: float
    total: float
    paymentMethod: str
    paymentSplits: List[PaymentSplit] = []
    isSplitPayment: bool = False
    splitDetails: List[SplitDetail] = []
    customerId: Optional[str] = None
    customerName: Optional[str] = None
    location: str
    cashier: str
    status: str = "completed"
    receiptNumber: Optional[str] = None
    printed: bool = False
    emailReceipt: Optional[str] = None
    smsReceipt: Optional[str] = None
    tableNumber: Optional[str] = None
    orderType: str = "retail"
    businessId: Optional[str] = None

class TransactionCreate(BaseModel):
    items: List[TransactionItem]
    paymentMethod: str
    paymentSplits: List[PaymentSplit] = []
    isSplitPayment: bool = False
    splitDetails: List[SplitDetail] = []
    tipAmount: float = 0.0
    customerId: Optional[str] = None
    location: str
    cashier: str
    discount: Optional[TransactionDiscount] = None
    appliedDiscounts: List[AppliedDiscount] = []
    pointsRedeemed: int = 0
    pointsDiscount: float = 0.0
    covers: Optional[int] = None
    emailReceipt: Optional[str] = None
    smsReceipt: Optional[str] = None
    tableNumber: Optional[str] = None
    orderType: str = "retail"
