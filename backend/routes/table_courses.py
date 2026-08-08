"""
Table Course Management — dining courses, dwell timing, colour codes and the
"Send" nudge from the floor plan.

Concepts:
  • Course definitions live in `table_courses.settings` — owner/manager edits
    them once; the whole floor plan uses those thresholds to colour-code
    tables by their current course + dwell time.
  • Live table state (occupied since / current course) lives on the
    `table_states` collection keyed by tableId.
  • "Send" pushes a nudge to the assigned server via the dock's notification
    channel (persisted so the server can catch up if offline).
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from database import db
from deps import get_user
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ─── Defaults — sensible thresholds for a mid-tier venue ─────────────────
DEFAULT_COURSES = [
    {"key": "seated",    "label": "Seated",    "colour": "#94A3B8", "maxMinutes": 5,   "next": "drinks"},
    {"key": "drinks",    "label": "Drinks",    "colour": "#38BDF8", "maxMinutes": 10,  "next": "entree"},
    {"key": "entree",    "label": "Entrée",    "colour": "#22C55E", "maxMinutes": 20,  "next": "main"},
    {"key": "main",      "label": "Main",      "colour": "#F59E0B", "maxMinutes": 45,  "next": "dessert"},
    {"key": "dessert",   "label": "Dessert",   "colour": "#EC4899", "maxMinutes": 20,  "next": "coffee"},
    {"key": "coffee",    "label": "Coffee",    "colour": "#8B5CF6", "maxMinutes": 15,  "next": "check"},
    {"key": "check",     "label": "Check",     "colour": "#EF4444", "maxMinutes": 10,  "next": None},
]
# When a table stays in a course past maxMinutes, its colour intensifies to signal to servers.
OVERDUE_COLOUR = "#7F1D1D"


class Course(BaseModel):
    key: str
    label: str
    colour: str
    maxMinutes: int
    next: Optional[str] = None


class CoursesSettingsIn(BaseModel):
    courses: list[Course]
    overdueColour: Optional[str] = OVERDUE_COLOUR
    autoAdvance: bool = False        # if True, courses auto-advance when maxMinutes elapses


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Settings CRUD ───────────────────────────────────────────────────────
@router.get("/table-courses/settings")
async def get_settings(_: dict = Depends(get_user)):
    row = await db.table_course_settings.find_one({"_id": "singleton"})
    if not row:
        row = {
            "courses": DEFAULT_COURSES,
            "overdueColour": OVERDUE_COLOUR,
            "autoAdvance": False,
            "updatedAt": _now(),
        }
        await db.table_course_settings.insert_one({"_id": "singleton", **row})
    row.pop("_id", None)
    return row


@router.put("/table-courses/settings")
async def update_settings(body: CoursesSettingsIn, user: dict = Depends(get_user)):
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(403, "Owner or manager only")
    payload = {
        "courses":       [c.dict() for c in body.courses],
        "overdueColour": body.overdueColour or OVERDUE_COLOUR,
        "autoAdvance":   bool(body.autoAdvance),
        "updatedAt":     _now(),
        "updatedBy":     user.get("email"),
    }
    await db.table_course_settings.update_one(
        {"_id": "singleton"}, {"$set": payload}, upsert=True,
    )
    return payload


# ─── Live table state ────────────────────────────────────────────────────
class TableStateIn(BaseModel):
    tableId: str
    course: Optional[str] = None
    partySize: Optional[int] = None
    serverId: Optional[str] = None
    reservationId: Optional[str] = None
    guestName: Optional[str] = None
    note: Optional[str] = None
    clearState: bool = False


@router.get("/table-courses/states")
async def list_states(_: dict = Depends(get_user)):
    """Return every table that has a live state (i.e. is currently occupied).
    Each row is enriched with derived colour + dwell minutes so the SPA can
    render without extra roundtrips."""
    states = await db.table_states.find({}, {"_id": 0}).to_list(500)
    settings_row = await db.table_course_settings.find_one({"_id": "singleton"})
    courses = (settings_row or {}).get("courses", DEFAULT_COURSES)
    overdue_colour = (settings_row or {}).get("overdueColour", OVERDUE_COLOUR)
    by_key = {c["key"]: c for c in courses}
    now = datetime.now(timezone.utc)

    enriched = []
    for s in states:
        course_obj = by_key.get(s.get("course"), by_key.get("seated", courses[0]))
        # Total dwell = since seatedAt; course dwell = since courseStartedAt.
        seated_at = s.get("seatedAt")
        course_at = s.get("courseStartedAt") or seated_at
        dwell_min = 0
        course_min = 0
        if seated_at:
            dwell_min = max(0, int((now - datetime.fromisoformat(seated_at)).total_seconds() // 60))
        if course_at:
            course_min = max(0, int((now - datetime.fromisoformat(course_at)).total_seconds() // 60))
        overdue = course_obj.get("maxMinutes") and course_min > course_obj["maxMinutes"]
        s["dwellMinutes"] = dwell_min
        s["courseMinutes"] = course_min
        s["courseLabel"] = course_obj.get("label")
        s["colour"] = overdue_colour if overdue else course_obj.get("colour")
        s["overdue"] = bool(overdue)
        enriched.append(s)
    return {"states": enriched, "courses": courses, "overdueColour": overdue_colour}


@router.post("/table-courses/states")
async def upsert_state(body: TableStateIn, user: dict = Depends(get_user)):
    """Seat a table, advance its course, or clear it (`clearState=true`)."""
    if body.clearState:
        r = await db.table_states.delete_one({"tableId": body.tableId})
        return {"cleared": r.deleted_count > 0}

    existing = await db.table_states.find_one({"tableId": body.tableId})
    now = _now()
    if existing:
        update = {"updatedAt": now}
        if body.course and body.course != existing.get("course"):
            update["course"] = body.course
            update["courseStartedAt"] = now
        for f in ("partySize", "serverId", "reservationId", "guestName", "note"):
            v = getattr(body, f)
            if v is not None:
                update[f] = v
        await db.table_states.update_one({"tableId": body.tableId}, {"$set": update})
        return await db.table_states.find_one({"tableId": body.tableId}, {"_id": 0})

    doc = {
        "id": str(uuid.uuid4()),
        "tableId": body.tableId,
        "course": body.course or "seated",
        "partySize": body.partySize,
        "serverId": body.serverId,
        "reservationId": body.reservationId,
        "guestName": body.guestName,
        "note": body.note,
        "seatedAt": now,
        "courseStartedAt": now,
        "createdAt": now,
        "updatedAt": now,
        "createdBy": user.get("email"),
    }
    await db.table_states.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ─── "Send" nudge from floor plan ────────────────────────────────────────
class SendNudgeIn(BaseModel):
    tableId: str
    message: str = "Please check on this table"
    targetServerId: Optional[str] = None      # overrides table's assigned server
    priority: str = "normal"                  # normal | urgent


@router.post("/table-courses/send")
async def send_nudge(body: SendNudgeIn, user: dict = Depends(get_user)):
    """Drops a notification into the dock for the server assigned to the
    table (or the explicit `targetServerId`). Also stored so the server can
    catch up when they log in."""
    state = await db.table_states.find_one({"tableId": body.tableId}, {"_id": 0})
    server_id = body.targetServerId or (state or {}).get("serverId")

    notif = {
        "id": str(uuid.uuid4()),
        "type": "table_nudge",
        "tableId": body.tableId,
        "serverId": server_id,          # None → broadcast to all servers
        "message": body.message,
        "priority": body.priority if body.priority in ("normal", "urgent") else "normal",
        "sentBy": user.get("email"),
        "sentAt": _now(),
        "read": False,
    }
    await db.dock_notifications.insert_one(notif)
    notif.pop("_id", None)

    # dock_notifications had no reader anywhere in the UI — a sent nudge was
    # persisted but never actually seen by the server it was meant for. Also
    # fan it out through the universal notification bell (already wired into
    # every staff screen), resolving serverId to their email when possible
    # and broadcasting to front-of-house otherwise.
    try:
        from services import notification_service
        target_email = None
        if server_id:
            staffer = await db.auth_users.find_one({"id": server_id}, {"_id": 0, "email": 1})
            target_email = (staffer or {}).get("email")
        await notification_service.send(
            kind="kitchen", title=f"Table {body.tableId} needs you", body=body.message,
            email=target_email, role=None if target_email else "cashier",
            severity="high" if notif["priority"] == "urgent" else "info",
            link="/floor-plan",
        )
    except Exception as e:
        from utils.errors import log_and_continue
        log_and_continue(logger, f"Table nudge bell notification failed for table {body.tableId}", e)

    return notif


@router.get("/table-courses/notifications")
async def list_notifications(serverId: Optional[str] = None, unreadOnly: bool = False,
                              _: dict = Depends(get_user)):
    q = {}
    if serverId:
        q["$or"] = [{"serverId": serverId}, {"serverId": None}]
    if unreadOnly:
        q["read"] = False
    return await db.dock_notifications.find(q, {"_id": 0}).sort("sentAt", -1).to_list(200)


@router.post("/table-courses/notifications/{notif_id}/read")
async def mark_notif_read(notif_id: str, user: dict = Depends(get_user)):
    r = await db.dock_notifications.update_one(
        {"id": notif_id},
        {"$set": {"read": True, "readAt": _now(), "readBy": user.get("email")}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Notification not found")
    return {"read": True}
