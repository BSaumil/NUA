"""Iteration 44 finalization batch — backend API tests.

Covers:
  - Print Routing auto-heal
  - Pre-Shift briefing
  - Booking day-rules
  - Marketing promo QR + scan + analytics
  - Channel state
  - Customer wallet + lookup-by-token
  - Inventory low-stock PDF + AI Pantry PDF
  - Automation triggers CRUD + ai-suggest
  - Locations extended PUT + gmb-sync
  - v15 POS tabs with tableId/tableNumber persistence
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@nua.com"
OWNER_PASS = "NuaOwner2026!"


@pytest.fixture(scope="session")
def owner_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASS},
                      timeout=15)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    if not tok:
        pytest.skip("no token in login response")
    return tok


@pytest.fixture(scope="session")
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}",
            "Content-Type": "application/json"}


# ----- Print routing auto-heal -----
class TestPrintRouting:
    def test_get_config_returns_array_routes(self, owner_headers):
        r = requests.get(f"{API}/print-routing/config", headers=owner_headers, timeout=10)
        assert r.status_code == 200
        cfg = r.json()
        assert isinstance(cfg.get("routes"), list), f"routes is not list: {cfg}"
        assert "enabled" in cfg
        assert "defaultPrinter" in cfg

    def test_save_rejects_bad_shape(self, owner_headers):
        r = requests.post(f"{API}/print-routing/config",
                          json={"routes": {"kitchen": "Kitchen"}},
                          headers=owner_headers, timeout=10)
        assert r.status_code == 400


# ----- Pre-shift briefing -----
class TestPreShift:
    def test_briefing_shape(self, owner_headers):
        r = requests.get(f"{API}/preshift/briefing", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("outOfStock", "specials", "activePromotions",
                  "onShift", "onShiftCount", "upsells"):
            assert k in d, f"missing {k}"
        assert isinstance(d["upsells"], list)
        assert len(d["upsells"]) <= 10


# ----- Booking day-rules -----
class TestBookingDayRules:
    def test_returns_seven_rows(self, owner_headers):
        r = requests.get(f"{API}/bookings/day-rules", headers=owner_headers, timeout=10)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and len(rows) == 7
        assert sorted([row["weekday"] for row in rows]) == list(range(7))

    def test_put_updates_row(self, owner_headers):
        payload = {"weekday": 3, "open": True, "openTime": "11:00",
                   "closeTime": "23:00", "maxCovers": 80,
                   "slotMinutes": 15, "turnMinutes": 60,
                   "minPartySize": 2, "maxPartySize": 12,
                   "bookableSpecials": ["prod-1"],
                   "bookableExperienceIds": ["exp-1"],
                   "note": "TEST_ iter44"}
        r = requests.put(f"{API}/bookings/day-rules/3", json=payload,
                         headers=owner_headers, timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body["openTime"] == "11:00"
        assert body["bookableSpecials"] == ["prod-1"]
        # GET should reflect
        r2 = requests.get(f"{API}/bookings/day-rules", headers=owner_headers, timeout=10)
        wed = next((x for x in r2.json() if x["weekday"] == 3), None)
        assert wed and wed["openTime"] == "11:00"


# ----- Marketing -----
class TestMarketing:
    def test_promo_qr_signed(self, owner_headers):
        r = requests.get(f"{API}/marketing/promo-qr",
                         params={"type": "voucher", "id": "V-TEST", "campaign": "iter44"},
                         headers=owner_headers, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "token" in d and "." in d["token"]
        assert d["payload"]["t"] == "voucher"
        assert d["payload"]["id"] == "V-TEST"

    def test_promo_qr_bad_type(self, owner_headers):
        r = requests.get(f"{API}/marketing/promo-qr",
                         params={"type": "not_valid", "id": "x"},
                         headers=owner_headers, timeout=10)
        assert r.status_code == 400

    def test_scan_public_and_analytics(self, owner_headers):
        # scan is public — no auth header
        r = requests.post(f"{API}/marketing/scan",
                          json={"token": "tst.abcd", "t": "voucher", "id": "V-TEST",
                                "c": "iter44", "ua": "pytest"},
                          timeout=10)
        assert r.status_code == 200
        assert r.json().get("tracked") is True
        r2 = requests.get(f"{API}/marketing/analytics", params={"days": 30},
                          headers=owner_headers, timeout=10)
        assert r2.status_code == 200
        d = r2.json()
        for k in ("totalScans", "totalBookings", "scansByType",
                  "bookingsBySource", "generatedAt"):
            assert k in d


# ----- Channel state -----
class TestChannelState:
    def test_upsert_and_list(self, owner_headers):
        r = requests.post(f"{API}/channels/state",
                          json={"channel": "TEST_ubereats", "action": "pause",
                                "reason": "iter44"},
                          headers=owner_headers, timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "paused"
        r2 = requests.get(f"{API}/channels/state", headers=owner_headers, timeout=10)
        assert r2.status_code == 200
        assert any(row.get("channel") == "TEST_ubereats" for row in r2.json())

    def test_bad_action(self, owner_headers):
        r = requests.post(f"{API}/channels/state",
                          json={"channel": "TEST_x", "action": "explode"},
                          headers=owner_headers, timeout=10)
        assert r.status_code == 400


# ----- Customer wallet -----
class TestCustomerWallet:
    @pytest.fixture(scope="class")
    def a_customer_id(self, owner_headers):
        r = requests.get(f"{API}/customers", headers=owner_headers, timeout=10)
        assert r.status_code == 200
        items = r.json()
        if not items:
            # create a TEST_ customer
            payload = {"name": "TEST_Iter44 Customer",
                       "email": "iter44@test.com", "phone": "+61400000044"}
            c = requests.post(f"{API}/customers", json=payload,
                              headers=owner_headers, timeout=10)
            assert c.status_code in (200, 201)
            return c.json().get("id")
        return items[0].get("id")

    def test_wallet_shape(self, owner_headers, a_customer_id):
        r = requests.get(f"{API}/customers/{a_customer_id}/wallet",
                         headers=owner_headers, timeout=10)
        assert r.status_code == 200
        d = r.json()
        for k in ("customerId", "tier", "points", "storeCredit", "barcode", "qrToken"):
            assert k in d
        assert d["customerId"] == a_customer_id

    def test_lookup_bad_token(self, owner_headers):
        r = requests.post(f"{API}/customers/lookup-by-token",
                          json={"token": "abc.deadbeef"},
                          headers=owner_headers, timeout=10)
        assert r.status_code in (400, 401)

    def test_lookup_valid_token_roundtrip(self, owner_headers, a_customer_id):
        w = requests.get(f"{API}/customers/{a_customer_id}/wallet",
                        headers=owner_headers, timeout=10).json()
        r = requests.post(f"{API}/customers/lookup-by-token",
                         json={"token": w["qrToken"]},
                         headers=owner_headers, timeout=10)
        assert r.status_code == 200
        assert r.json().get("id") == a_customer_id


# ----- PDF exports -----
class TestPdfExports:
    def test_low_stock_pdf(self, owner_headers):
        r = requests.get(f"{API}/inventory/low-stock/pdf",
                        headers=owner_headers, timeout=15)
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type", "")
        assert r.content.startswith(b"%PDF-1.4"), r.content[:20]

    def test_ai_pantry_pdf(self, owner_headers):
        r = requests.get(f"{API}/ai-pantry/order-sheet/pdf",
                        headers=owner_headers, timeout=15)
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type", "")
        assert r.content.startswith(b"%PDF-1.4"), r.content[:20]


# ----- Automation triggers -----
class TestAutomationTriggers:
    def test_crud(self, owner_headers):
        # create
        r = requests.post(f"{API}/automations/triggers",
                        json={"name": "TEST_iter44 trigger",
                              "event": "low_stock",
                              "conditions": {"threshold": 3},
                              "actions": [{"type": "dock_notify",
                                          "params": {"message": "hi"}}]},
                        headers=owner_headers, timeout=10)
        assert r.status_code == 200, r.text
        tid = r.json()["id"]

        # list
        r2 = requests.get(f"{API}/automations/triggers", headers=owner_headers, timeout=10)
        assert r2.status_code == 200
        assert any(t.get("id") == tid for t in r2.json())

        # patch
        r3 = requests.patch(f"{API}/automations/triggers/{tid}",
                            json={"active": False},
                            headers=owner_headers, timeout=10)
        assert r3.status_code == 200
        assert r3.json()["active"] is False

        # delete
        r4 = requests.delete(f"{API}/automations/triggers/{tid}",
                            headers=owner_headers, timeout=10)
        assert r4.status_code == 200

        # confirm 404 on second delete
        r5 = requests.delete(f"{API}/automations/triggers/{tid}",
                            headers=owner_headers, timeout=10)
        assert r5.status_code == 404

    def test_ai_suggest_fallback(self, owner_headers):
        r = requests.post(f"{API}/automations/ai-suggest",
                          json={"prompt": "notify me when a special is running low"},
                          headers=owner_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("name", "event", "conditions", "actions",
                  "aiGenerated", "aiPrompt"):
            assert k in d
        assert isinstance(d["actions"], list)


# ----- Locations extended + gmb-sync -----
class TestLocationsExtended:
    @pytest.fixture(scope="class")
    def a_location_id(self, owner_headers):
        r = requests.get(f"{API}/locations", headers=owner_headers, timeout=10)
        assert r.status_code == 200
        locs = r.json()
        if not locs:
            c = requests.post(f"{API}/locations",
                              json={"name": "TEST_iter44 loc",
                                    "address": "1 Test St"},
                              headers=owner_headers, timeout=10)
            assert c.status_code in (200, 201)
            return c.json()["id"]
        return locs[0]["id"]

    def test_extended_put(self, owner_headers, a_location_id):
        r = requests.put(f"{API}/locations/{a_location_id}",
                        json={"email": "shop@test.com",
                              "website": "https://test.com",
                              "logoUrl": "https://cdn.test/logo.png",
                              "hours": {"mon": {"open": "09:00", "close": "17:00", "closed": False}},
                              "timezone": "Australia/Sydney"},
                        headers=owner_headers, timeout=10)
        assert r.status_code == 200
        d = r.json()
        # extended fields should be present via GET
        rl = requests.get(f"{API}/locations", headers=owner_headers, timeout=10).json()
        me = next((x for x in rl if x["id"] == a_location_id), {})
        assert me.get("email") == "shop@test.com"
        assert me.get("website") == "https://test.com"
        assert me.get("timezone") == "Australia/Sydney"

    def test_gmb_sync_without_place_id(self, owner_headers, a_location_id):
        # First clear any place id
        requests.put(f"{API}/locations/{a_location_id}",
                    json={"gmbPlaceId": None}, headers=owner_headers, timeout=10)
        r = requests.post(f"{API}/locations/{a_location_id}/gmb-sync",
                        headers=owner_headers, timeout=10)
        assert r.status_code == 400

    def test_gmb_sync_missing_location(self, owner_headers):
        r = requests.post(f"{API}/locations/does-not-exist/gmb-sync",
                        headers=owner_headers, timeout=10)
        assert r.status_code == 404

    def test_gmb_sync_with_place_id(self, owner_headers, a_location_id):
        requests.put(f"{API}/locations/{a_location_id}",
                    json={"gmbPlaceId": "ChIJ_TEST_iter44"},
                    headers=owner_headers, timeout=10)
        r = requests.post(f"{API}/locations/{a_location_id}/gmb-sync",
                        headers=owner_headers, timeout=10)
        assert r.status_code == 200
        assert "syncedAt" in r.json()


# ----- v15 POS tabs — tableId persistence -----
class TestPosTabsPersistTable:
    def test_create_tab_persists_table(self, owner_headers):
        r = requests.post(f"{API}/pos/tabs",
                        json={"name": "TEST_iter44 tab",
                              "cart": [],
                              "tableId": "tbl-TEST-44",
                              "tableNumber": 7,
                              "serverId": "srv-TEST"},
                        headers=owner_headers, timeout=10)
        assert r.status_code == 200, r.text
        tab = r.json()
        assert tab["tableId"] == "tbl-TEST-44"
        assert tab["tableNumber"] == 7
        assert tab["serverId"] == "srv-TEST"
        tab_id = tab["id"]

        # GET list
        r2 = requests.get(f"{API}/pos/tabs", headers=owner_headers, timeout=10)
        assert r2.status_code == 200
        found = next((t for t in r2.json() if t["id"] == tab_id), None)
        assert found and found["tableId"] == "tbl-TEST-44"
        assert found["tableNumber"] == 7

        # cleanup
        requests.delete(f"{API}/pos/tabs/{tab_id}", headers=owner_headers, timeout=10)
