"""Resolve a typed table number to a real table on a floor plan.

The POS lets staff type a table number by hand ("12", "Patio-A"). Free text is
how orders end up on tables that don't exist, so everything that accepts a
typed table routes through `resolve_table` here rather than trusting the
string. Matching is deliberately forgiving about how people type — "Table 12",
"table-12", " 12 " and "12" are the same table — but never invents one.

Venues that haven't drawn a floor plan yet must keep working, so
`has_floor_plan()` lets callers fall back to accepting free text instead of
blocking a sale behind setup the venue hasn't done.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

from database import db

# Leading words people type before the actual identifier.
_PREFIX_RE = re.compile(r"^(?:table|tbl|tab|t)?\s*[#\-.]?\s*", re.IGNORECASE)


def normalize_table_number(raw: Any) -> str:
    """Fold a typed table reference to a comparable key.

    "Table 12" / "t12" / " 12 " / "12" all collapse to "12", and
    "Patio - A" / "patio a" collapse to "PATIOA".
    """
    s = str(raw or "").strip()
    if not s:
        return ""
    s = _PREFIX_RE.sub("", s, count=1)
    # Drop separators so "Patio-A" == "Patio A" == "patioa".
    s = re.sub(r"[\s\-_.#]+", "", s)
    return s.upper()


async def get_plans(active_only: bool = True) -> List[Dict[str, Any]]:
    """Floor plans, newest-updated first, optionally only the active ones."""
    query = {"isActive": True} if active_only else {}
    plans = await db.floor_plans.find(query, {"_id": 0}).to_list(100)
    if active_only and not plans:
        # A venue may have plans that predate the isActive flag; rather than
        # report "no floor plan" (which would switch validation off) fall back
        # to every plan on file.
        plans = await db.floor_plans.find({}, {"_id": 0}).to_list(100)
    return plans


async def list_tables(active_only: bool = True) -> List[Dict[str, Any]]:
    """Every table across the relevant plans, each tagged with its planId."""
    out: List[Dict[str, Any]] = []
    for plan in await get_plans(active_only=active_only):
        for t in plan.get("tables") or []:
            if t.get("isActive") is False:
                continue
            row = dict(t)
            row["planId"] = plan.get("id")
            row["planName"] = plan.get("name")
            out.append(row)
    return out


async def has_floor_plan() -> bool:
    """True when at least one table is configured anywhere.

    Callers use this to decide whether an unrecognised table number is an
    error or simply a venue that types its own table names.
    """
    return len(await list_tables()) > 0


async def resolve_table(raw: Any) -> Optional[Tuple[Dict[str, Any], str]]:
    """Return (table, planId) for a typed table number, or None if unknown."""
    key = normalize_table_number(raw)
    if not key:
        return None
    for t in await list_tables():
        if normalize_table_number(t.get("number")) == key:
            return t, t.get("planId")
        # Some venues name tables instead of numbering them.
        if t.get("name") and normalize_table_number(t.get("name")) == key:
            return t, t.get("planId")
    return None


async def suggest(raw: Any, limit: int = 6) -> List[str]:
    """Nearby table numbers to offer when a typed one doesn't exist."""
    key = normalize_table_number(raw)
    tables = await list_tables()
    numbers = [str(t.get("number") or "") for t in tables if t.get("number")]
    if not key:
        return sorted(numbers)[:limit]
    # Prefix matches first (mid-typing), then anything containing the input.
    starts = [n for n in numbers if normalize_table_number(n).startswith(key)]
    contains = [n for n in numbers if key in normalize_table_number(n) and n not in starts]
    return (starts + contains)[:limit] or sorted(numbers)[:limit]


async def set_table_status(table_id: str, plan_id: str, status: str,
                           order_id: Optional[str] = None) -> bool:
    """Write a table's status back onto its plan. Returns True if it changed."""
    plan = await db.floor_plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        return False
    tables = plan.get("tables") or []
    hit = False
    for t in tables:
        if t.get("id") == table_id:
            t["status"] = status
            if status == "available":
                t["currentOrderId"] = None
            elif order_id is not None:
                t["currentOrderId"] = order_id
            hit = True
            break
    if not hit:
        return False
    from datetime import datetime
    await db.floor_plans.update_one(
        {"id": plan_id},
        {"$set": {"tables": tables, "updatedAt": datetime.utcnow().isoformat()}},
    )
    return True
