"""Guest-facing bill splitting.

A table's open kitchen order becomes individually claimable "lines" — one
per unit, so "2x Burger" is two separate claimable lines — that any guest
at the table can claim from their own phone and pay for themselves,
instead of the whole table waiting on one card at the counter.

Reuses the table's real, live kitchen order (db.kitchen_orders) as the
source of truth — the exact same collection the kitchen prints from
(services/print_routing.py) and the POS's own coursing UI reads
(routes/coursing.py) — so a guest's bill always matches what's actually
been fired to the kitchen, not a stale snapshot handed to them at the
door.

Payment reuses the existing Stripe/Coinbase checkout + finalize pipeline
end to end (see routes/bill_split.py): each guest's claimed items become
their own real Transaction via the exact pricing/GST/loyalty engine every
other sale in this codebase goes through, tagged with a customerId
resolved from their OTP-verified phone (services/customer_identity) so
their points land on their own account, not the table's.
"""
from __future__ import annotations
from collections import Counter
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid

from database import db

OPEN_ORDER_EXCLUDED_STATUSES = ("served", "cancelled")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _open_kitchen_orders(table_number: str) -> List[dict]:
    return await db.kitchen_orders.find(
        {"tableNumber": str(table_number), "status": {"$nin": list(OPEN_ORDER_EXCLUDED_STATUSES)}},
        {"_id": 0},
    ).to_list(200)


def _price_item(item: dict, products_by_id: Dict[str, dict]) -> float:
    """Server-authoritative price at the moment the split is opened — the
    live product price plus any structured modifier surcharges, same
    inputs create_transaction itself prices from. Free-text
    `modifications` (the QR self-order path) carries no price impact,
    consistent with how table_ordering.py already treats it."""
    product = products_by_id.get(item.get("productId")) or {}
    base = float(product.get("price") or 0)
    mods = item.get("modifiers") or []
    mod_total = sum(float(m.get("price") or 0) for m in mods if isinstance(m, dict))
    return round(base + mod_total, 2)


def _fingerprint(line: dict) -> tuple:
    return (line["productId"], line["productName"], line["unitPrice"])


async def _build_lines(orders: List[dict]) -> List[dict]:
    product_ids = {it.get("productId") for o in orders for it in o.get("items", []) if it.get("productId")}
    products = await db.products.find({"id": {"$in": list(product_ids)}}, {"_id": 0}).to_list(1000)
    products_by_id = {p["id"]: p for p in products}

    lines: List[dict] = []
    n = 0
    for order in orders:
        for item in order.get("items", []):
            unit_price = _price_item(item, products_by_id)
            qty = max(int(item.get("quantity") or 1), 1)
            for _ in range(qty):
                n += 1
                lines.append({
                    "id": f"L{n}", "productId": item.get("productId"),
                    "productName": item.get("productName") or item.get("name") or "Item",
                    "category": item.get("category"), "unitPrice": unit_price,
                    "status": "open", "claimedByPhone": None, "transactionId": None,
                })
    return lines


