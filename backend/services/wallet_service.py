"""
Customer wallet — one place that answers "what value does this customer
hold with the store right now?": store credit, loyalty points, active
vouchers, and auto-issued occasion offers (birthday month, etc.).

Occasion offers are issued lazily whenever a wallet is read (and in bulk
by the loyalty agent tick), deduped per customer per occasion per year.
"""
from datetime import datetime, timezone
from typing import Optional
import calendar
import uuid

from database import db

DEFAULT_OFFERS = {
    "birthdayEnabled": True,
    "birthdayAmount": 10.0,   # $ voucher, valid for the whole birthday month
}


async def get_offer_settings() -> dict:
    s = await db.settings.find_one({"key": "wallet_offers"}, {"_id": 0})
    cfg = dict(DEFAULT_OFFERS)
    if s and isinstance(s.get("value"), dict):
        cfg.update(s["value"])
    return cfg


def _parse_birthday(raw: str):
    """Accept YYYY-MM-DD or MM-DD; return (month, day) or None."""
    if not raw:
        return None
    parts = str(raw).split("-")
    try:
        if len(parts) == 3:
            return int(parts[1]), int(parts[2])
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None
    return None


async def ensure_birthday_voucher(customer: dict, amount: Optional[float] = None) -> Optional[dict]:
    """Issue this year's birthday-month voucher if the customer's birthday
    falls in the current month and they don't have one yet. Idempotent."""
    cfg = await get_offer_settings()
    if not cfg.get("birthdayEnabled", True):
        return None
    bd = _parse_birthday(customer.get("birthday"))
    if not bd:
        return None
    now = datetime.now(timezone.utc)
    if bd[0] != now.month:
        return None
    existing = await db.vouchers.find_one({
        "customerId": customer["id"], "reason": "birthday", "year": now.year,
    })
    if existing:
        return None
    last_day = calendar.monthrange(now.year, now.month)[1]
    expires = datetime(now.year, now.month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    voucher = {
        "id": f"VCH-{str(uuid.uuid4())[:8].upper()}",
        "customerId": customer["id"],
        "amount": float(amount if amount is not None else cfg.get("birthdayAmount", 10.0)),
        "reason": "birthday",
        "occasion": "Birthday Month 🎂",
        "year": now.year,
        "status": "active",
        "createdAt": now.isoformat(),
        "expiresAt": expires.isoformat(),
    }
    await db.vouchers.insert_one(voucher)
    voucher.pop("_id", None)
    return voucher


async def expire_stale_vouchers(customer_id: str):
    """Flip active-but-expired vouchers to 'expired' so wallets stay honest."""
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.vouchers.update_many(
        {"customerId": customer_id, "status": "active", "expiresAt": {"$lt": now_iso}},
        {"$set": {"status": "expired"}},
    )


async def get_wallet(customer_id: str) -> Optional[dict]:
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        return None
    # Lazy occasion issuance + cleanup, then read
    await ensure_birthday_voucher(customer)
    await expire_stale_vouchers(customer_id)
    vouchers = await db.vouchers.find(
        {"customerId": customer_id, "status": "active"}, {"_id": 0}
    ).to_list(100)
    # Two kinds of voucher land in this collection: wallet ones written here
    # (amount/createdAt) and Universal Voucher Engine ones from campaigns,
    # refunds and promotions (value/issuedAt, plus a code + QR). Normalize so
    # the wallet shows one consistent list — before this, engine vouchers
    # displayed as $0 and sorted to the bottom for want of an `amount`.
    for v in vouchers:
        if v.get("amount") is None and v.get("value") is not None:
            v["amount"] = float(v.get("value") or 0)
        v.setdefault("createdAt", v.get("issuedAt"))
    vouchers.sort(key=lambda v: str(v.get("createdAt") or ""), reverse=True)
    # Percentage-off vouchers have no fixed dollar value, so they'd inflate a
    # dollar total — count only the fixed-value ones.
    fixed_value = [v for v in vouchers if v.get("valueType") != "percentage"]
    return {
        "customerId": customer_id,
        "name": customer.get("name"),
        "storeCredit": round(float(customer.get("storeCredit") or 0), 2),
        "points": int(customer.get("points") or 0),
        "membershipTier": customer.get("membershipTier", "Bronze"),
        "vouchers": vouchers,
        "occasionOffers": [v for v in vouchers if v.get("occasion")],
        "totalVoucherValue": round(sum(float(v.get("amount") or 0) for v in fixed_value), 2),
    }


async def redeem_wallet_voucher(voucher_id: str, txn_id: str) -> bool:
    """Mark a wallet voucher used (atomically) when a sale consumes it."""
    res = await db.vouchers.find_one_and_update(
        {"id": voucher_id, "status": "active"},
        {"$set": {"status": "used", "usedAt": datetime.now(timezone.utc).isoformat(), "transactionId": txn_id}},
    )
    return res is not None
