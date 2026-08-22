"""Partial payment handling for guest bill-split.

Guests can pay partial amounts and put the remainder on a tab that staff
collects later (cash, tip, or future visit). Tracks partial payments,
remaining balance, and tab status.
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from database import db
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_guest_tab(split_id: str, guest_phone: str, total_amount: float,
                            claimed_lines: Optional[List[str]] = None,
                            slot_index: Optional[int] = None) -> Dict[str, Any]:
    """Create a new guest tab for partial payment."""
    tab_id = f"TAB-{str(uuid.uuid4())[:12].upper()}"

    tab = {
        "id": tab_id,
        "splitId": split_id,
        "guestPhone": guest_phone,
        "totalAmount": round(total_amount, 2),
        "paidAmount": 0.0,
        "remainingBalance": round(total_amount, 2),
        "claimedLines": claimed_lines or [],
        "slotIndex": slot_index,
        "payments": [],  # Track partial payments
        "status": "open",  # open, partial, paid, cancelled
        "createdAt": _now(),
        "expiresAt": None,  # Can set for time-limited tabs
    }

    await db.split_tabs.insert_one(tab)
    tab.pop("_id", None)
    return tab


async def record_partial_payment(tab_id: str, amount: float, method: str = "card",
                                  reference: str = "") -> Dict[str, Any]:
    """Record a partial payment on a tab."""
    tab = await db.split_tabs.find_one({"id": tab_id})
    if not tab:
        return {"error": "Tab not found", "success": False}

    payment = {
        "id": f"PAY-{str(uuid.uuid4())[:12].upper()}",
        "amount": round(amount, 2),
        "method": method,
        "reference": reference,
        "timestamp": _now(),
    }

    new_paid = round((tab.get("paidAmount", 0) or 0) + amount, 2)
    new_balance = round((tab.get("totalAmount", 0) or 0) - new_paid, 2)
    new_status = "paid" if new_balance <= 0 else "partial"

    await db.split_tabs.update_one(
        {"id": tab_id},
        {
            "$push": {"payments": payment},
            "$set": {
                "paidAmount": new_paid,
                "remainingBalance": max(0, new_balance),
                "status": new_status,
                "updatedAt": _now(),
            }
        }
    )

    return {
        "success": True,
        "paymentId": payment["id"],
        "paidAmount": new_paid,
        "remainingBalance": max(0, new_balance),
        "status": new_status,
    }


async def get_guest_tabs(guest_phone: str) -> List[Dict[str, Any]]:
    """Get all open tabs for a guest (by phone)."""
    tabs = await db.split_tabs.find(
        {"guestPhone": guest_phone, "status": {"$in": ["open", "partial"]}},
        {"_id": 0}
    ).to_list(100)
    return tabs


async def close_tab(tab_id: str, force: bool = False) -> Dict[str, Any]:
    """Close a tab (mark as paid or cancelled)."""
    tab = await db.split_tabs.find_one({"id": tab_id})
    if not tab:
        return {"error": "Tab not found", "success": False}

    remaining = tab.get("remainingBalance", 0) or 0
    if remaining > 0 and not force:
        return {
            "error": f"Tab has ${remaining:.2f} remaining balance",
            "success": False,
            "remainingBalance": remaining,
        }

    status = "cancelled" if force else "paid"
    await db.split_tabs.update_one(
        {"id": tab_id},
        {"$set": {"status": status, "closedAt": _now()}}
    )

    return {"success": True, "status": status, "tabId": tab_id}


async def staff_process_tab_payment(tab_id: str, amount: float, method: str = "cash") -> Dict[str, Any]:
    """Staff processes remaining tab balance (e.g., cash payment at end of meal)."""
    tab = await db.split_tabs.find_one({"id": tab_id})
    if not tab:
        return {"error": "Tab not found", "success": False}

    remaining = tab.get("remainingBalance", 0) or 0
    if remaining <= 0:
        return {"error": "Tab already paid", "success": False}

    # Record the payment
    return await record_partial_payment(tab_id, min(amount, remaining), method, "staff_collected")
