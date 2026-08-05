"""Iteration 45 finalization batch — supplements iteration 44.

Focus:
  - GET /api/locations MUST NOT 500 even with legacy MongoDB docs
    that have malformed/legacy `timings` and missing required fields.
  - 'A Social' (seed) must be present in the response.
  - Extended fields on POST /api/locations (logoUrl, website,
    gmbPlaceId, hours dict).
  - Wallet endpoints (customer wallet + lookup-by-token roundtrip).
  - Automation triggers CRUD + AI suggest.
  - GMB sync with/without place id.
"""
import os
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@nua.com"
OWNER_PASS = "NuaOwner2026!"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture(scope="session")
def owner_headers():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASS},
        timeout=15,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    if not tok:
        pytest.skip("no token in login response")
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def mongo_db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


# ─────────────────────────────────────────────────────────────
# Locations defensive read
# ─────────────────────────────────────────────────────────────
class TestLocationsDefensiveRead:
    """Locations GET must handle malformed legacy docs gracefully."""

    def test_baseline_get_locations_200(self, owner_headers):
        r = requests.get(f"{API}/locations", headers=owner_headers, timeout=10)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_seed_a_social_present(self, owner_headers):
        r = requests.get(f"{API}/locations", headers=owner_headers, timeout=10)
        assert r.status_code == 200
        names = [x.get("name") for x in r.json()]
        assert "A Social" in names, f"'A Social' seed missing, got: {names}"

    def test_legacy_malformed_doc_does_not_crash(self, owner_headers, mongo_db):
        """Insert a legacy doc with (a) `timings` as legacy alias for `hours`,
        (b) `hours` as a non-dict string that would normally break Pydantic.
        GET should still return 200 and skip/coerce the bad row."""
        bad_id = "TEST_iter45_legacy"
        try:
            mongo_db.locations.delete_one({"id": bad_id})
            mongo_db.locations.insert_one({
                "id": bad_id,
                "name": "TEST_iter45 legacy shop",
                # missing address & phone entirely
                "hours": "9-5 mon-fri",          # legacy free-text
                "timings": {"mon": {"open": "09:00", "close": "17:00", "closed": False}},
            })
            r = requests.get(f"{API}/locations", headers=owner_headers, timeout=10)
            assert r.status_code == 200, f"GET /locations 500'd on legacy doc: {r.text}"
            locs = r.json()
            # The legacy row must appear (via safe fallback) or at least NOT
            # break the whole list. `A Social` still visible confirms fallback.
            names = [x.get("name") for x in locs]
            assert "A Social" in names
        finally:
            mongo_db.locations.delete_one({"id": bad_id})

    def test_legacy_timings_coerced_to_hours(self, owner_headers, mongo_db):
        """When a doc has ONLY `timings` (no `hours`) as a dict, GET should
        coerce it to `hours` in the response."""
        tid = "TEST_iter45_timings"
        try:
            mongo_db.locations.delete_one({"id": tid})
            mongo_db.locations.insert_one({
                "id": tid,
                "name": "TEST_iter45 timings",
                "address": "1 Legacy Ln",
                "phone": "+61400000045",
                "status": "active",
                "timings": {"tue": {"open": "10:00", "close": "22:00", "closed": False}},
            })
            r = requests.get(f"{API}/locations", headers=owner_headers, timeout=10)
            assert r.status_code == 200
            me = next((x for x in r.json() if x.get("id") == tid), None)
            assert me, "legacy row missing"
            # hours should now show tue slot (coerced from timings)
            hrs = me.get("hours") or {}
            assert isinstance(hrs, dict) and "tue" in hrs, f"hours not coerced: {hrs}"
        finally:
            mongo_db.locations.delete_one({"id": tid})


# ─────────────────────────────────────────────────────────────
# POST /api/locations with extended fields
# ─────────────────────────────────────────────────────────────
class TestLocationCreateExtended:
    def test_create_with_all_extended(self, owner_headers):
        payload = {
            "name": "TEST_iter45 extended",
            "address": "42 Extended Ave",
            "phone": "+61400000045",
            "email": "ext@test.com",
            "website": "https://ext.test",
            "logoUrl": "https://cdn.test/ext-logo.png",
            "timezone": "Australia/Melbourne",
            "hours": {
                "mon": {"open": "08:00", "close": "20:00", "closed": False},
                "sun": {"open": "10:00", "close": "16:00", "closed": False},
            },
            "gmbPlaceId": "ChIJ_ext_iter45",
        }
        r = requests.post(f"{API}/locations", json=payload,
                          headers=owner_headers, timeout=10)
        assert r.status_code in (200, 201), r.text
        created = r.json()
        assert created["email"] == "ext@test.com"
        assert created["website"] == "https://ext.test"
        assert created["logoUrl"] == "https://cdn.test/ext-logo.png"
        assert created["gmbPlaceId"] == "ChIJ_ext_iter45"
        assert isinstance(created.get("hours"), dict)
        loc_id = created["id"]

        # GET verification
        rl = requests.get(f"{API}/locations", headers=owner_headers, timeout=10).json()
        me = next((x for x in rl if x["id"] == loc_id), None)
        assert me and me["logoUrl"] == "https://cdn.test/ext-logo.png"

        # cleanup
        requests.delete(f"{API}/locations/{loc_id}",
                        headers=owner_headers, timeout=10)


