"""
Iteration: P0 Auth-Refactor + Channel Menus / Reservations AI / Fair Work / Bookings AI Inbox.

Validates:
  * Auth precedence: 401 (anon) and 403 (cashier) fire BEFORE Pydantic 422.
  * Happy-path with owner for products bulk-edit, modifiers CRUD, product-images.
  * Channel menus CRUD + AI prep-times + AI slow-mover discount.
  * Reservations AI auto-assign + seat + complete.
  * Awards catalogue, install, sync, super-by-award.
  * Bookings AI inbox ingest + list + ack -> reservation.
  * Regression on products/transactions/customers.
"""
import os
import base64
import pytest
import requests
from datetime import datetime, timedelta

_BURL = os.environ.get("REACT_APP_BACKEND_URL")
if not _BURL:
    # fall back to reading the frontend .env at runtime
    try:
        with open("/app/frontend/.env") as _f:
            for _line in _f:
                if _line.startswith("REACT_APP_BACKEND_URL="):
                    _BURL = _line.strip().split("=", 1)[1]
                    break
    except FileNotFoundError:
        pass
assert _BURL, "REACT_APP_BACKEND_URL not configured"
BASE = _BURL.rstrip("/") + "/api"

OWNER = {"email": "owner@nuva.com", "password": "NuvaOwner2026!"}
CASHIER = {"email": "cashier@nuva.com", "password": "Staff2026!"}


# ---------- shared fixtures ---------- #
@pytest.fixture(scope="session")
def owner_token():
    r = requests.post(f"{BASE}/auth/login", json=OWNER, timeout=30)
    assert r.status_code == 200, r.text
    return r.json().get("token") or r.json().get("access_token")


@pytest.fixture(scope="session")
def cashier_token():
    r = requests.post(f"{BASE}/auth/login", json=CASHIER, timeout=30)
    assert r.status_code == 200, r.text
    return r.json().get("token") or r.json().get("access_token")


