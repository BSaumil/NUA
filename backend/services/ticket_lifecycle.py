"""What happens to a table's kitchen ticket and floor-plan state when the
bill is paid.

Occupying a table and opening a ticket were both wired up; nothing closed
either. Over a service the floor plan filled and never drained, and a paid
table kept a live ticket — so the next party's first order would silently
join the previous party's bill.

Everything here is best-effort and idempotent: a payment has already been
taken by the time it runs, so a failure to tidy up must never surface as a
failed sale, and a retry must not double-apply.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import db

log = logging.getLogger(__name__)

# A ticket in any of these is still the kitchen's problem.
OPEN_STATUSES = ["new", "preparing", "ready"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def close_tickets(table_number: Optional[str] = None,
                        transaction_id: Optional[str] = None,
                        order_id: Optional[str] = None,
                        actor: Optional[str] = None) -> List[str]:
    """Close the kitchen tickets a completed payment covers.

    Every course is marked served as well as the ticket — a ticket closed
    with courses still showing "fired" reads on the KDS as food nobody
    collected.
    """
    query: Dict[str, Any] = {"status": {"$in": OPEN_STATUSES}}
    if order_id:
        query = {"id": order_id}
    elif transaction_id:
        query["transactionId"] = transaction_id
    elif table_number:
        query["tableNumber"] = table_number
    else:
        return []

    closed: List[str] = []
    now = _now()
    for order in await db.kitchen_orders.find(query, {"_id": 0}).to_list(50):
        courses = dict(order.get("courses") or {})
        for key, state in courses.items():
            if state.get("status") != "served":
                courses[key] = {**state, "status": "served",
                                "servedAt": state.get("servedAt") or now}
        await db.kitchen_orders.update_one(
            {"id": order["id"]},
            {"$set": {"status": "served", "servedAt": now, "courses": courses,
                      "closedBy": actor, "closedReason": "paid"}},
        )
        closed.append(order["id"])
    return closed


async def free_table(table_number: Optional[str], actor: Optional[str] = None) -> bool:
    """Release the table on the floor plan and clear its pacing state."""
    if not table_number:
        return False
    try:
        from services import floor_tables
        hit = await floor_tables.resolve_table(table_number)
        if not hit:
            return False
        table, plan_id = hit
        await floor_tables.set_table_status(table["id"], plan_id, "available")
        # Pacing state is what drives the dwell timers; leaving it behind
        # would show the next party as having been seated since lunch.
        await db.table_states.delete_one({"tableId": table["id"]})
        return True
    except Exception as e:
        log.warning("close: could not free table %r: %s", table_number, e)
        return False


async def settle(table_number: Optional[str] = None,
                 transaction_id: Optional[str] = None,
                 order_id: Optional[str] = None,
                 actor: Optional[str] = None,
                 release_table: bool = True) -> Dict[str, Any]:
    """Close tickets and (for dine-in) hand the table back."""
    closed = await close_tickets(table_number=table_number,
                                 transaction_id=transaction_id,
                                 order_id=order_id, actor=actor)
    freed = await free_table(table_number, actor) if release_table else False
    return {"closedOrders": closed, "tableFreed": freed, "tableNumber": table_number}


async def void_items(order_id: str, voids: List[dict], actor: Optional[str] = None) -> Dict[str, Any]:
    """Remove or reduce items on a live ticket.

    `voids` is [{productId|productName, quantity, course?, seat?}] — quantity
    is how many to take *off*. Anything already cooking still has to be told;
    silently dropping it from the POS leaves the kitchen plating a dish nobody
    is paying for.

    Returns the items actually removed, so the caller can print a void docket
    for the stations that were cooking them.
    """
    order = await db.kitchen_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        return {"ok": False, "removed": [], "reason": "not found"}

    items = [dict(i) for i in (order.get("items") or [])]
    removed: List[dict] = []

    for v in voids or []:
        want = int(v.get("quantity") or 0)
        if want <= 0:
            continue
        for it in items:
            if want <= 0:
                break
            same = (
                (v.get("productId") and it.get("productId") == v.get("productId"))
                or (v.get("productName") and it.get("productName") == v.get("productName"))
            )
            if not same:
                continue
            if v.get("course") is not None and int(it.get("course") or 1) != int(v["course"]):
                continue
            if v.get("seat") is not None and it.get("seat") != v.get("seat"):
                continue
            take = min(int(it.get("quantity") or 0), want)
            if take <= 0:
                continue
            it["quantity"] = int(it.get("quantity") or 0) - take
            want -= take
            removed.append({**{k: it.get(k) for k in
                               ("productId", "productName", "category", "course", "courseLabel", "seat")},
                            "quantity": take})

    if not removed:
        return {"ok": True, "removed": [], "order": order}

    kept = [i for i in items if int(i.get("quantity") or 0) > 0]
    # A course with nothing left on it shouldn't keep a fire state that
    # implies the kitchen still owes the table something.
    live_courses = {str(int(i.get("course") or 1)) for i in kept}
    courses = {k: v for k, v in (order.get("courses") or {}).items() if k in live_courses}

    voids_log = list(order.get("voids") or [])
    voids_log.append({"at": _now(), "by": actor, "items": removed})

    updated = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {"items": kept, "courses": courses, "voids": voids_log}},
        return_document=True,
    )
    if updated:
        updated.pop("_id", None)
    return {"ok": True, "removed": removed, "order": updated}
