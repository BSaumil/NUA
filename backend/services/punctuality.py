"""Punctuality: how a staff member's actual clock-in/out compares to their
rostered shift time.

Uses the same UTC-wall-clock convention already established in
routes/staff_management.py's _is_rostered_now() and analytics.py's
labor-cost calc — not truly timezone-aware, but consistent with how every
other shift-time comparison in this app already works, rather than
introducing a second, inconsistent standard just for this.
"""
from datetime import datetime
from typing import Optional

GRACE_MINUTES = 5


def _minutes(hh_mm: str) -> Optional[int]:
    try:
        h, m = (int(x) for x in hh_mm.split(":"))
        return h * 60 + m
    except Exception:
        return None


def _clock_minutes(iso_ts: Optional[str]) -> Optional[int]:
    if not iso_ts:
        return None
    try:
        dt = datetime.fromisoformat(iso_ts)
        return dt.hour * 60 + dt.minute
    except Exception:
        return None


def shift_punctuality(timecard: dict, roster_shift: dict) -> dict:
    """Compares one timecard against its matching rostered shift.

    lateMinutes / earlyLeaveMinutes are positive when the staff member
    clocked in late or clocked out early, zero or negative when they were
    on time or better. onTime allows a GRACE_MINUTES window either side —
    a genuine shift never starts to the exact second.
    """
    scheduled_start = _minutes(roster_shift.get("startTime", ""))
    scheduled_end = _minutes(roster_shift.get("endTime", ""))
    actual_in = _clock_minutes(timecard.get("clockIn"))
    actual_out = _clock_minutes(timecard.get("clockOut"))

    late_minutes = (actual_in - scheduled_start) if (scheduled_start is not None and actual_in is not None) else None
    early_leave_minutes = (scheduled_end - actual_out) if (scheduled_end is not None and actual_out is not None) else None

    on_time = (
        late_minutes is not None and late_minutes <= GRACE_MINUTES
        and (early_leave_minutes is None or early_leave_minutes <= GRACE_MINUTES)
    )

    return {
        "scheduledStart": roster_shift.get("startTime"),
        "scheduledEnd": roster_shift.get("endTime"),
        "actualClockIn": timecard.get("clockIn"),
        "actualClockOut": timecard.get("clockOut"),
        "lateMinutes": late_minutes,
        "earlyLeaveMinutes": early_leave_minutes,
        "onTime": on_time,
    }