@pytest.fixture(scope="session")
def owner_h(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture(scope="session")
def cashier_h(cashier_token):
    return {"Authorization": f"Bearer {cashier_token}"}


# ---------- Auth Precedence (401 before 422) ---------- #
AUTH_ENDPOINTS_POST = [
    "/products/bulk-edit",
    "/modifiers",
    "/categories",
    "/discounts",
    "/comp-void",
    "/payment-links",
    "/product-images",
    "/channel-menus/website/patch",
    "/channel-menus/website/bulk-price",
    "/channel-menus/website/ai-prep-times",
    "/channel-menus/website/ai-discount-slow",
    "/seed/catalog",
]


class TestAuthPrecedence:
    @pytest.mark.parametrize("path", AUTH_ENDPOINTS_POST)
    def test_anon_returns_401_not_422(self, path):
        r = requests.post(f"{BASE}{path}", json={"__bogus__": True}, timeout=30)
        assert r.status_code == 401, f"{path} expected 401, got {r.status_code}: {r.text[:200]}"

    @pytest.mark.parametrize("path", AUTH_ENDPOINTS_POST)
    def test_cashier_returns_403_not_422(self, path, cashier_h):
        r = requests.post(f"{BASE}{path}", json={"__bogus__": True}, headers=cashier_h, timeout=30)
        assert r.status_code == 403, f"{path} expected 403, got {r.status_code}: {r.text[:200]}"


# ---------- Products bulk-edit happy path ---------- #
class TestProductsBulkEdit:
    def test_bulk_edit_price_delta(self, owner_h):
        # find two products
        plist = requests.get(f"{BASE}/products", headers=owner_h, timeout=30).json()
        assert isinstance(plist, list) and len(plist) >= 2
        ids = [p["id"] for p in plist[:2]]
        payload = {
            "productIds": ids,
            "priceDelta": 0.0,        # no-op delta, safe
            "modifierAdd": [],
            "modifierRemove": [],
        }
        r = requests.post(f"{BASE}/products/bulk-edit", headers=owner_h, json=payload, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Tolerant assertion on shape
        assert "updated" in data
        assert "failed" in data or "errors" in data or "mode" in data


# ---------- Modifiers CRUD ---------- #
class TestModifiersCRUD:
    def test_create_update_delete(self, owner_h):
        body = {"name": "TEST_Sauce", "price": 1.5, "category": "Sauce"}
        r = requests.post(f"{BASE}/modifiers", headers=owner_h, json=body, timeout=30)
        assert r.status_code in (200, 201), r.text
        mid = r.json().get("id") or r.json().get("_id")
        assert mid

        r2 = requests.put(f"{BASE}/modifiers/{mid}", headers=owner_h,
                          json={"name": "TEST_Sauce2", "price": 2.0}, timeout=30)
        assert r2.status_code == 200, r2.text

        r3 = requests.delete(f"{BASE}/modifiers/{mid}", headers=owner_h, timeout=30)
        assert r3.status_code in (200, 204), r3.text


# ---------- Product Images ---------- #
class TestProductImages:
    def test_upload_list_delete(self, owner_h):
        tiny_png = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
        data_url = "data:image/png;base64," + tiny_png
        r = requests.post(f"{BASE}/product-images", headers=owner_h,
                          json={"name": "TEST_img", "dataUrl": data_url,
                                "contentType": "image/png"}, timeout=30)
        assert r.status_code in (200, 201), r.text
        iid = r.json().get("id") or r.json().get("_id")
        rl = requests.get(f"{BASE}/product-images", headers=owner_h, timeout=30)
        assert rl.status_code == 200
        if iid:
            rd = requests.delete(f"{BASE}/product-images/{iid}", headers=owner_h, timeout=30)
            assert rd.status_code in (200, 204)


# ---------- Channel Menus ---------- #
class TestChannelMenus:
    def test_channels_list(self, owner_h):
        r = requests.get(f"{BASE}/channel-menus/channels", headers=owner_h, timeout=30)
        assert r.status_code == 200, r.text
        chans = r.json()
        # Accept either list of channels or {channels:[...]}
        if isinstance(chans, dict):
            chans = chans.get("channels", [])
        assert len(chans) >= 7  # spec says 8

    def test_website_listing(self, owner_h):
        r = requests.get(f"{BASE}/channel-menus/website", headers=owner_h, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        items = body if isinstance(body, list) else body.get("products", body.get("items", []))
        assert isinstance(items, list)

    def test_patch_and_bulk_and_delete(self, owner_h):
        # pick first product id
        items = requests.get(f"{BASE}/channel-menus/website", headers=owner_h, timeout=30).json()
        if isinstance(items, dict):
            items = items.get("products", items.get("items", []))
        assert items, "no products on website channel"
        pid = items[0].get("id") or items[0].get("productId") or items[0].get("_id")
        assert pid

        rp = requests.post(f"{BASE}/channel-menus/website/patch", headers=owner_h,
                           json={"productId": pid, "priceOverride": 9.99}, timeout=30)
        assert rp.status_code == 200, rp.text

        rb = requests.post(f"{BASE}/channel-menus/website/bulk-price", headers=owner_h,
                           json={"deltaPercent": 10, "rounding": "nearest_5c"}, timeout=30)
        assert rb.status_code == 200, rb.text

        rd = requests.delete(f"{BASE}/channel-menus/website/{pid}", headers=owner_h, timeout=30)
        assert rd.status_code in (200, 204), rd.text


# ---------- AI Kitchen Heat / Slow Mover ---------- #
class TestAIChannelMenu:
    def test_ai_prep_times(self, owner_h):
        r = requests.post(f"{BASE}/channel-menus/website/ai-prep-times",
                          headers=owner_h, json={}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("updated", "heat", "multiplier", "activeTickets"):
            assert k in data, f"missing key {k}: {data}"

    def test_ai_discount_slow(self, owner_h):
        r = requests.post(f"{BASE}/channel-menus/website/ai-discount-slow",
                          headers=owner_h,
                          json={"discountPercent": 15, "bottomN": 3}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "applied" in data, data
        assert isinstance(data["applied"], list)


# ---------- Reservations AI auto-assign ---------- #
class TestReservationsAI:
    def test_create_assign_seat_complete(self, owner_h):
        when = datetime.utcnow() + timedelta(days=1)
        body = {
            "guestName": "TEST_AI_Guest",
            "phone": "0400000000",
            "partySize": 2,
            "date": when.strftime("%Y-%m-%d"),
            "time": "19:00",
            "notes": "auto-assign test",
        }
        r = requests.post(f"{BASE}/reservations", headers=owner_h, json=body, timeout=30)
        assert r.status_code in (200, 201), r.text
        rid = r.json().get("id") or r.json().get("_id")
        assert rid

        ra = requests.post(f"{BASE}/reservations/{rid}/ai-assign-table",
                           headers=owner_h, json={}, timeout=30)
        # Allow 200 with table or 200 with no_fit message
        assert ra.status_code == 200, ra.text

        rs = requests.post(f"{BASE}/reservations/{rid}/seat", headers=owner_h, json={}, timeout=30)
        assert rs.status_code in (200, 204), rs.text

        rc = requests.post(f"{BASE}/reservations/{rid}/complete", headers=owner_h, json={}, timeout=30)
        assert rc.status_code in (200, 204), rc.text


# ---------- Fair Work Awards ---------- #
class TestFairWorkAwards:
    def test_catalogue(self, owner_h):
        r = requests.get(f"{BASE}/awards/catalogue", headers=owner_h, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        items = body if isinstance(body, list) else body.get("awards", body.get("catalogue", []))
        assert len(items) >= 7, f"expected ≥7 awards, got {len(items)}"

    def test_install_and_list(self, owner_h):
        r = requests.post(f"{BASE}/awards/install", headers=owner_h,
                          json={"code": "MA000119"}, timeout=30)
        assert r.status_code in (200, 201), r.text
        rl = requests.get(f"{BASE}/awards/installed", headers=owner_h, timeout=30)
        assert rl.status_code == 200, rl.text
        installed = rl.json()
        installed_list = installed if isinstance(installed, list) else installed.get("awards", [])
        codes = [a.get("code") for a in installed_list]
        assert "MA000119" in codes, codes

    def test_sync_fairwork(self, owner_h):
        r = requests.post(f"{BASE}/awards/sync-fairwork", headers=owner_h, json={}, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("stale", "count", "awards"):
            assert k in data, f"missing {k}: {data}"

    def test_super_by_award(self, owner_h):
        r = requests.post(f"{BASE}/payruns/super-by-award", headers=owner_h, json={}, timeout=30)
        assert r.status_code == 200, r.text


# ---------- Bookings AI Inbox ---------- #
class TestBookingsInbox:
    def test_ingest_list_ack_to_reservation(self, owner_h):
        body = {
            "channel": "email",
            "from": "guest@example.com",
            "subject": "Reservation",
            "rawMessage": "Hi, table for 4 tomorrow 7pm please. Name Jane.",
        }
        r = requests.post(f"{BASE}/bookings/inbox", headers=owner_h, json=body, timeout=60)
        assert r.status_code in (200, 201), r.text
        data = r.json()
        # Backend returns parsed, aiSummary, suggestedReply
        assert "parsed" in data, data
        assert ("summary" in data) or ("aiSummary" in data), data
        assert ("reply" in data) or ("suggestedReply" in data), data
        bid = data.get("id") or data.get("_id") or (data.get("inbox") or {}).get("id")

        rl = requests.get(f"{BASE}/bookings/inbox", headers=owner_h, timeout=30)
        assert rl.status_code == 200, rl.text
        rows = rl.json()
        rows_list = rows if isinstance(rows, list) else rows.get("inbox", rows.get("items", []))
        assert isinstance(rows_list, list)
        if not bid and rows_list:
            bid = rows_list[0].get("id") or rows_list[0].get("_id")
        assert bid, "no inbox id available"

        ra = requests.post(f"{BASE}/bookings/inbox/{bid}/ack", headers=owner_h,
                           json={"convertToReservation": True}, timeout=30)
        assert ra.status_code == 200, ra.text


# ---------- Regression ---------- #
class TestRegression:
    def test_products_list(self, owner_h):
        r = requests.get(f"{BASE}/products", headers=owner_h, timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_product(self, owner_h):
        body = {
            "name": "TEST_RegProd",
            "price": 4.50,
            "cost": 1.50,
            "stock": 10,
            "sku": "TEST-REG-001",
            "category": "Coffee",
            "image": "https://example.com/x.png",
        }
        r = requests.post(f"{BASE}/products", headers=owner_h, json=body, timeout=30)
        assert r.status_code in (200, 201), r.text
        pid = r.json().get("id") or r.json().get("_id")
        if pid:
            requests.delete(f"{BASE}/products/{pid}", headers=owner_h, timeout=30)

    def test_create_transaction(self, owner_h):
        body = {
            "items": [{"productId": "x", "productName": "TEST", "price": 1.0, "quantity": 1}],
            "subtotal": 1.0, "gst": 0.1, "total": 1.1,
            "paymentMethod": "cash",
            "location": "main",
            "cashier": "owner@nuva.com",
        }
        r = requests.post(f"{BASE}/transactions", headers=owner_h, json=body, timeout=30)
        assert r.status_code in (200, 201), r.text

    def test_create_customer(self, owner_h):
        body = {"name": "TEST_RegCust", "phone": "0400111222", "email": "trc@example.com"}
        r = requests.post(f"{BASE}/customers", headers=owner_h, json=body, timeout=30)
        assert r.status_code in (200, 201), r.text
