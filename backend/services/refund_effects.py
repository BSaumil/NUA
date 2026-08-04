"""What a refund has to undo outside the ledger.

The money path and the food path were tracked independently: a refund posted
its reversal to the ledger and stopped. The kitchen ticket stayed open, so the
kitchen kept cooking a dish nobody was paying for, and the stock consumed by
the sale was never returned, so inventory drifted a little further from truth
with every refund.

Everything here is best-effort and reported rather than raised: the customer
has already been refunded by the time it runs, so a failure to tidy up must
never turn into a failed refund. What it did — and didn't — comes back to the
caller so it lands on the refund record instead of only in a log.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import db

log = logging.getLogger(__name__)

OPEN_STATUSES = ["new", "preparing", "ready"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _line_key(item: dict) -> str:
    return str(item.get("productId") or item.get("id") or item.get("productName") or item.get("name") or "")


def _refund_scope(original: dict, refund: dict) -> Dict[str, int]:
    """Which items, and how many of each, this refund covers.

    An itemised refund names them. A whole-order refund covers everything. A
    partial-amount refund names nothing, so we deliberately reverse nothing
    rather than guess which dish the money came off — a wrong guess would
    cancel food the table is still eating.
    """
    named = refund.get("items") or []
    if named:
        return {_line_key(i): int(i.get("quantity") or 1) for i in named if _line_key(i)}
    total = float(original.get("total") or 0)
    amount = float(refund.get("amount") or 0)
    if total and abs(amount - total) < 0.01:
        return {_line_key(i): int(i.get("quantity") or 1)
                for i in (original.get("items") or []) if _line_key(i)}
    return {}


async def _restock(scope: Dict[str, int], original: dict, actor: Optional[str]) -> List[dict]:
    """Return refunded quantities to stock."""
    moved = []
    by_key = {_line_key(i): i for i in (original.get("items") or [])}
    for key, qty in scope.items():
        item = by_key.get(key) or {}
        pid = item.get("productId") or item.get("id")
        if not pid or qty <= 0:
            continue
        try:
            r = await db.products.update_one({"id": pid}, {"$inc": {"stock": qty}})
            if r.matched_count:
                moved.append({"productId": pid, "quantity": qty,
                              "name": item.get("productName") or item.get("name")})
        except Exception as e:
            log.warning("refund restock failed for %s: %s", pid, e)
    if moved:
        try:
            await db.stock_movements.insert_one({
                "type": "refund_restock", "at": _now(), "by": actor,
                "transactionId": original.get("id"), "items": moved,
            })
        except Exception:
            pass
    return moved


async def reverse(original: dict, refund: dict, actor: Optional[str] = None) -> Dict[str, Any]:
    """Undo a refunded sale's kitchen and stock effects.

    Returns a record of what happened, including an explicit reason when
    nothing was reversed — "we did nothing" is an answer a manager needs to be
    able to see, not something to infer from silence.
    """
    scope = _refund_scope(original, refund)
    result: Dict[str, Any] = {"at": _now(), "by": actor, "restocked": [],
                              "voidedFrom": [], "closedTickets": [], "reason": None}

    if not scope:
        result["reason"] = ("partial-amount refund with no itemisation — nothing "
                            "reversed, because guessing which dish it came off "
                            "could cancel food the table is still eating")
        return result

    result["restocked"] = await _restock(scope, original, actor)

    # Any still-open kitchen ticket for this sale gets the refunded items taken
    # off it, and closes if nothing is left to cook.
    query = {"status": {"$in": OPEN_STATUSES}}
    txn_id = original.get("id")
    tickets = await db.kitchen_orders.find(
        {**query, "transactionId": txn_id}, {"_id": 0}).to_list(20)
    if not tickets and original.get("tableNumber"):
        tickets = await db.kitchen_orders.find(
            {**query, "tableNumber": original["tableNumber"]}, {"_id": 0}).to_list(20)

    if not tickets:
        result["reason"] = "no open kitchen ticket for this sale — stock returned only"
        return result

    from services import ticket_lifecycle
    for ticket in tickets:
        voids = [{"productId": k if k.startswith(("P-", "PRD")) else None,
                  "productName": next((i.get("productName") or i.get("name")
                                       for i in (original.get("items") or [])
                                       if _line_key(i) == k), k),
                  "quantity": q}
                 for k, q in scope.items() if q > 0]
        try:
            out = await ticket_lifecycle.void_items(ticket["id"], voids, actor=actor)
        except Exception as e:
            log.warning("refund void failed on %s: %s", ticket["id"], e)
            continue
        if out.get("removed"):
            result["voidedFrom"].append({"orderId": ticket["id"],
                                         "removed": out["removed"]})
        remaining = (out.get("order") or {}).get("items") or []
        if not remaining:
            closed = await ticket_lifecycle.close_tickets(order_id=ticket["id"], actor=actor)
            result["closedTickets"].extend(closed)

    if not result["voidedFrom"] and not result["closedTickets"]:
        result["reason"] = "kitchen ticket had nothing matching left to reverse"
    return result
