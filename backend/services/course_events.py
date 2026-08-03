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
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from database import db

log = logging.getLogger(__name__)

# The ticket keeps a bounded window so the document can't grow without limit,
# but nothing is lost: every entry is also written to its own collection, so a
# long-lived ticket's earliest history is still there rather than silently
# rolling off the front.
MAX_HISTORY = 200


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

    # Durable copy — this is what analytics reads, and what makes the cap on
    # the ticket safe.
    try:
        await db.course_events.insert_one({
            **entry, "orderId": order_id,
            # Real date (not the ISO string) so the TTL index can expire it.
            "expiresAt": datetime.now(timezone.utc) + timedelta(days=RETENTION_DAYS),
        })
    except Exception as e:
        log.warning("course event write failed for %s: %s", order_id, e)


# How long the durable trail is kept. Long enough for a quarter's analytics,
# bounded so the collection can't grow forever on a busy site.
RETENTION_DAYS = int(os.environ.get("COURSE_EVENT_RETENTION_DAYS", "120"))


async def ensure_indexes() -> None:
    """Index the trail on time, and let Mongo expire old rows itself.

    Analytics filters on `at` over a rolling window, which is a collection
    scan without this. The TTL index is what stops the durable trail — the
    thing that makes the ticket's own capped history safe — from becoming an
    unbounded collection instead.
    """
    try:
        await db.course_events.create_index("at")
        await db.course_events.create_index("orderId")
        # `expiresAt` is a real date so Mongo's TTL monitor can act on it;
        # `at` is stored as an ISO string for everything else that reads it.
        await db.course_events.create_index("expiresAt", expireAfterSeconds=0)
    except Exception as e:
        log.warning("course event index setup failed: %s", e)


async def purge_expired() -> int:
    """Delete rows past retention.

    A TTL index does this on its own in a real deployment, but it isn't
    instant, and mongomock has no TTL monitor at all — so retention is also
    enforceable on demand rather than only being a promise.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
    try:
        r = await db.course_events.delete_many({"at": {"$lt": cutoff}})
        return r.deleted_count
    except Exception as e:
        log.warning("course event purge failed: %s", e)
        return 0


async def record_initial(order_id: str, courses: Dict[str, Any],
                         actor: Optional[str] = None) -> None:
    """Record the state each course starts in.

    A course held at creation never passes through the hold endpoint, so
    without this there is no "held" entry to measure from and held time is
    permanently null for the ordinary case — which is most of them. The entry
    is marked `initial` so it's distinguishable from a server actively
    choosing to hold something later.
    """
    for key, state in (courses or {}).items():
        status = (state or {}).get("status")
        if not status:
            continue
        try:
            course = int(key)
        except (TypeError, ValueError):
            continue
        await record_transition(order_id, course, status, actor,
                                from_state=None, extra={"initial": True})


async def full_history(order_id: str) -> list:
    """Every recorded transition for a ticket, including any the ticket's own
    capped window has since dropped."""
    rows = await db.course_events.find(
        {"orderId": order_id}, {"_id": 0}).to_list(2000)
    rows.sort(key=lambda r: r.get("at") or "")
    return rows


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


# Course state -> what the ticket as a whole is doing. Ordered worst-to-best
# so the ticket reports the least-progressed thing still outstanding.
def derive_order_status(order: Dict[str, Any]) -> Optional[str]:
    """What the ticket's status should be, given its courses.

    The two were tracked independently, so a ticket could read "ready" while a
    course sat held — the expo screen says collect it, the kitchen hasn't
    started half of it. Courses are the source of truth here because they're
    what staff actually act on.
    """
    courses = order.get("courses") or {}
    if not courses:
        return None                       # pre-coursing ticket: leave it alone
    states = {(v or {}).get("status") for v in courses.values()}
    if states <= {"served"}:
        return "served"
    if states <= {"served", "ready"}:
        return "ready"                    # everything left is up at the pass
    if states & {"fired", "queued"}:
        return "preparing"
    if states <= {"held", "served", "ready"}:
        # Nothing is cooking; whatever remains is deliberately waiting.
        return "new"
    return None


async def reconcile_status(order_id: str) -> Optional[str]:
    """Bring a ticket's status in line with its courses. Returns the new one."""
    order = await db.kitchen_orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        return None
    want = derive_order_status(order)
    if not want or want == order.get("status"):
        return order.get("status")
    patch: Dict[str, Any] = {"status": want}
    if want == "ready" and not order.get("readyAt"):
        patch["readyAt"] = _now()
    if want == "served" and not order.get("servedAt"):
        patch["servedAt"] = _now()
    try:
        await db.kitchen_orders.update_one({"id": order_id}, {"$set": patch})
    except Exception as e:
        log.warning("status reconcile failed for %s: %s", order_id, e)
    return want


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
