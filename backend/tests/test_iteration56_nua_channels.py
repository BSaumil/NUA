"""
Iteration 56 — NUA namespace refactor + Channel schedule tests.

Coverage:
  * NUA native routes (/api/nua/*) return 200 with valid data
  * /api/ash/* backwards-compat alias still returns 200 (via NuaAliasMiddleware)
  * Channel schedule save & load persists (POST /api/channels/{c}/schedule)
  * Channel schedule RBAC (cashier gets 403)
  * Channel effective-status computes openNow from schedule
  * Existing pause/resume flow still works
"""
import os
import time
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER = {"email": "owner@nua.com", "password": "NuaOwner2026!"}
CASHIER = {"email": "cashier@nua.com", "password": "Staff2026!"}


def _login(session: requests.Session, creds: dict) -> str:
    r = session.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text[:200]}"
    body = r.json()
    return body.get("token") or body.get("access_token")


@pytest.fixture(scope="module")
def owner_client():
    s = requests.Session()
    s.headers["Content-Type"] = "application/json"
    tok = _login(s, OWNER)
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def cashier_client():
    s = requests.Session()
    s.headers["Content-Type"] = "application/json"
    try:
        tok = _login(s, CASHIER)
    except AssertionError:
        pytest.skip("Cashier account unavailable")
    s.headers["Authorization"] = f"Bearer {tok}"
    return s


