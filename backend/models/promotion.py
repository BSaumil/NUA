from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid


class Promotion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # bundle | category | mixed
    # Applicability — any combination of these can be set. `products` and
    # `categories` (plural) let the owner mix individual items + whole
    # categories in a single promo. `category` (singular) is kept for
    # backwards compat with existing rows.
    products: Optional[List[str]] = None
    category: Optional[str] = None
    categories: Optional[List[str]] = None
    # Pricing:
    # • pricingMode="percentage" → apply `discount` (%) to matching items.
    # • pricingMode="fixed_price" → the whole bundle costs `bundlePrice` $.
    pricingMode: str = "percentage"          # percentage | fixed_price
    discount: float = 0.0                    # % — used when pricingMode=percentage
    bundlePrice: Optional[float] = None      # $ — used when pricingMode=fixed_price
    originalPrice: Optional[float] = None
    discountedPrice: Optional[float] = None
    # Bundle rules (used when pricingMode=fixed_price + type=bundle):
    minQuantity: Optional[int] = None        # e.g. "any 3 items from list = $25"
    maxQuantity: Optional[int] = None        # cap
    stackable: bool = False                  # allow stacking with other promos
    active: bool = True
    schedule: str = ""
    # Enhanced scheduling
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    activeDays: List[str] = []  # ["Monday","Tuesday",...]
    startTime: Optional[str] = None  # "11:00"
    endTime: Optional[str] = None    # "14:00"
    # Which POS order types this promo is allowed to fire on. Empty list =
    # unrestricted (applies to every order type, including any future ones)
    # — this is what every promo created before this field existed already
    # means, so it stays the default rather than silently narrowing them.
    # A non-empty list is an ALLOW-list, not a block-list: only the order
    # types named here qualify. That's deliberate — it's what lets a Happy
    # Hour promo set to ["dine-in"] correctly exclude takeaway, delivery,
    # and any order type this system doesn't even have yet (e.g. a future
    # "functions" type) without needing to know its name in advance.
    channels: List[str] = []  # subset of ["dine-in", "takeaway"]
    createdAt: datetime = Field(default_factory=datetime.utcnow)


class PromotionCreate(BaseModel):
    name: str
    type: str
    products: Optional[List[str]] = None
    category: Optional[str] = None
    categories: Optional[List[str]] = None
    pricingMode: str = "percentage"
    discount: float = 0.0
    bundlePrice: Optional[float] = None
    originalPrice: Optional[float] = None
    discountedPrice: Optional[float] = None
    minQuantity: Optional[int] = None
    maxQuantity: Optional[int] = None
    stackable: bool = False
    active: bool = True
    schedule: str = ""
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    activeDays: List[str] = []
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    channels: List[str] = []
