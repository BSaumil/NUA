"""
Measured / Fractional Stock — service layer.

Two responsibilities:
  1. `deduct_on_sale(product_id, quantity, actor)` — called from the sales
     finalisation path. Silently no-ops if the product isn't linked to a
     SellVariant (i.e. it's a plain whole-unit product), so existing sales
     flow is untouched.

  2. `reorder_available(product_id)` — returns the whole-unit-equivalent
     stock count that Insight #11 should use so a bottle mid-pour or a
     keg mid-service isn't invisible to the reorder logic.

Also exposes `apply_wastage_to_container` used by both the manual wastage
endpoint and by the reconcile flow when it needs to log implied shrinkage.

Every write goes through `stamped_update` / `stamped_insert` so version
counters, audit events, and actor/device/ip stamping are automatic.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timezone
from database import db
from services.entity_service import stamped_insert, stamped_update
import logging
import uuid

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Unit conversion ──────────────────────────────────────────────────────
# Built-in conversion table. Owner-configured UomConversion rows override
# this at runtime (checked first). Kept intentionally small — measured
# stock is only for liquid and mass right now; "ea" is opaque.
_BUILTIN_FACTORS = {
    ("l", "ml"): 1000.0,
    ("ml", "l"): 0.001,
    ("kg", "g"): 1000.0,
    ("g", "kg"): 0.001,
}


async def convert(amount: float, from_uom: str, to_uom: str) -> float:
    """Convert `amount` from one UoM to another. Falls through custom
    UomConversion table first, then builtin. Raises ValueError if there's
    no path."""
    if from_uom == to_uom:
        return amount
    key = (from_uom, to_uom)
    custom = await db.uom_conversions.find_one({"fromUom": from_uom, "toUom": to_uom}, {"_id": 0})
    if custom and custom.get("factor"):
        return amount * float(custom["factor"])
    if key in _BUILTIN_FACTORS:
        return amount * _BUILTIN_FACTORS[key]
    raise ValueError(f"No conversion from {from_uom} to {to_uom}")


# ─── Container operations ─────────────────────────────────────────────────
async def _active_container(stock_unit_id: str) -> Optional[Dict[str, Any]]:
    """Return the most recently-opened, not-yet-closed container for a
    stock unit, or None."""
    return await db.open_containers.find_one(
        {"stockUnitId": stock_unit_id, "closedAt": None, "deletedAt": None},
        {"_id": 0},
        sort=[("openedAt", -1)],
    )


async def _auto_open_container(stock_unit_id: str, *, actor: str,
                                 station_id: Optional[str] = None,
                                 initial_remaining: Optional[float] = None) -> Dict[str, Any]:
    """Open a new container for a stock unit — usually invoked when a sale
    lands with none open. Not gated by permissions since the alternative
    is refusing the sale, which we don't want."""
    su = await db.stock_units.find_one({"id": stock_unit_id}, {"_id": 0})
    if not su:
        raise ValueError(f"StockUnit {stock_unit_id} not found")
    remaining = initial_remaining if initial_remaining is not None else float(su["totalMeasure"])
    doc = {
        "id": str(uuid.uuid4()),
        "stockUnitId": stock_unit_id,
        "openedAt": _now(),
        "openedBy": actor,
        "remainingMeasure": remaining,
        "stationId": station_id,
        "closedAt": None,
        "closedBy": None,
    }
    return await stamped_insert("open_containers", doc, entity_type="open_container")


async def open_container(stock_unit_id: str, *, actor: str,
                          station_id: Optional[str] = None) -> Dict[str, Any]:
    return await _auto_open_container(stock_unit_id, actor=actor, station_id=station_id)


async def deduct_on_sale(product_id: str, quantity: float, actor: str) -> Dict[str, Any]:
    """Deduct measured stock for a sale. Called from the transaction
    finalise path alongside the existing whole-unit stock decrement.

    Behaviour
    ─────────
    • If the product has no linked SellVariant → return {'measured': False}
      and the caller keeps using the plain whole-unit `$inc: stock -1` logic.
    • Otherwise find the active OpenContainer for the linked StockUnit,
      auto-open one if there isn't one, decrement remainingMeasure by
      `deductAmount * quantity` (converted if UoMs differ), and roll any
      overdraw onto a freshly-opened container.
    """
    variant = await db.sell_variants.find_one(
        {"productId": product_id, "deletedAt": None}, {"_id": 0},
    )
    if not variant:
        return {"measured": False}

    stock_unit_id = variant["stockUnitId"]
    su = await db.stock_units.find_one({"id": stock_unit_id}, {"_id": 0})
    if not su:
        logger.warning(f"[measured] SellVariant {variant['id']} points at "
                       f"missing StockUnit {stock_unit_id}")
        return {"measured": False, "error": "missing_stock_unit"}

    # Amount to deduct, converted into the StockUnit's own UoM
    raw_deduct = float(variant["deductAmount"]) * float(quantity)
    try:
        deduct = await convert(raw_deduct, variant["uom"], su["uom"])
    except ValueError as e:
        logger.error(f"[measured] {e}")
        return {"measured": False, "error": str(e)}

    container = await _active_container(stock_unit_id)
    auto_opened = False
    if not container:
        container = await _auto_open_container(stock_unit_id, actor=actor)
        auto_opened = True

    remaining = float(container["remainingMeasure"]) - deduct
    events: list = [{"containerId": container["id"], "wasAutoOpened": auto_opened,
                       "deductedFrom": container["remainingMeasure"], "deductedBy": deduct}]

    if remaining >= 0:
        # Simple case — enough in the current container
        await stamped_update("open_containers", container["id"], {
            "remainingMeasure": remaining,
            **({"closedAt": _now(), "closedBy": actor} if remaining == 0 else {}),
        }, entity_type="open_container")
        return {"measured": True, "events": events, "closed": remaining == 0}

    # Overdraw — close current container at 0, open a new one at
    # totalMeasure - overdraw so nothing is lost from the count.
    overdraw = -remaining
    await stamped_update("open_containers", container["id"], {
        "remainingMeasure": 0.0,
        "closedAt": _now(),
        "closedBy": actor,
    }, entity_type="open_container")
    next_container = await _auto_open_container(
        stock_unit_id, actor=actor,
        initial_remaining=float(su["totalMeasure"]) - overdraw,
    )
    events.append({"containerId": next_container["id"], "wasAutoOpened": True,
                    "openedAt": next_container["remainingMeasure"] + overdraw,
                    "rolledOverdrawFromPrev": overdraw})
    return {"measured": True, "events": events, "closed": True, "rolled": True}


