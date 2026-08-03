"""Coursing — which dish belongs to which course, and when each course fires.

Two things are deliberately separated here:

  * **Assignment** — what course an item lands on. Owners map categories to
    courses ("Entrees" -> 1, "Mains" -> 2) so staff don't have to think during
    service; anything unmapped falls to `defaultCourse`.
  * **Firing** — whether a course goes to the pass now or waits. Coursed
    service holds later courses until the server fires them; "straight fire"
    sends everything at once.

The whole feature is off by default. A takeaway-only venue should never see a
course selector, so `enabled: False` means the POS renders exactly what it did
before this existed.
"""
from typing import Any, Dict, List, Optional

from database import db

CONFIG_ID = "singleton"

DEFAULT_COURSING_CONFIG: Dict[str, Any] = {
    # Master switch. Off = no course UI anywhere, everything fires on send.
    "enabled": False,
    # Owner-editable course list. `key` is what gets stamped on items and is
    # what the KDS hold/fire endpoints address.
    "courses": [
        {"key": 1, "label": "Starter"},
        {"key": 2, "label": "Main"},
        {"key": 3, "label": "Dessert"},
        {"key": 4, "label": "Coffee"},
    ],
    # Category -> course key. Matched case-insensitively.
    "categoryCourses": {},
    # Where anything unmapped lands.
    "defaultCourse": 1,
    # On send, fire the earliest course immediately and hold the rest. Turn off
    # to hold everything until the server fires each course by hand.
    "autoFireFirstCourse": True,
    # Show the "Fire All Now" override in the cart.
    "allowStraightFire": True,
    # Order types that always straight-fire regardless of the above — a
    # takeaway coffee should never sit held behind a starter.
    "straightFireOrderTypes": ["takeaway", "delivery"],
}


async def get_config() -> Dict[str, Any]:
    row = await db.coursing_config.find_one({"_id": CONFIG_ID}, {"_id": 0})
    if not row:
        row = dict(DEFAULT_COURSING_CONFIG)
        await db.coursing_config.insert_one({"_id": CONFIG_ID, **row})
        return row
    # Fill in keys added after this venue first saved its config.
    merged = dict(DEFAULT_COURSING_CONFIG)
    merged.update(row)
    return merged


def course_keys(config: Dict[str, Any]) -> List[int]:
    keys = []
    for c in config.get("courses") or []:
        try:
            keys.append(int(c.get("key")))
        except (TypeError, ValueError):
            continue
    return sorted(set(keys)) or [1]


def course_for_category(category: Optional[str], config: Dict[str, Any]) -> int:
    """Which course a category maps to, falling back to the default."""
    default = config.get("defaultCourse") or 1
    if not category:
        return default
    mapping = config.get("categoryCourses") or {}
    wanted = str(category).strip().lower()
    for cat, key in mapping.items():
        if str(cat).strip().lower() == wanted:
            try:
                return int(key)
            except (TypeError, ValueError):
                return default
    return default


def assign_courses(items: List[dict], config: Dict[str, Any]) -> List[dict]:
    """Stamp a course on every item.

    An explicit course already on the item wins — the server may have moved a
    dish to a different course on the POS, and that decision outranks the
    category default.
    """
    valid = set(course_keys(config))
    default = config.get("defaultCourse") or 1
    out = []
    for it in items or []:
        row = dict(it)
        explicit = row.get("course")
        if explicit is not None and str(explicit).strip() != "":
            try:
                course = int(explicit)
            except (TypeError, ValueError):
                course = course_for_category(row.get("category"), config)
        else:
            course = course_for_category(row.get("category"), config)
        # Never stamp a course the venue has since deleted.
        row["course"] = course if course in valid else default
        out.append(row)
    return out


def is_straight_fire(order_type: Optional[str], config: Dict[str, Any],
                     requested: bool = False) -> bool:
    """Should this order skip coursing and fire everything at once?"""
    if not config.get("enabled"):
        return True
    if requested:
        return True
    types = [str(t).lower() for t in (config.get("straightFireOrderTypes") or [])]
    ot = str(order_type or "").lower().replace("-", "_")
    return ot in types or ot.replace("_", "-") in types


def initial_course_states(items: List[dict], config: Dict[str, Any],
                          order_type: Optional[str] = None,
                          straight_fire: bool = False,
                          fired_by: Optional[str] = None,
                          now: Optional[str] = None) -> Dict[str, Any]:
    """Build the kitchen order's `courses` map at the moment of sending.

    Straight fire => every course fired. Coursed => the earliest course fires
    (when `autoFireFirstCourse`) and everything after it is held, which is what
    stops a dessert hitting the pass alongside the entree.
    """
    present = sorted({int(it.get("course") or 1) for it in items or []}) or [1]
    straight = is_straight_fire(order_type, config, straight_fire)
    states: Dict[str, Any] = {}
    for idx, course in enumerate(present):
        base = {"status": "queued", "heldAt": None, "firedAt": None,
                "firedBy": None, "servedAt": None}
        if straight:
            base.update({"status": "fired", "firedAt": now, "firedBy": fired_by})
        elif idx == 0 and config.get("autoFireFirstCourse", True):
            base.update({"status": "fired", "firedAt": now, "firedBy": fired_by})
        elif idx > 0:
            base.update({"status": "held", "heldAt": now})
        states[str(course)] = base
    return states


def sanitize_config(body: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only known keys, and coerce the shapes the POS relies on."""
    patch: Dict[str, Any] = {}
    for key in DEFAULT_COURSING_CONFIG:
        if key not in body:
            continue
        val = body[key]
        if key == "courses":
            cleaned = []
            for c in val or []:
                try:
                    k = int(c.get("key"))
                except (TypeError, ValueError):
                    continue
                label = str(c.get("label") or f"Course {k}").strip()
                cleaned.append({"key": k, "label": label or f"Course {k}"})
            # A venue with no courses at all would break assignment, so keep
            # at least one.
            patch[key] = cleaned or list(DEFAULT_COURSING_CONFIG["courses"])
        elif key == "categoryCourses":
            cleaned = {}
            for cat, course in (val or {}).items():
                try:
                    cleaned[str(cat)] = int(course)
                except (TypeError, ValueError):
                    continue
            patch[key] = cleaned
        elif key == "defaultCourse":
            try:
                patch[key] = int(val)
            except (TypeError, ValueError):
                patch[key] = 1
        elif key == "straightFireOrderTypes":
            patch[key] = [str(t) for t in (val or [])]
        else:
            patch[key] = bool(val)

    # Drop mappings and defaults that point at courses which no longer exist.
    if "courses" in patch:
        valid = {c["key"] for c in patch["courses"]}
        if "categoryCourses" in patch:
            patch["categoryCourses"] = {
                k: v for k, v in patch["categoryCourses"].items() if v in valid
            }
        if patch.get("defaultCourse") not in valid:
            patch["defaultCourse"] = min(valid)
    return patch
