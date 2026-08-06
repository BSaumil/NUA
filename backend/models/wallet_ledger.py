"""
Unified Wallet Ledger — single source of truth for every value movement
per customer. Loyalty points, store credit, gift card balance, voucher
face value, cashback, referral rewards, refunds — all become signed
ledger entries that sum to the current balance in each "bucket".

Entry schema
────────────
type    — points | store_credit | gift_card | voucher | cashback | referral
sign    — +1 (credit) or -1 (debit)
amount  — value in each bucket's native unit (points, dollars, …)
sourceType / sourceRef — where this came from
metadata — free-form (transactionId, staffId, terminalId, locationId, note, ...)
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class LedgerEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customerId: str
    type: str                               # points | store_credit | gift_card | voucher | cashback | referral
    sign: int = 1                           # +1 credit, -1 debit
    amount: float
    balanceAfter: Optional[float] = None    # snapshot for fast timelines
    sourceType: str                         # transaction | refund | promotion | voucher_redeem | referral | manual | expiry
    sourceRef: Optional[str] = None
    note: Optional[str] = None
    createdAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = {}
    # Optional/nullable, stamped on new entries going forward — see
    # models/voucher.py's businessId field for the same rationale.
    businessId: Optional[str] = None


class LedgerEntryCreate(BaseModel):
    customerId: str
    type: str
    sign: int = 1
    amount: float
    sourceType: str = "manual"
    sourceRef: Optional[str] = None
    note: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