# ─────────────────────────────────────────────────────────────
# GMB Sync
# ─────────────────────────────────────────────────────────────
class TestGMBSync:
    @pytest.fixture(scope="class")
    def a_location_id(self, owner_headers):
        r = requests.get(f"{API}/locations",
                         headers={"Authorization": owner_headers["Authorization"]},
                         timeout=10)
        assert r.status_code == 200
        return r.json()[0]["id"]

    def test_gmb_sync_with_place_id(self, owner_headers, a_location_id):
        requests.put(f"{API}/locations/{a_location_id}",
                     json={"gmbPlaceId": "ChIJ_TEST_iter45"},
                     headers=owner_headers, timeout=10)
        r = requests.post(f"{API}/locations/{a_location_id}/gmb-sync",
                          headers=owner_headers, timeout=10)
        assert r.status_code == 200
        assert "syncedAt" in r.json()

    def test_gmb_sync_without_place_id_400(self, owner_headers, a_location_id):
        requests.put(f"{API}/locations/{a_location_id}",
                     json={"gmbPlaceId": None},
                     headers=owner_headers, timeout=10)
        r = requests.post(f"{API}/locations/{a_location_id}/gmb-sync",
                          headers=owner_headers, timeout=10)
        assert r.status_code == 400
        # restore for downstream tests
        requests.put(f"{API}/locations/{a_location_id}",
                     json={"gmbPlaceId": "ChIJ_TEST_iter45"},
                     headers=owner_headers, timeout=10)


# ─────────────────────────────────────────────────────────────
# Customer Wallet
# ─────────────────────────────────────────────────────────────
class TestCustomerWallet:
    @pytest.fixture(scope="class")
    def a_customer_id(self, owner_headers):
        r = requests.get(f"{API}/customers", headers=owner_headers, timeout=10)
        items = r.json() if r.status_code == 200 else []
        if items:
            return items[0]["id"]
        c = requests.post(
            f"{API}/customers",
            json={"name": "TEST_iter45 c", "email": "iter45c@test.com",
                  "phone": "+61400000045"},
            headers=owner_headers, timeout=10)
        assert c.status_code in (200, 201), c.text
        return c.json()["id"]

    def test_wallet_shape(self, owner_headers, a_customer_id):
        r = requests.get(f"{API}/customers/{a_customer_id}/wallet",
                         headers=owner_headers, timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("customerId", "name", "tier", "points",
                  "storeCredit", "barcode", "qrToken", "walletDataUrl"):
            assert k in d, f"wallet missing key: {k}"
        assert d["customerId"] == a_customer_id
        assert d["walletDataUrl"].startswith("data:text/plain;base64,")

    def test_lookup_valid_token(self, owner_headers, a_customer_id):
        w = requests.get(f"{API}/customers/{a_customer_id}/wallet",
                         headers=owner_headers, timeout=10).json()
        r = requests.post(f"{API}/customers/lookup-by-token",
                          json={"token": w["qrToken"]},
                          headers=owner_headers, timeout=10)
        assert r.status_code == 200
        assert r.json().get("id") == a_customer_id

    def test_lookup_bad_token_400_or_401(self, owner_headers):
        r = requests.post(f"{API}/customers/lookup-by-token",
                          json={"token": "corrupt.xyz"},
                          headers=owner_headers, timeout=10)
        assert r.status_code in (400, 401)


# ─────────────────────────────────────────────────────────────
# Automation triggers
# ─────────────────────────────────────────────────────────────
class TestAutomationTriggers:
    def test_full_crud(self, owner_headers):
        # CREATE
        r = requests.post(
            f"{API}/automations/triggers",
            json={"name": "TEST_iter45 trigger",
                  "event": "low_stock",
                  "conditions": {"threshold": 4},
                  "actions": [{"type": "dock_notify",
                               "params": {"message": "hi 45"}}]},
            headers=owner_headers, timeout=10)
        assert r.status_code == 200, r.text
        tid = r.json()["id"]
        assert r.json()["active"] is True

        # LIST includes it
        r2 = requests.get(f"{API}/automations/triggers",
                          headers=owner_headers, timeout=10)
        assert r2.status_code == 200
        assert any(t["id"] == tid for t in r2.json())

        # TOGGLE active off
        r3 = requests.patch(f"{API}/automations/triggers/{tid}",
                            json={"active": False},
                            headers=owner_headers, timeout=10)
        assert r3.status_code == 200
        assert r3.json()["active"] is False

        # DELETE
        r4 = requests.delete(f"{API}/automations/triggers/{tid}",
                             headers=owner_headers, timeout=10)
        assert r4.status_code == 200

        # Second delete → 404
        r5 = requests.delete(f"{API}/automations/triggers/{tid}",
                             headers=owner_headers, timeout=10)
        assert r5.status_code == 404

    def test_ai_suggest_returns_shape(self, owner_headers):
        r = requests.post(f"{API}/automations/ai-suggest",
                          json={"prompt": "notify chef when a bottle drops below 3"},
                          headers=owner_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("name", "event", "conditions", "actions",
                  "aiGenerated", "aiPrompt"):
            assert k in d
        assert isinstance(d["actions"], list) and len(d["actions"]) >= 1

    def test_ai_suggest_empty_prompt_400(self, owner_headers):
        r = requests.post(f"{API}/automations/ai-suggest",
                          json={"prompt": ""},
                          headers=owner_headers, timeout=10)
        assert r.status_code == 400