# ─── Wastage ──────────────────────────────────────────────────────────────
async def apply_wastage_to_container(open_container_id: str, amount: float,
                                       uom: str, *, actor: str) -> Dict[str, Any]:
    c = await db.open_containers.find_one({"id": open_container_id}, {"_id": 0})
    if not c:
        raise ValueError("open_container not found")
    su = await db.stock_units.find_one({"id": c["stockUnitId"]}, {"_id": 0})
    if not su:
        raise ValueError("stock_unit not found")
    deduct = await convert(float(amount), uom, su["uom"])
    new_remaining = max(0.0, float(c["remainingMeasure"]) - deduct)
    patch = {"remainingMeasure": new_remaining}
    if new_remaining == 0:
        patch.update({"closedAt": _now(), "closedBy": actor})
    return await stamped_update("open_containers", open_container_id, patch,
                                  entity_type="open_container")


# ─── Reorder-point helper for Ash Insight #11 ────────────────────────────
async def reorder_available(product_id: str) -> Dict[str, Any]:
    """Return an equivalent whole-unit stock count for reorder logic.

    equivalent = sealed_units + sum(remainingMeasure / totalMeasure) for
                  all currently-open containers linked via SellVariant.
    """
    variants = await db.sell_variants.find(
        {"productId": product_id, "deletedAt": None}, {"_id": 0},
    ).to_list(20)
    stock_unit_ids = list({v["stockUnitId"] for v in variants})
    if not stock_unit_ids:
        return {"measured": False}
    sealed_units = 0
    partial = 0.0
    for suid in stock_unit_ids:
        su = await db.stock_units.find_one({"id": suid}, {"_id": 0})
        if not su:
            continue
        # We DON'T maintain a sealed count separately yet — an owner is
        # expected to update product.stock as they buy new bottles. That
        # matches how they think about inventory today.
        sealed_units += int((su.get("sealedUnits") or 0))
        cont = await db.open_containers.find_one(
            {"stockUnitId": suid, "closedAt": None, "deletedAt": None},
            {"_id": 0},
        )
        if cont and su.get("totalMeasure"):
            partial += float(cont["remainingMeasure"]) / float(su["totalMeasure"])
    return {
        "measured": True,
        "sealed": sealed_units,
        "partial": round(partial, 3),
        "equivalent": round(sealed_units + partial, 3),
    }


# ─── Reconcile — stocktake counted vs theoretical ─────────────────────────
async def reconcile_stocktake(stock_unit_id: str, counted_remaining: float, uom: str,
                                *, actor: str, threshold_pct: float = 0.05) -> Dict[str, Any]:
    """Compare the counted quantity to what the ledger says should remain
    across all currently-open containers of this stock unit. Positive
    variance beyond the threshold logs a wastage_event with reason=other."""
    su = await db.stock_units.find_one({"id": stock_unit_id}, {"_id": 0})
    if not su:
        raise ValueError("stock_unit not found")
    counted = await convert(float(counted_remaining), uom, su["uom"])

    open_conts = await db.open_containers.find(
        {"stockUnitId": stock_unit_id, "closedAt": None, "deletedAt": None},
        {"_id": 0},
    ).to_list(50)
    theoretical = sum(float(c["remainingMeasure"]) for c in open_conts)
    variance = theoretical - counted             # positive = missing stock
    variance_pct = (variance / theoretical) if theoretical else 0.0
    result = {
        "stockUnitId": stock_unit_id,
        "theoretical": round(theoretical, 3),
        "counted": round(counted, 3),
        "variance": round(variance, 3),
        "variancePct": round(variance_pct, 4),
        "uom": su["uom"],
        "flagged": abs(variance_pct) > threshold_pct,
        "reconciledAt": _now(),
        "reconciledBy": actor,
    }

    if result["flagged"] and variance > 0 and open_conts:
        # Log implied shrinkage against the earliest-open container so it
        # shows up in Insight #6 (waste). Cap the container debit at what
        # it still has to avoid negatives on the ledger.
        c = open_conts[0]
        debit = min(float(c["remainingMeasure"]), variance)
        await stamped_insert("wastage_events", {
            "id": str(uuid.uuid4()),
            "openContainerId": c["id"],
            "stockUnitId": stock_unit_id,
            "amount": debit,
            "uom": su["uom"],
            "reason": "other",
            "loggedBy": actor,
            "note": f"Stocktake variance {variance_pct*100:.1f}% — auto-logged shrinkage",
        }, entity_type="wastage_event")
        if debit > 0:
            await stamped_update("open_containers", c["id"], {
                "remainingMeasure": max(0.0, float(c["remainingMeasure"]) - debit),
            }, entity_type="open_container")

    await stamped_insert("stocktake_reconciles", {
        "id": str(uuid.uuid4()), **result,
    }, entity_type="stocktake_reconcile")
    return result
