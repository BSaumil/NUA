"""Shared date-range query helper.

Before this, the same "$match stage for an optional date range" logic was
copy-pasted with small variations across analytics.py, transactions.py,
settings.py, and others — some comparing `datetime` objects, some comparing
raw ISO strings against a `datetime`-typed field (a latent bug: whether that
comparison works at all depends on Mongo/driver type coercion, not on
anything the code guarantees). One canonical version, one behavior.
"""
from datetime import datetime
from typing import Optional


def date_range_filter(field: str, start_date: Optional[str], end_date: Optional[str]) -> dict:
    """A Mongo filter clause for an optional date range on `field`, or {} for
    all-time. Both bounds are inclusive. Returns {} rather than filtering
    out everything when neither bound is given — an unbounded report is a
    valid, common request (lifetime figures), not an error.
    """
    if not start_date and not end_date:
        return {}
    rng = {}
    if start_date:
        rng["$gte"] = datetime.fromisoformat(start_date)
    if end_date:
        rng["$lte"] = datetime.fromisoformat(end_date)
    return {field: rng}
