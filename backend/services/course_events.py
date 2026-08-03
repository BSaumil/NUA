"""Recording what happened to a course, and who did it.

Two separate needs, deliberately kept together so a state change can't be
recorded in one place and missed in the other:

  * **History** — an append-only trail on the ticket, so questions like "how
    long did mains sit at the pass?" have an answer. The `courses` map only
    keeps the latest timestamp per state, so a course held twice, or re-fired
    after a hold, silently loses its earlier life.
  * **Audit** — fires and voids land in the same audit log Settings already
    surfaces. Comps and voids are the classic shrinkage vector, and a void
    recorded only on the ticket it deleted items from is not an audit trail.

Both are best-effort: losing a history row must never stop food reaching the
pass.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import db

log = logging.getLogger(__name__)

MAX_HISTORY = 200   # a very long service, not an unbounded document


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def record_transition(order_id: str, course: int, to_state: str,
                            actor: Optional[str], from_state: Optional[str] = None,
                            extra: Optional[Dict[str, Any]] = None) -> None:
    """Append one course state change to the ticket's history."""
    entry = {
        "course": int(course),
        "from": from_state,
        "to": to_state,
        "at": _now(),
        "by": actor or "system",
        **(extra or {}),
    }
    try:
        await db.kitchen_orders.update_one(
            {"id": order_id},
            {"$push": {"courseHistory": {"$each": [entry], "$slice": -MAX_HISTORY}}},
        )
    except Exception as e:
        log.warning("course history append failed for %s: %s", order_id, e)


def course_state(order: Dict[str, Any], course: int) -> Optional[str]:
    return ((order.get("courses") or {}).get(str(course)) or {}).get("status")


def minutes_between(history: List[dict], course: int, from_state: str, to_state: str) -> Optional[float]:
    """How long a course spent between two states, from the history trail.

    Uses the last time it entered `from_state` before the first subsequent
    `to_state`, so a course held, fired, held again and re-fired reports the
    span that actually mattered rather than the whole meal.
    """
    rows = [h for h in (history or []) if int(h.get("course", -1)) == int(course)]
    start = None
    for h in rows:
        if h.get("to") == from_state:
            start = h.get("at")
        elif h.get("to") == to_state and start:
            try:
                a = datetime.fromisoformat(start)
                b = datetime.fromisoformat(h["at"])
            except (TypeError, ValueError):
                return None
            if not a.tzinfo:
                a = a.replace(tzinfo=timezone.utc)
            if not b.tzinfo:
                b = b.replace(tzinfo=timezone.utc)
            return round((b - a).total_seconds() / 60, 2)
    return None


def summarise(order: Dict[str, Any]) -> Dict[str, Any]:
    """Per-course timings a manager would actually ask about."""
    history = order.get("courseHistory") or []
    out: Dict[str, Any] = {}
    for key in (order.get("courses") or {}):
        try:
            course = int(key)
        except (TypeError, ValueError):
            continue
        out[key] = {
            "heldMinutes": minutes_between(history, course, "held", "fired"),
            "cookMinutes": minutes_between(history, course, "fired", "ready"),
            # The number that actually costs a venue: food sitting under a
            # lamp between the kitchen calling it and someone running it.
            "atPassMinutes": minutes_between(history, course, "ready", "served"),
        }
    return out


async def audit(action: str, order: Dict[str, Any], *, course: Optional[int] = None,
                actor: Optional[str] = None, memo: Optional[str] = None,
                severity: str = "info", before: Optional[dict] = None,
                after: Optional[dict] = None) -> None:
    """Write a course/void event into the universal audit log."""
    try:
        from services import audit_service
        await audit_service.log_event(
            entity_type="kitchen_order",
            entity_id=order.get("id"),
            action=action,
            before=before,
            after=after,
            memo=memo,
            severity=severity,
            tags=["coursing"] + ([f"course:{course}"] if course is not None else []),
        )
    except Exception as e:
        log.warning("audit write failed for %s/%s: %s", order.get("id"), action, e)
