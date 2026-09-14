"""Booking 3.0 — cancellation-policy engine.

A configurable per-business cutoff: cancel at least `cutoffHours` before
the reservation's own date/time and any deposit actually collected (see
routes/reservations.py's request_deposit/mark_no_show) is refunded in
full, same as cancellation always behaved before this. Cancel later than
that and the deposit is forfeited as a cancellation fee instead — the
same "keep what was actually collected, never fabricate a charge that
was never collected" mechanism mark_no_show already uses for a genuine
no-show, just triggered by a late cancellation rather than a no-show.

Per-business from day one — unlike loyalty_config (routes/loyalty_engine.py),
a documented, deliberately-not-fixed single global document elsewhere in
this codebase, cancellation_policies is keyed by businessId from the
start so this mistake isn't repeated.
"""
from datetime import datetime, timedelta
from typing import Optional

from database import db
from middleware.actor_context import tenant_scope_filter

DEFAULT_CUTOFF_HOURS = 24.0


async def get_policy(business_id: Optional[str] = None) -> dict:
    """The business's own policy if it's ever set one, else the default —
    seeded lazily on first read/write rather than a migration, same
    pattern as routes/loyalty.py's tier catalog."""
    doc = await db.cancellation_policies.find_one(tenant_scope_filter(business_id), {"_id": 0})
    if doc:
        return doc
    return {"businessId": business_id, "cutoffHours": DEFAULT_CUTOFF_HOURS}


def _reservation_datetime(res: dict) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(f"{res['date']}T{res['time']}:00")
    except Exception:
        return None


async def is_within_free_cancellation_window(res: dict, business_id: Optional[str] = None) -> bool:
    """True when this cancellation is early enough to owe nothing.

    A missing or unparseable reservation date/time fails toward the
    guest, not the business: we genuinely don't know how close the
    booking is, so treat it as within the free window rather than
    forfeiting money on a guess.
    """
    when = _reservation_datetime(res)
    if when is None:
        return True
    policy = await get_policy(business_id)
    cutoff = timedelta(hours=float(policy.get("cutoffHours", DEFAULT_CUTOFF_HOURS)))
    return (when - datetime.utcnow()) >= cutoff