# ============================================================
# NUA namespace — native routes
# ============================================================
class TestNuaNativeRoutes:
    def test_tools(self, owner_client):
        r = owner_client.get(f"{API}/nua/tools", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data, list) and len(data) > 0
        # Each tool must have permission info
        for t in data[:3]:
            assert "name" in t and "effectivePermission" in t

    def test_personas(self, owner_client):
        r = owner_client.get(f"{API}/nua/personas", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data, list) and len(data) >= 6
        ids = {p.get("id") for p in data}
        assert {"executive", "finance", "ops", "hr", "marketing", "guest"}.issubset(ids)

    def test_briefing(self, owner_client):
        r = owner_client.get(f"{API}/nua/briefing", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        # Briefing should be an object (either fresh or cached)
        assert isinstance(data, dict)

    def test_health_score(self, owner_client):
        r = owner_client.get(f"{API}/nua/health-score", timeout=30)
        assert r.status_code == 200, r.text[:300]

    def test_scheduler_status(self, owner_client):
        r = owner_client.get(f"{API}/nua/scheduler/status", timeout=30)
        assert r.status_code == 200, r.text[:300]

    def test_agent_post(self, owner_client):
        r = owner_client.post(f"{API}/nua/agent",
                              json={"message": "What tools do you have?"},
                              timeout=90)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "reply" in data
        assert isinstance(data["reply"], str) and len(data["reply"]) > 0


# ============================================================
# /api/ash/* alias — backwards-compat
# ============================================================
class TestAshAlias:
    def test_alias_tools(self, owner_client):
        r = owner_client.get(f"{API}/ash/tools", timeout=30)
        assert r.status_code == 200, f"ash alias broken: {r.status_code} {r.text[:200]}"
        assert isinstance(r.json(), list)

    def test_alias_personas(self, owner_client):
        r = owner_client.get(f"{API}/ash/personas", timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert isinstance(r.json(), list)

    def test_alias_briefing(self, owner_client):
        r = owner_client.get(f"{API}/ash/briefing", timeout=60)
        assert r.status_code == 200, r.text[:300]

    def test_alias_health_score(self, owner_client):
        r = owner_client.get(f"{API}/ash/health-score", timeout=30)
        assert r.status_code == 200, r.text[:300]


# ============================================================
# Channel schedule endpoints
# ============================================================
CHANNEL = "TEST_website"


class TestChannelSchedule:
    def test_get_default_schedule(self, owner_client):
        r = owner_client.get(f"{API}/channels/{CHANNEL}/schedule", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["channel"] == CHANNEL
        assert "enabled" in data and "mode" in data
        assert "simpleHours" in data and "weeklyHours" in data

    def test_save_simple_schedule_and_persist(self, owner_client):
        payload = {
            "enabled": True,
            "mode": "simple",
            "simpleHours": {"open": "11:00", "close": "22:00", "closed": False},
            "weeklyHours": None,
            "overrides": [],
        }
        r = owner_client.post(f"{API}/channels/{CHANNEL}/schedule", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:300]
        saved = r.json()
        assert saved["enabled"] is True
        assert saved["mode"] == "simple"
        assert saved["simpleHours"]["open"] == "11:00"
        assert saved["simpleHours"]["close"] == "22:00"

        # Verify persistence via GET
        r2 = owner_client.get(f"{API}/channels/{CHANNEL}/schedule", timeout=30)
        assert r2.status_code == 200
        got = r2.json()
        assert got["enabled"] is True
        assert got["mode"] == "simple"
        assert got["simpleHours"]["open"] == "11:00"

    def test_save_weekly_schedule_with_overrides(self, owner_client):
        override_date = (datetime.now(timezone.utc).date() + timedelta(days=7)).isoformat()
        payload = {
            "enabled": True,
            "mode": "weekly",
            "simpleHours": {"open": "09:00", "close": "22:00", "closed": False},
            "weeklyHours": {
                "mon": {"open": "10:00", "close": "20:00", "closed": False},
                "tue": {"open": "10:00", "close": "20:00", "closed": False},
                "wed": {"open": "10:00", "close": "20:00", "closed": False},
                "thu": {"open": "10:00", "close": "20:00", "closed": False},
                "fri": {"open": "10:00", "close": "23:00", "closed": False},
                "sat": {"open": "11:00", "close": "23:00", "closed": False},
                "sun": {"open": "00:00", "close": "00:00", "closed": True},
            },
            "overrides": [
                {"date": override_date, "closed": True, "reason": "Public holiday"},
            ],
        }
        r = owner_client.post(f"{API}/channels/{CHANNEL}/schedule", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:300]
        saved = r.json()
        assert saved["mode"] == "weekly"
        assert saved["weeklyHours"]["sun"]["closed"] is True
        assert len(saved["overrides"]) == 1
        assert saved["overrides"][0]["date"] == override_date

        # Verify persistence
        r2 = owner_client.get(f"{API}/channels/{CHANNEL}/schedule", timeout=30)
        got = r2.json()
        assert got["mode"] == "weekly"
        assert got["weeklyHours"]["fri"]["close"] == "23:00"
        assert len(got["overrides"]) == 1

    def test_cashier_forbidden(self, cashier_client):
        payload = {"enabled": False, "mode": "simple",
                    "simpleHours": {"open": "09:00", "close": "22:00", "closed": False},
                    "weeklyHours": None, "overrides": []}
        r = cashier_client.post(f"{API}/channels/{CHANNEL}/schedule", json=payload, timeout=30)
        assert r.status_code == 403, f"Expected 403 for cashier, got {r.status_code}: {r.text[:200]}"

    def test_invalid_mode_rejected(self, owner_client):
        r = owner_client.post(f"{API}/channels/{CHANNEL}/schedule",
                              json={"enabled": True, "mode": "bogus"}, timeout=30)
        assert r.status_code == 400


# ============================================================
# Channel effective-status
# ============================================================
class TestChannelEffectiveStatus:
    def test_effective_status_shape(self, owner_client):
        # First save an always-open schedule so openNow reliably returns isOpen=True
        payload = {
            "enabled": True,
            "mode": "simple",
            "simpleHours": {"open": "00:00", "close": "23:59", "closed": False},
            "weeklyHours": None,
            "overrides": [],
        }
        owner_client.post(f"{API}/channels/{CHANNEL}/schedule", json=payload, timeout=30)

        # Ensure not paused
        owner_client.post(f"{API}/channels/state",
                          json={"channel": CHANNEL, "action": "resume"}, timeout=30)

        r = owner_client.get(f"{API}/channels/{CHANNEL}/effective-status", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["channel"] == CHANNEL
        assert "state" in data and "schedule" in data
        assert "openNow" in data and isinstance(data["openNow"], dict)
        assert "isOpen" in data["openNow"] and "reason" in data["openNow"]
        assert data["effective"] in ("active", "paused")
        # With 00:00-23:59 hours, should be open
        assert data["openNow"]["isOpen"] is True
        assert data["effective"] == "active"

    def test_effective_status_closed_when_outside_hours(self, owner_client):
        # Set very narrow closed-hours window that's guaranteed outside current UTC time
        now = datetime.now(timezone.utc)
        # Set a window that starts and ends within a single already-past minute
        # A schedule of 00:00–00:01 will only be open in the first minute of UTC day
        payload = {
            "enabled": True,
            "mode": "simple",
            "simpleHours": {"open": "00:00", "close": "00:01", "closed": False},
            "weeklyHours": None,
            "overrides": [],
        }
        # If current time is 00:00 UTC, this test would be flaky — skip in that case
        if now.hour == 0 and now.minute == 0:
            pytest.skip("Skipping — current UTC minute is inside the tiny test window")
        owner_client.post(f"{API}/channels/{CHANNEL}/schedule", json=payload, timeout=30)
        owner_client.post(f"{API}/channels/state",
                          json={"channel": CHANNEL, "action": "resume"}, timeout=30)

        r = owner_client.get(f"{API}/channels/{CHANNEL}/effective-status", timeout=30)
        data = r.json()
        assert data["openNow"]["isOpen"] is False
        assert data["effective"] == "paused"  # Schedule closed → effective is paused


# ============================================================
# Channel pause/resume flow
# ============================================================
class TestChannelPauseResume:
    def test_pause_and_resume(self, owner_client):
        # Pause
        r = owner_client.post(f"{API}/channels/state",
                              json={"channel": CHANNEL, "action": "pause",
                                    "reason": "TEST_kitchen_slammed"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["status"] == "paused"
        assert r.json()["reason"] == "TEST_kitchen_slammed"

        # Verify via GET states
        r2 = owner_client.get(f"{API}/channels/state", timeout=30)
        assert r2.status_code == 200
        rows = r2.json()
        found = next((x for x in rows if x["channel"] == CHANNEL), None)
        assert found is not None
        assert found["status"] == "paused"

        # Resume
        r3 = owner_client.post(f"{API}/channels/state",
                               json={"channel": CHANNEL, "action": "resume"}, timeout=30)
        assert r3.status_code == 200
        assert r3.json()["status"] == "active"

    def test_pause_action_validation(self, owner_client):
        r = owner_client.post(f"{API}/channels/state",
                              json={"channel": CHANNEL, "action": "invalid"}, timeout=30)
        assert r.status_code == 400

    def test_cashier_cannot_pause(self, cashier_client):
        r = cashier_client.post(f"{API}/channels/state",
                                 json={"channel": CHANNEL, "action": "pause"}, timeout=30)
        assert r.status_code == 403


# Cleanup — remove TEST_ channel doc at module teardown
@pytest.fixture(scope="module", autouse=True)
def _cleanup(owner_client):
    yield
    # Best-effort cleanup — set schedule disabled + resume
    try:
        owner_client.post(f"{API}/channels/state",
                          json={"channel": CHANNEL, "action": "resume"}, timeout=15)
    except Exception:
        pass
