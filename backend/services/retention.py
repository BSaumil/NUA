"""How long the ephemeral stuff sticks around, and why nothing financial is here.

Coursing already had a retention story (course_events, TTL'd at 30 days) and
2FA got one too (totp_used, trusted_devices). Everything else in the database
just accumulated forever: an abandoned kiosk cart from a guest who walked out
without ordering, an in-app notification from six months ago, a failed-login
lockout record — none of it useful past a certain age, all of it useful right
up until then.

What is deliberately NOT here: transactions, refunds, the audit log, BAS/GST
reports. Those are financial and compliance records — in Australia, tax law
generally expects five years of retention, and an automatic purge job is
exactly the kind of thing that should never touch them. If a venue needs to
delete customer data on request, that's the existing GDPR erase endpoint
(routes/v15_features.py), which acts on a specific person by request, not a
timer that runs on everyone.

Retention here works the same way it does for coursing and 2FA: an
`expiresAt` field set at write time, backed by a TTL index. Changing the
number of days below only changes it for documents written after the change —
a TTL index can't retroactively shorten or lengthen the lifetime of rows
already on disk, so this is a policy for what gets written next, not a purge
tool for what already exists. (`purge_now()` exists for the latter, for a
manager who wants to reclaim space immediately rather than wait.)
"""
import logging
from datetime import datetime, timedelta, timezone

from database import db

log = logging.getLogger(__name__)

# Days to keep. Deliberately short for things that are genuinely disposable —
# a kiosk cart nobody checked out, a login lockout that's long since expired —
# and generous for things a manager might still want to look back on.
KIOSK_SESSION_DAYS = 1
NOTIFICATION_DAYS = 90
LOGIN_LOCKOUT_DAYS = 1


def kiosk_session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=KIOSK_SESSION_DAYS)


def notification_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=NOTIFICATION_DAYS)


async def ensure_indexes() -> None:
    try:
        await db.kiosk_sessions.create_index("expiresAt", expireAfterSeconds=0)
        await db.notifications.create_index("expiresAt", expireAfterSeconds=0)
        # login_attempts already carries a real datetime in locked_until —
        # no new field needed, the existing one is TTL-able as-is.
        await db.login_attempts.create_index("locked_until", expireAfterSeconds=0)
    except Exception as e:
        log.info("retention indexes not created: %s", e)


POLICY = [
    {"collection": "kiosk_sessions", "field": "expiresAt", "days": KIOSK_SESSION_DAYS,
     "reason": "abandoned guest carts — operational clutter, not a record of anything"},
    {"collection": "notifications", "field": "expiresAt", "days": NOTIFICATION_DAYS,
     "reason": "in-app notifications — useful for a season, not a compliance record"},
    {"collection": "login_attempts", "field": "locked_until", "days": LOGIN_LOCKOUT_DAYS,
     "reason": "failed-login lockout counters — meaningless once the lockout has passed"},
]


async def purge_now() -> dict:
    """Delete anything already past its expiry, for whoever doesn't want to
    wait for Mongo's own TTL sweep (which runs on its own schedule, typically
    within a minute but not instantly). Safe to call as often as wanted —
    it only ever removes rows that TTL would have removed anyway."""
    now = datetime.now(timezone.utc)
    out = {}
    for rule in POLICY:
        try:
            res = await db[rule["collection"]].delete_many({rule["field"]: {"$lt": now}})
            out[rule["collection"]] = res.deleted_count
        except Exception as e:
            out[rule["collection"]] = f"error: {e}"
    return out


async def status() -> list:
    """What's currently pending expiry, per collection — for an owner to see
    the policy is actually doing something rather than trusting a comment."""
    now = datetime.now(timezone.utc)
    rows = []
    for rule in POLICY:
        try:
            total = await db[rule["collection"]].count_documents({})
            expired = await db[rule["collection"]].count_documents(
                {rule["field"]: {"$lt": now}})
        except Exception:
            total = expired = None
        rows.append({**rule, "totalDocuments": total, "pastExpiry": expired})
    return rows
