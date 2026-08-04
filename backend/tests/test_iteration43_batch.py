"""
Iteration 43 backend tests:
  - Superannuation (Fair Work) endpoints
  - Temperature monitoring (device registry, ingest, alerts, reports)
  - Table Courses (settings, states, send nudge)
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
OWNER_EMAIL = "owner@nua.com"
OWNER_PW = "NuaOwner2026!"


@pytest.fixture(scope="session")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PW}, timeout=30)
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text}"
    return r.json().get("token") or r.json().get("access_token")


@pytest.fixture(scope="session")
def owner_client(owner_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"})
    return s


# ─── Superannuation ──────────────────────────────────────────────────────
class TestSuper:
    def test_rate_after_2025_07_01_is_12(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/super/rate?payDate=2025-07-05", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["rate"] == 12.0
        assert d["source"] == "fair_work_commission"
        assert isinstance(d["tiers"], list) and len(d["tiers"]) >= 4

    def test_rate_default_payDate(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/super/rate", timeout=15)
        assert r.status_code == 200
        assert r.json()["source"] == "fair_work_commission"

    def test_calc_uses_tier_rate(self, owner_client):
        r = owner_client.post(f"{BASE_URL}/api/super/calc", json={
            "payPeriodStart": "2025-07-01", "payPeriodEnd": "2025-07-07", "payDate": "2025-07-08",
            "staff": [{"name": "TEST_Emp1", "grossPay": 2400.0},
                      {"name": "TEST_Emp2", "grossPay": 1000.0}],
        }, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["rate"] == 12.0
        assert d["totalSuper"] == round(2400*0.12 + 1000*0.12, 2)
        assert len(d["employees"]) == 2

    def test_calc_with_override(self, owner_client):
        r = owner_client.post(f"{BASE_URL}/api/super/calc", json={
            "payPeriodStart": "2025-07-01", "payPeriodEnd": "2025-07-07", "payDate": "2025-07-08",
            "staff": [{"name": "TEST_Override", "grossPay": 1000.0}],
            "rate": 15.0,
        }, timeout=15)
        assert r.status_code == 200
        assert r.json()["rate"] == 15.0
        assert r.json()["totalSuper"] == 150.0

    def test_weekly_run_commit_and_list_and_paid(self, owner_client):
        payload = {
            "payPeriodStart": "2025-07-01", "payPeriodEnd": "2025-07-07", "payDate": "2025-07-08",
            "staff": [{"name": "TEST_Weekly", "grossPay": 2000.0}],
            "note": "TEST_run"
        }
        r = owner_client.post(f"{BASE_URL}/api/super/weekly-runs", json=payload, timeout=15)
        assert r.status_code == 200
        run = r.json()
        assert run["status"] == "unpaid"
        assert "id" in run
        run_id = run["id"]

        # list
        r2 = owner_client.get(f"{BASE_URL}/api/super/weekly-runs", timeout=15)
        assert r2.status_code == 200
        assert any(x["id"] == run_id for x in r2.json())

        # mark paid
        r3 = owner_client.patch(f"{BASE_URL}/api/super/weekly-runs/{run_id}",
                                json={"status": "paid"}, timeout=15)
        assert r3.status_code == 200
        assert r3.json()["status"] == "paid"

    def test_bas_line(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/super/bas-line",
                             params={"quarterStart": "2025-07-01", "quarterEnd": "2025-09-30"},
                             timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "totalSuper" in d and "totalSuperPaid" in d and "reportingDueBy" in d
        # 28 days after Sep 30 => Oct 28
        assert d["reportingDueBy"] == "2025-10-28"

    def test_summary_returns_4_quarters(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/super/summary?fy=2025-2026", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert len(d["quarters"]) == 4
        assert d["fy"] == "2025-2026"


# ─── Temperature ─────────────────────────────────────────────────────────
class TestTemperature:
    _device_id = None
    _secret = None

    def test_brands(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/temperature/brands", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert len(d["brands"]) >= 13
        keys = {b["key"] for b in d["brands"]}
        for k in ["sensorpush", "govee", "inkbird", "thermopro", "monnit",
                  "cooper_atkins", "hobo_onset", "lacrosse", "ambient_weather",
                  "wireless_tag", "sensaphone", "generic", "manual"]:
            assert k in keys, f"Missing brand {k}"
        assert "fridge" in d["defaultRanges"]

    def test_create_device_returns_secret(self, owner_client):
        r = owner_client.post(f"{BASE_URL}/api/temperature/devices", json={
            "name": f"TEST_Fridge_{uuid.uuid4().hex[:6]}",
            "unitType": "fridge", "brand": "sensorpush",
            "connectivity": "bluetooth",
        }, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "ingestSecret" in d and d["ingestSecret"]
        assert d["minC"] == 1.0 and d["maxC"] == 5.0
        TestTemperature._device_id = d["id"]
        TestTemperature._secret = d["ingestSecret"]

    def test_list_devices_strips_secret(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/temperature/devices", timeout=15)
        assert r.status_code == 200
        for dev in r.json():
            assert "ingestSecret" not in dev

    def test_ingest_wrong_secret_401(self):
        r = requests.post(f"{BASE_URL}/api/temperature/ingest", json={
            "deviceId": TestTemperature._device_id, "ingestSecret": "wrong",
            "temperatureC": 3.5,
        }, timeout=15)
        assert r.status_code == 401

    def test_ingest_correct_secret_persists(self):
        r = requests.post(f"{BASE_URL}/api/temperature/ingest", json={
            "deviceId": TestTemperature._device_id, "ingestSecret": TestTemperature._secret,
            "temperatureC": 3.5,
        }, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "normal"

    def test_manual_reading_and_abnormal_creates_alert(self, owner_client):
        r = owner_client.post(f"{BASE_URL}/api/temperature/readings", json={
            "deviceId": TestTemperature._device_id, "temperatureC": 12.0, "source": "manual",
        }, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "abnormal_high"

        # Alerts should include one for our device
        r2 = owner_client.get(f"{BASE_URL}/api/temperature/alerts", timeout=15)
        assert r2.status_code == 200
        matching = [a for a in r2.json() if a["deviceId"] == TestTemperature._device_id]
        assert len(matching) >= 1
        alert_id = matching[0]["id"]
        r3 = owner_client.post(f"{BASE_URL}/api/temperature/alerts/{alert_id}/acknowledge", timeout=15)
        assert r3.status_code == 200
        assert r3.json()["acknowledged"] is True

    def test_weekly_report(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/temperature/report?period=weekly", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["range"]["period"] == "weekly"
        assert "devices" in d and "readings" in d

    def test_monthly_and_yearly_and_custom_report(self, owner_client):
        for p in ("monthly", "yearly"):
            r = owner_client.get(f"{BASE_URL}/api/temperature/report?period={p}", timeout=20)
            assert r.status_code == 200
            assert r.json()["range"]["period"] == p
        r = owner_client.get(f"{BASE_URL}/api/temperature/report",
                             params={"start": "2025-01-01", "end": "2026-12-31"}, timeout=20)
        assert r.status_code == 200
        assert r.json()["range"]["period"] == "custom"

    def test_scan_missing(self, owner_client):
        r = owner_client.post(f"{BASE_URL}/api/temperature/scan-missing", timeout=20)
        assert r.status_code == 200
        assert "remindersCreated" in r.json()

    def test_rotate_secret(self, owner_client):
        r = owner_client.post(
            f"{BASE_URL}/api/temperature/devices/{TestTemperature._device_id}/rotate-secret", timeout=15)
        assert r.status_code == 200
        new_secret = r.json()["ingestSecret"]
        assert new_secret and new_secret != TestTemperature._secret

    def test_delete_device(self, owner_client):
        r = owner_client.delete(
            f"{BASE_URL}/api/temperature/devices/{TestTemperature._device_id}", timeout=15)
        assert r.status_code == 200


# ─── Table Courses ───────────────────────────────────────────────────────
class TestTableCourses:
    def test_default_settings(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/table-courses/settings", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert len(d["courses"]) == 7
        keys = [c["key"] for c in d["courses"]]
        for k in ["seated", "drinks", "entree", "main", "dessert", "coffee", "check"]:
            assert k in keys
        assert d["overdueColour"]

    def test_update_settings_owner(self, owner_client):
        # get, modify one label, put back
        current = owner_client.get(f"{BASE_URL}/api/table-courses/settings", timeout=15).json()
        courses = current["courses"]
        r = owner_client.put(f"{BASE_URL}/api/table-courses/settings", json={
            "courses": courses, "overdueColour": "#7F1D1D", "autoAdvance": False,
        }, timeout=15)
        assert r.status_code == 200

    def test_seat_table_and_states(self, owner_client):
        table_id = f"TEST_T_{uuid.uuid4().hex[:6]}"
        r = owner_client.post(f"{BASE_URL}/api/table-courses/states", json={
            "tableId": table_id, "course": "drinks", "partySize": 4,
        }, timeout=15)
        assert r.status_code == 200
        assert r.json()["course"] == "drinks"

        r2 = owner_client.get(f"{BASE_URL}/api/table-courses/states", timeout=15)
        assert r2.status_code == 200
        body = r2.json()
        found = [s for s in body["states"] if s["tableId"] == table_id]
        assert len(found) == 1
        st = found[0]
        assert "colour" in st and "dwellMinutes" in st and "courseMinutes" in st
        assert st["courseLabel"] in ("Drinks", "drinks")

        # send nudge
        r3 = owner_client.post(f"{BASE_URL}/api/table-courses/send", json={
            "tableId": table_id, "message": "TEST_check", "priority": "urgent",
        }, timeout=15)
        assert r3.status_code == 200
        assert r3.json()["type"] == "table_nudge"

        # clear
        r4 = owner_client.post(f"{BASE_URL}/api/table-courses/states", json={
            "tableId": table_id, "clearState": True,
        }, timeout=15)
        assert r4.status_code == 200
        assert r4.json()["cleared"] is True