async def get_or_create_split(table_number: str) -> dict:
    """The one open split session for this table, built from its live
    kitchen orders. Idempotent — scanning the QR twice, or two guests
    opening the link at once, lands on the same session.

    If the kitchen order has grown since the split was opened (another
    round fired), the newly-appeared units are appended as fresh open
    lines; anything already claimed or paid is left exactly as it was —
    a guest who's already paid for their burger never sees it reset.
    """
    orders = await _open_kitchen_orders(table_number)
    if not orders:
        raise ValueError("No open order for this table")
    order_ids = sorted(o["id"] for o in orders)

    existing = await db.bill_splits.find_one({"tableNumber": str(table_number), "status": "open"}, {"_id": 0})
    fresh_lines = await _build_lines(orders)

    if not existing:
        doc = {
            "id": f"SPLIT-{str(uuid.uuid4())[:8].upper()}",
            "tableNumber": str(table_number), "orderIds": order_ids,
            "mode": None, "equalParts": [], "lines": fresh_lines,
            "status": "open", "createdAt": _now(),
        }
        await db.bill_splits.insert_one(dict(doc))
        doc.pop("_id", None)
        return doc

    # Multiset-diff against every unit currently on the table's open
    # order(s), not just a same/different order-id-set check — a new round
    # fired onto an ALREADY-open order (same order id, more items) changes
    # nothing about orderIds but genuinely adds billable units, and that
    # has to be caught here too, not just a brand-new order appearing.
    remaining = Counter(_fingerprint(l) for l in existing["lines"])
    new_lines = []
    for l in fresh_lines:
        fp = _fingerprint(l)
        if remaining.get(fp, 0) > 0:
            remaining[fp] -= 1
            continue
        new_lines.append(l)

    if new_lines or sorted(existing.get("orderIds") or []) != order_ids:
        updated_lines = existing["lines"] + new_lines
        await db.bill_splits.update_one(
            {"id": existing["id"]},
            {"$set": {"orderIds": order_ids, "lines": updated_lines, "updatedAt": _now()}},
        )
        existing["lines"] = updated_lines
        existing["orderIds"] = order_ids
    return existing


async def set_mode(split_id: str, mode: str, equal_count: Optional[int] = None) -> dict:
    """Whoever asks first decides items-vs-equal for the table — it sticks
    (idempotent no-op on a repeat call) so a second guest opening the link
    a moment later sees the same choice instead of resetting it."""
    if mode not in ("items", "equal"):
        raise ValueError("mode must be 'items' or 'equal'")
    split = await db.bill_splits.find_one({"id": split_id}, {"_id": 0})
    if not split:
        raise LookupError("split not found")
    if split.get("mode"):
        return split

    update: Dict[str, Any] = {"mode": mode}
    if mode == "equal":
        n = max(1, min(20, int(equal_count or 2)))
        total = round(sum(l["unitPrice"] for l in split["lines"]), 2)
        share = round(total / n, 2) if n else 0.0
        drift = round(total - share * n, 2)
        update["equalParts"] = [
            {"index": i, "amount": round(share + (drift if i == 0 else 0), 2),
             "status": "open", "claimedByPhone": None, "transactionId": None}
            for i in range(n)
        ]
    updated = await db.bill_splits.find_one_and_update(
        {"id": split_id}, {"$set": update}, return_document=True)
    updated.pop("_id", None)
    return updated


async def claim_lines(split_id: str, phone: str, line_ids: List[str]) -> Dict[str, Any]:
    """Atomically claims each requested line. A line already claimed by
    someone else — the exact multi-guest race this feature has to survive
    — is skipped, not overwritten, and reported back so the guest's
    screen can refresh instead of silently succeeding at claiming
    something someone else already has."""
    claimed, failed = [], []
    for lid in line_ids:
        r = await db.bill_splits.update_one(
            {"id": split_id, "lines": {"$elemMatch": {"id": lid, "status": "open"}}},
            {"$set": {"lines.$.status": "claimed", "lines.$.claimedByPhone": phone}},
        )
        (claimed if r.modified_count else failed).append(lid)
    split = await db.bill_splits.find_one({"id": split_id}, {"_id": 0})
    return {"split": split, "claimed": claimed, "failed": failed}


async def claim_equal_slot(split_id: str, phone: str, index: int) -> Dict[str, Any]:
    r = await db.bill_splits.update_one(
        {"id": split_id, "equalParts": {"$elemMatch": {"index": index, "status": "open"}}},
        {"$set": {"equalParts.$.status": "claimed", "equalParts.$.claimedByPhone": phone}},
    )
    split = await db.bill_splits.find_one({"id": split_id}, {"_id": 0})
    return {"split": split, "claimed": bool(r.modified_count)}


