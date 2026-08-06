"""
Universal Voucher — every promotion, gift, refund, referral, birthday reward,
staff/corporate/event issue becomes a voucher with a globally unique code,
signed validation token, redemption rules, and complete audit trail.

Design notes
────────────
• `code` — human-readable alphanumeric (e.g. NUA-FAM-4XK9)
• `qrPayload` — HMAC-signed compact JSON, embedded in the QR image
• `sourceType` — where it came from (promotion, refund, gift_card, referral,
  birthday, anniversary, staff, corporate, event, manual)
• `usageType` — one_time | multi_use | unlimited
• `maxRedemptions` — hard limit (`None` = unlimited)
• `redemptions` — full audit log of every scan (staff, terminal, ts, amount)
• `rules` — eligibility filters: date/time window, weekdays, first_visit_only,
  club_only, min_spend, items/categories, locations, delivery_channel, etc.
• `partialRedeemable` — voucher retains residual value on each redemption
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class VoucherRedemption(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    amount: float                           # dollar value applied
    staffId: Optional[str] = None
    staffName: Optional[str] = None
    terminalId: Optional[str] = None
    transactionId: Optional[str] = None
    locationId: Optional[str] = None
    note: Optional[str] = None


class VoucherRules(BaseModel):
    # Time window
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    activeDays: List[str] = []              # ["Monday","Tuesday",…]
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    happyHourOnly: bool = False
    # Customer / segmentation
    firstVisitOnly: bool = False
    clubMembersOnly: bool = False
    minMembershipTier: Optional[str] = None
    # Spend / cart
    minSpend: Optional[float] = None
    maxDiscount: Optional[float] = None
    eligibleItems: List[str] = []
    eligibleCategories: List[str] = []
    excludeItems: List[str] = []
    excludeCategories: List[str] = []
    # Where
    locationIds: List[str] = []             # empty = all locations
    deliveryChannels: List[str] = []        # ["dine_in","delivery","pickup"] — empty = all
    seatingAreas: List[str] = []
    # Booking source
    bookingSources: List[str] = []


class Voucher(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    qrPayload: str                          # HMAC-signed token — what the QR encodes
    sourceType: str = "manual"              # promotion|refund|gift_card|referral|birthday|anniversary|staff|corporate|event|manual
    sourceRef: Optional[str] = None         # e.g. promotionId, refundId, transactionId
    label: str
    description: Optional[str] = None
    # Value
    valueType: str = "amount"               # amount | percentage | free_item | tier_upgrade
    value: float = 0.0                      # $ or %
    faceValue: float = 0.0                  # original issued value (for accounting)
    residualValue: float = 0.0              # remaining $ (only for partialRedeemable)
    freeItemId: Optional[str] = None        # for valueType=free_item
    # Usage
    usageType: str = "one_time"             # one_time | multi_use | unlimited
    maxRedemptions: Optional[int] = 1
    redemptionCount: int = 0
    partialRedeemable: bool = False
    # Assignment
    customerId: Optional[str] = None
    customerEmail: Optional[str] = None
    customerName: Optional[str] = None
    assignable: bool = True
    # Tenant — which business issued this voucher, from the issuing staff
    # member's own token (see middleware/actor_context.py). Optional/nullable
    # for now: stamped on new vouchers going forward, not backfilled onto
    # existing ones, so no read-side filtering depends on it yet.
    businessId: Optional[str] = None
    # Rules
    rules: VoucherRules = Field(default_factory=VoucherRules)
    # Lifecycle
    status: str = "active"                  # active | redeemed | partial | expired | revoked
    issuedAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    issuedBy: Optional[str] = None
    expiresAt: Optional[str] = None
    revokedAt: Optional[str] = None
    revokedBy: Optional[str] = None
    revokeReason: Optional[str] = None
    # Audit
    redemptions: List[VoucherRedemption] = []
    metadata: Dict[str, Any] = {}


class VoucherCreate(BaseModel):
    label: str
    valueType: str = "amount"
    value: float = 0.0
    sourceType: str = "manual"
    sourceRef: Optional[str] = None
    description: Optional[str] = None
    usageType: str = "one_time"
    maxRedemptions: Optional[int] = 1
    partialRedeemable: bool = False
    customerId: Optional[str] = None
    expiresAt: Optional[str] = None
    freeItemId: Optional[str] = None
    rules: Optional[VoucherRules] = None
    metadata: Optional[Dict[str, Any]] = None


class VoucherRedeemRequest(BaseModel):
    code: Optional[str] = None              # manual entry
    token: Optional[str] = None             # scanned QR
    amount: float                            # $ requested against the voucher
    transactionId: Optional[str] = None
    terminalId: Optional[str] = None
    locationId: Optional[str] = None
    cart: Optional[List[Dict[str, Any]]] = None
    note: Optional[str] = None


class VoucherValidateRequest(BaseModel):
    code: Optional[str] = None
    token: Optional[str] = None
    cart: Optional[List[Dict[str, Any]]] = None
    customerId: Optional[str] = None
    locationId: Optional[str] = None
    channel: Optional[str] = None
