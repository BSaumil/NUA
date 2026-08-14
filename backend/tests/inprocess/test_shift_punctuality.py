"""Pre-Shift Briefing should show who's on shift to everyone, and to owners
only, also show each staff member's actual clock-in/clock-out time against
their rostered shift so lateness is visible. The staff leaderboard folds the
same comparison into its performance score as a punctuality bonus."""
import asyncio
from datetime import date, datetime, time, timezone

from conftest import req


def _today_iso():
    return date.today().isoformat()


def _add_staff(client, owner_headers, name, pin, role="cashier"):
    r = req(client, "POST", "/api/auth/staff/add", headers=owner_headers,
            json={"name": name, "role": role, "pin": pin})
    assert r.status_code == 200, r.text
    return r.json()


def _roster(client, owner_headers, staff, start="09:00", end="17:00"):
    r = req(client, "POST", "/api/staff/roster", headers=owner_headers, json={
        "staffId": staff["id"], "staffName": staff["name"],
        "date": _today_iso(), "startTime": start, "endTime": end,
    })
    assert r.status_code == 200, r.text
    return r.json()


def _insert_timecard(staff, clock_in_time, clock_out_time=None):
    from database import db

    async def run():
        await db.timecards.insert_one({
            "id": f"TC-{staff['id']}-{clock_in_time.isoformat()}",
            "staffId": staff["id"], "staffName": staff["name"], "role": staff["role"],
            "clockIn": datetime.combine(date.today(), clock_in_time, tzinfo=timezone.utc).isoformat(),
            "clockOut": datetime.combine(date.today(), clock_out_time, tzinfo=timezone.utc).isoformat() if clock_out_time else None,
            "breakMinutes": 0, "hoursWorked": 8 if clock_out_time else 0, "payRate": 25, "salaryType": "hourly",
        })
    asyncio.get_event_loop().run_until_complete(run())


def _staff_headers(client, staff):
    """A token for this staff member, minted directly rather than through
    pin-login — pin-login's own roster gate (is this staff member rostered
    on *right now*) is a separate concern from what this file is testing,
    and would make these tests flaky against whatever time they happen to
    run at (mirrors test_pin_roster_gate.py's own JWT-crafting helper)."""
    import jwt
    import os
    from datetime import timedelta
    token = jwt.encode(
        {"sub": staff["id"], "email": staff["email"], "role": staff["role"],
         "businessId": staff.get("businessId"), "exp": datetime.now(timezone.utc) + timedelta(hours=8),
         "type": "access"},
        os.environ["JWT_SECRET"], algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_preshift_briefing_shows_rostered_staff_to_everyone(client, owner_headers):
    staff = _add_staff(client, owner_headers, "ZZZ Briefing Visible Cashier", "8801")
    # Spans the whole day so pin-login's roster gate passes at any test run time.
    _roster(client, owner_headers, staff, start="00:00", end="23:59")

    staff_headers = _staff_headers(client, staff)
    r = req(client, "GET", "/api/preshift/briefing", headers=staff_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    entry = next((s for s in body["onShift"] if s["staffId"] == staff["id"]), None)
    assert entry is not None, body["onShift"]
    assert entry["staffName"] == staff["name"]
    # Non-owners see who's on shift but not actual clock times/punctuality.
    assert "clockIn" not in entry
    assert "scheduledStart" not in entry
    assert "onTime" not in entry


def test_preshift_briefing_shows_actual_times_and_lateness_to_owner_only(client, owner_headers):
    staff = _add_staff(client, owner_headers, "ZZZ Briefing Late Cashier", "8802")
    _roster(client, owner_headers, staff, start="09:00", end="17:00")
    _insert_timecard(staff, time(9, 12), time(17, 0))  # 12 min late, 5 min grace

    r = req(client, "GET", "/api/preshift/briefing", headers=owner_headers)
    assert r.status_code == 200, r.text
    entry = next(s for s in r.json()["onShift"] if s["staffId"] == staff["id"])
    assert entry["scheduledStart"] == "09:00"
    assert entry["scheduledEnd"] == "17:00"
    assert entry["clockIn"] is not None
    assert entry["clockOut"] is not None
    assert entry["lateMinutes"] == 12
    assert entry["onTime"] is False

    staff_headers = _staff_headers(client, staff)
    r2 = req(client, "GET", "/api/preshift/briefing", headers=staff_headers)
    entry2 = next(s for s in r2.json()["onShift"] if s["staffId"] == staff["id"])
    assert "clockIn" not in entry2
    assert "lateMinutes" not in entry2


def test_preshift_briefing_on_time_within_grace_window(client, owner_headers):
    staff = _add_staff(client, owner_headers, "ZZZ Briefing OnTime Cashier", "8803")
    _roster(client, owner_headers, staff, start="09:00", end="17:00")
    _insert_timecard(staff, time(9, 3), time(17, 0))  # 3 min late, inside 5 min grace

    r = req(client, "GET", "/api/preshift/briefing", headers=owner_headers)
    entry = next(s for s in r.json()["onShift"] if s["staffId"] == staff["id"])
    assert entry["lateMinutes"] == 3
    assert entry["onTime"] is True


def test_preshift_briefing_includes_walkin_clockins_without_a_roster_entry(client, owner_headers):
    staff = _add_staff(client, owner_headers, "ZZZ Briefing Walkin Cashier", "8804")
    _insert_timecard(staff, time(10, 0), None)

    r = req(client, "GET", "/api/preshift/briefing", headers=owner_headers)
    entry = next(s for s in r.json()["onShift"] if s["staffId"] == staff["id"])
    assert entry["scheduledStart"] is None
    assert entry["clockIn"] is not None
    assert entry["clockOut"] is None


def test_leaderboard_computes_punctuality_bonus_for_matched_shifts(client, owner_headers):
    staff = _add_staff(client, owner_headers, "ZZZ Leaderboard Punctual Cashier", "8805")
    _roster(client, owner_headers, staff, start="09:00", end="17:00")
    _insert_timecard(staff, time(9, 0), time(17, 0))  # exactly on time

    r = req(client, "GET", "/api/staff/leaderboard", headers=owner_headers)
    assert r.status_code == 200, r.text
    entry = next(s for s in r.json()["leaderboard"] if s["id"] == staff["id"])
    assert entry["shiftsTracked"] == 1
    assert entry["punctualityRate"] == 1.0
    assert entry["avgLateMinutes"] == 0.0


def test_leaderboard_is_neutral_for_staff_with_no_rostered_history(client, owner_headers):
    staff = _add_staff(client, owner_headers, "ZZZ Leaderboard Norostered Cashier", "8806")
    _insert_timecard(staff, time(9, 0), time(17, 0))  # completed shift, but never rostered

    r = req(client, "GET", "/api/staff/leaderboard", headers=owner_headers)
    entry = next(s for s in r.json()["leaderboard"] if s["id"] == staff["id"])
    assert entry["shiftsTracked"] == 0
    assert entry["punctualityRate"] is None
