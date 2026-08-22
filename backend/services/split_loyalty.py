"""Loyalty points integration for guest bill-split payments.

When a guest pays for their split share, award loyalty points to their
customer record (resolved from OTP-verified phone). Uses the same loyalty
engine as staff-initiated transactions.
"""
from __future__ import annotations
from typing import Optional, Dict, Any
from database import db


async def calculate_loyalty_points(amount: float, category: Optional[str] = None) -> int:
    """
    Calculate loyalty points earned on a guest payment.

    Standard: 1 point per $1 spent
    Premium categories (loyalty, membership): 1.5x multiplier
    """
    base_points = int(amount)  # 1 point per dollar

    if category and category.lower() in ["loyalty", "premium", "membership"]:
        return int(base_points * 1.5)

    return base_points


async def award_loyalty_points(customer_id: str, points: int,
                                transaction_id: str,
                                reason: str = "guest_split_payment") -> Dict[str, Any]:
    """Award loyalty points to a customer account from a guest split payment."""
    if not customer_id or not points or points <= 0:
        return {"awarded": False, "points": 0, "reason": "invalid_input"}

    try:
        # Find or create loyalty account
        loyalty = await db.loyalty_accounts.find_one({"customerId": customer_id})
        if not loyalty:
            loyalty = {
                "id": f"LOY-{customer_id[:8]}",
                "customerId": customer_id,
                "points": 0,
                "tier": "bronze",
                "createdAt": "2026-08-22T00:00:00Z",
            }
            await db.loyalty_accounts.insert_one(loyalty)

        # Award points
        await db.loyalty_accounts.update_one(
            {"customerId": customer_id},
            {"$inc": {"points": points}, "$set": {"updatedAt": "2026-08-22T00:00:00Z"}}
        )

        # Log transaction in loyalty history
        await db.loyalty_transactions.insert_one({
            "id": f"LT-{transaction_id}",
            "customerId": customer_id,
            "transactionId": transaction_id,
            "type": "earn",
            "points": points,
            "reason": reason,
            "balance": (loyalty.get("points", 0) or 0) + points,
            "createdAt": "2026-08-22T00:00:00Z",
        })

        return {
            "awarded": True,
            "points": points,
            "newBalance": (loyalty.get("points", 0) or 0) + points,
            "tier": loyalty.get("tier", "bronze"),
        }
    except Exception as e:
        return {"awarded": False, "error": str(e)}
