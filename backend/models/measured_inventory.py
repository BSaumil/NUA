"""
Measured / Fractional Stock — Phase 1.

Companion to NUA_POS_Master_Roadmap_v1.txt §5 (Universal Entity Model).

Design
──────
Today stock is a scalar `stock` int on each product. That is fine for
products sold in the same unit you buy them in (a bag of coffee beans, a
retail bottle). It falls over the moment a product is *purchased* in one
unit (750ml bottle, 50L keg, 1kg wheel) and *sold* in another (150ml glass,
100g portion). This module adds a measured layer without breaking any
existing product.

Five entities capture the shape:

  UomConversion    factor between units (ml↔l, g↔kg, ea→portion with yield)
  StockUnit        the *bought* container (bottle, keg, wheel)
  SellVariant      the *sold* form (glass, schooner, portion)
  OpenContainer    one running instance of a StockUnit (current bottle in use)
  WastageEvent     one entry in the wastage log

Every model extends BaseEntity so id/business/audit/version stamping
happens the same way as every other kind. Writes route through
stamped_insert / stamped_update — never a bare motor call.
"""
from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel
from datetime import datetime
from .base_entity import BaseEntity


Uom = Literal["ml", "l", "g", "kg", "ea"]


# ─── UomConversion ────────────────────────────────────────────────────────
class UomConversion(BaseEntity):
    """Factor to convert `fromUom` to `toUom`. yieldPct handles waste-in-prep
    (e.g. an "ea" avocado yields ~85% edible flesh)."""
    fromUom: Uom
    toUom: Uom
    factor: float                       # multiply fromUom by this to get toUom
    yieldPct: Optional[float] = None    # 0.0-1.0, for ea→portion with wastage


# ─── StockUnit — a bought container ───────────────────────────────────────
class StockUnit(BaseEntity):
    productId: str                      # FK -> existing product.id
    uom: Uom
    totalMeasure: float                 # e.g. 750 for a 750ml bottle
    costPerUnit: float
    supplierId: Optional[str] = None
    label: Optional[str] = None         # human-readable ("750ml bottle")


class StockUnitCreate(BaseModel):
    productId: str
    uom: Uom
    totalMeasure: float
    costPerUnit: float
    supplierId: Optional[str] = None
    label: Optional[str] = None


# ─── SellVariant — the sold form ──────────────────────────────────────────
class SellVariant(BaseEntity):
    productId: str                      # sellable menu item (e.g. "Glass of Shiraz")
    stockUnitId: str                    # FK -> StockUnit it deducts from
    deductAmount: float                 # e.g. 150
    uom: Uom
    label: Optional[str] = None         # "Glass 150ml"


class SellVariantCreate(BaseModel):
    productId: str
    stockUnitId: str
    deductAmount: float
    uom: Uom
    label: Optional[str] = None


# ─── OpenContainer — running instance ─────────────────────────────────────
class OpenContainer(BaseEntity):
    stockUnitId: str
    openedAt: str
    openedBy: str
    remainingMeasure: float             # decrements on every linked sale
    stationId: Optional[str] = None     # which tap/fridge/pass position
    closedAt: Optional[str] = None
    closedBy: Optional[str] = None


class OpenContainerCreate(BaseModel):
    stockUnitId: str
    stationId: Optional[str] = None


# ─── WastageEvent ─────────────────────────────────────────────────────────
WastageReason = Literal["spillage", "corked", "over_pour", "kicked", "expired", "other"]


class WastageEvent(BaseEntity):
    openContainerId: Optional[str] = None
    stockUnitId: Optional[str] = None
    amount: float
    uom: Uom
    reason: WastageReason
    loggedBy: str
    note: Optional[str] = None


class WastageEventCreate(BaseModel):
    openContainerId: Optional[str] = None
    stockUnitId: Optional[str] = None
    amount: float
    uom: Uom
    reason: WastageReason
    note: Optional[str] = None
