"""Shared now()/iso()/uid() helpers.

Six route files each independently defined their own near-identical
_now()/_iso()/_uid() trio (commerce_v29, inventory_accounting, licensing,
online_orders, v25_suite, v26_commerce) — this consolidates the four that
were byte-for-byte identical in behavior: commerce_v29.py, inventory_
accounting.py, online_orders.py, v26_commerce.py.

licensing.py's _uid used 10 hex chars instead of 8 (deliberately more
entropy for billing-related identifiers) and v25_suite.py's _now()
returned an ISO string rather than a datetime (a different contract every
call site there already relies on) — both were left as-is rather than
folded in here, since normalizing either would be a real behavior change,
not a mechanical dedup.
"""
from datetime import datetime, timezone
import uuid


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt) -> str:
    return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


def gen_uid(prefix: str, hex_len: int = 8) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:hex_len].upper()}"