async def release_claim(split_id: str, phone: str, line_ids: Optional[List[str]] = None,
                          slot_index: Optional[int] = None) -> dict:
    for lid in (line_ids or []):
        await db.bill_splits.update_one(
            {"id": split_id, "lines": {"$elemMatch": {"id": lid, "status": "claimed", "claimedByPhone": phone}}},
            {"$set": {"lines.$.status": "open", "lines.$.claimedByPhone": None}},
        )
    if slot_index is not None:
        await db.bill_splits.update_one(
            {"id": split_id, "equalParts": {"$elemMatch": {"index": slot_index, "status": "claimed",
                                                              "claimedByPhone": phone}}},
            {"$set": {"equalParts.$.status": "open", "equalParts.$.claimedByPhone": None}},
        )
    return await db.bill_splits.find_one({"id": split_id}, {"_id": 0})


async def build_guest_sale_payload(split_id: str, phone: str, *, line_ids: Optional[List[str]] = None,
                                     slot_index: Optional[int] = None) -> Dict[str, Any]:
    """What this guest is paying for, priced from the split's own snapshot
    — never re-derived from live product prices at pay-time, so a guest
    who claimed at a given price pays that price even if the menu changes
    in between."""
    split = await db.bill_splits.find_one({"id": split_id}, {"_id": 0})
    if not split:
        raise LookupError("split not found")

    if split.get("mode") == "equal":
        if slot_index is None:
            raise ValueError("slot_index required for an equal split")
        slot = next((p for p in split["equalParts"] if p["index"] == slot_index), None)
        if not slot or slot["status"] != "claimed" or slot["claimedByPhone"] != phone:
            raise PermissionError("This share isn't claimed by you")
        amount = slot["amount"]
        items = [{"productId": "SPLIT-SHARE", "productName": f"Table {split['tableNumber']} — equal share",
                  "quantity": 1, "price": amount, "modifiers": []}]
        return {"amount": amount, "items": items, "splitLineIds": [], "splitSlotIndex": slot_index}

    lines = [l for l in split["lines"] if l["id"] in (line_ids or [])]
    if not lines:
        raise ValueError("No claimed lines to pay for")
    for l in lines:
        if l["status"] != "claimed" or l["claimedByPhone"] != phone:
            raise PermissionError(f"Line {l['id']} isn't claimed by you")
    amount = round(sum(l["unitPrice"] for l in lines), 2)
    items = [{"productId": l["productId"], "productName": l["productName"], "quantity": 1,
              "price": l["unitPrice"], "modifiers": []} for l in lines]
    return {"amount": amount, "items": items, "splitLineIds": [l["id"] for l in lines], "splitSlotIndex": None}


async def mark_lines_paid(split_id: str, line_ids: Optional[List[str]], slot_index: Optional[int],
                            transaction_id: str) -> None:
    """Called from routes/integrations.py's _finalize_pos_sale_if_applicable
    once a guest's payment actually lands as a real Transaction — this is
    bookkeeping on top of money that's already moved, so it deliberately
    never raises into that path; a failure here means the split UI shows
    stale status, not that the sale itself is at risk."""
    for lid in (line_ids or []):
        await db.bill_splits.update_one(
            {"id": split_id, "lines.id": lid},
            {"$set": {"lines.$.status": "paid", "lines.$.transactionId": transaction_id}},
        )
    if slot_index is not None:
        await db.bill_splits.update_one(
            {"id": split_id, "equalParts.index": slot_index},
            {"$set": {"equalParts.$.status": "paid", "equalParts.$.transactionId": transaction_id}},
        )

    split = await db.bill_splits.find_one({"id": split_id}, {"_id": 0})
    if not split:
        return
    if split.get("mode") == "equal":
        fully_paid = bool(split.get("equalParts")) and all(p["status"] == "paid" for p in split["equalParts"])
    else:
        fully_paid = bool(split["lines"]) and all(l["status"] == "paid" for l in split["lines"])
    if fully_paid and split["status"] != "settled":
        await db.bill_splits.update_one({"id": split_id}, {"$set": {"status": "settled", "settledAt": _now()}})
