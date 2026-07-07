"""
Iteration 46 backend regression tests.

Covers:
  - mongo_safe refactor regressions (GET /api/locations, GET /api/customers)
  - Native Apple Wallet .pkpass generation
  - Google Wallet save-to-phone JWT link
  - Marketing analytics endpoint (bookingsBySource, scansByType)
  - Channels state pause/resume/schedule + RBAC enforcement
"""
import io
import os
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")

OWNER_EMAIL = "owner@nuva.com"
OWNER_PASS = "NuvaOwner2026!"


# ─────────────────────────── fixtures ───────────────────────────
@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASS}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"no token in login response: {r.json()}"
    return tok


@pytest.fixture(scope="module")
def owner_client(owner_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def any_customer_id(owner_client):
    r = owner_client.get(f"{BASE_URL}/api/customers", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if not data:
        # seed a test customer
        cr = owner_client.post(f"{BASE_URL}/api/customers", json={
            "name": "TEST_iter46 Wallet", "email": "TEST_iter46@example.com", "phone": "+61400000046",
        }, timeout=15)
        assert cr.status_code in (200, 201), f"customer create failed: {cr.status_code} {cr.text}"
        return cr.json()["id"]
    return data[0]["id"]


# ─────────────────────── mongo_safe regressions ───────────────────────
class TestMongoSafeRefactor:
    def test_locations_list_still_ok(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/locations", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list), f"expected list, got {type(data)}"
        # locations shape should be preserved
        if data:
            row = data[0]
            assert "id" in row
            assert "name" in row

    def test_customers_list_still_ok(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/customers", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        if data:
            c = data[0]
            assert "id" in c


# ────────────────────────── wallet passes ──────────────────────────
class TestApplePkpass:
    def test_pkpass_returns_valid_zip(self, owner_client, any_customer_id):
        r = owner_client.get(f"{BASE_URL}/api/customers/{any_customer_id}/wallet/apple.pkpass", timeout=20)
        assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
        # Content-Type
        ctype = r.headers.get("content-type", "")
        assert "vnd.apple.pkpass" in ctype, f"unexpected content-type: {ctype}"
        # signed header present
        assert "X-Pkpass-Signed" in r.headers, f"missing X-Pkpass-Signed header, got headers: {list(r.headers.keys())}"
        # In this preview env certs are not configured — expect false
        assert r.headers["X-Pkpass-Signed"] in ("false", "true")
        # Content is a zip with pass.json + manifest.json + icon.png
        blob = r.content
        assert len(blob) > 200, f"pkpass too small: {len(blob)} bytes"
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            names = z.namelist()
            assert "pass.json" in names, f"missing pass.json in {names}"
            assert "manifest.json" in names, f"missing manifest.json in {names}"
            assert "icon.png" in names, f"missing icon.png in {names}"


class TestGoogleWallet:
    def test_google_wallet_link_shape(self, owner_client, any_customer_id):
        r = owner_client.get(f"{BASE_URL}/api/customers/{any_customer_id}/wallet/google", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("url", "jwt", "signed", "classId", "objectId"):
            assert key in data, f"missing {key} in {data}"
        assert data["url"].startswith("https://pay.google.com/gp/v/save/"), data["url"]
        # signed will be false in preview env
        assert isinstance(data["signed"], bool)
        assert isinstance(data["jwt"], str) and len(data["jwt"]) > 20
        assert data["classId"] and data["objectId"]


# ───────────────────────── marketing analytics ─────────────────────────
class TestMarketingAnalytics:
    def test_analytics_shape(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/marketing/analytics?days=30", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("totalScans", "totalBookings", "bookingsBySource", "scansByType"):
            assert key in data, f"missing {key} in analytics response"
        assert isinstance(data["totalScans"], int)
        assert isinstance(data["totalBookings"], int)
        assert isinstance(data["bookingsBySource"], dict)
        assert isinstance(data["scansByType"], dict)
        assert data.get("windowDays") == 30


# ─────────────────────────── channel state ───────────────────────────
class TestChannelState:
    def test_get_channel_state(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/channels/state", timeout=15)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_pause_and_resume(self, owner_client):
        # Pause
        pr = owner_client.post(f"{BASE_URL}/api/channels/state",
                                json={"channel": "TEST_iter46_channel", "action": "pause",
                                       "reason": "TEST_iter46 pause test"}, timeout=15)
        assert pr.status_code == 200, pr.text
        pdoc = pr.json()
        assert pdoc["channel"] == "TEST_iter46_channel"
        assert pdoc["status"] == "paused"

        # Verify persisted
        g = owner_client.get(f"{BASE_URL}/api/channels/state", timeout=15)
        assert g.status_code == 200
        rows = g.json()
        row = next((x for x in rows if x.get("channel") == "TEST_iter46_channel"), None)
        assert row is not None, "paused channel state not persisted"
        assert row["status"] == "paused"

        # Schedule
        sr = owner_client.post(f"{BASE_URL}/api/channels/state",
                                json={"channel": "TEST_iter46_channel", "action": "schedule",
                                       "pausedUntil": "2026-12-31T23:59:00Z"}, timeout=15)
        assert sr.status_code == 200, sr.text
        assert sr.json()["status"] == "paused"
        assert sr.json()["pausedUntil"] == "2026-12-31T23:59:00Z"

        # Resume
        rr = owner_client.post(f"{BASE_URL}/api/channels/state",
                                json={"channel": "TEST_iter46_channel", "action": "resume"}, timeout=15)
        assert rr.status_code == 200
        assert rr.json()["status"] == "active"

    def test_invalid_action_400(self, owner_client):
        r = owner_client.post(f"{BASE_URL}/api/channels/state",
                              json={"channel": "TEST_iter46_channel", "action": "explode"}, timeout=15)
        assert r.status_code == 400

    def test_rbac_forbidden_for_non_owner(self):
        # login as cashier
        lr = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"email": "cashier@nuva.com", "password": "Staff2026!"}, timeout=15)
        if lr.status_code != 200:
            pytest.skip(f"cashier login failed: {lr.status_code}")
        tok = lr.json().get("token") or lr.json().get("access_token")
        assert tok
        r = requests.post(f"{BASE_URL}/api/channels/state",
                          json={"channel": "TEST_iter46_channel", "action": "pause"},
                          headers={"Authorization": f"Bearer {tok}"}, timeout=15)
        assert r.status_code == 403, f"expected 403 for cashier, got {r.status_code} {r.text}"
