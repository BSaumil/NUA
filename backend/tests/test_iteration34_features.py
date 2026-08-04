"""
Iteration 34 backend tests:
- AI Bookings Inbox (POST/GET/ack)
- Awards Super engine (catalogue/install/uninstall/super-by-award)
- Integrations Hub (Banks AU + Payment Terminals categories & providers)
- Products bulk-edit modes (update_many vs per_row)
- /product-images auth guard (POST/DELETE owner/manager only; GET requires auth)
"""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = BASE_URL + "/api"


def _login(email: str, password: str):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="module")
def owner_token():
    return _login("owner@nua.com", "NuaOwner2026!")


@pytest.fixture(scope="module")
def cashier_token():
    try:
        return _login("cashier@nua.com", "Staff2026!")
    except Exception:
        pytest.skip("cashier login unavailable")


@pytest.fixture
def owner_session(owner_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"})
    return s


@pytest.fixture
def cashier_session(cashier_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {cashier_token}", "Content-Type": "application/json"})
    return s


# ----------------------- AI BOOKINGS INBOX -----------------------
class TestBookingsInbox:
    def test_ingest_phone_message_returns_parsed_and_summary(self):
        body = {
            "channel": "phone",
            "rawMessage": "Want a table for 4 tonight at 7pm under name Alex 0412333444 — one gluten free",
            "fromHandle": "TEST_iter34_alex",
        }
        r = requests.post(f"{API}/bookings/inbox", json=body, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["channel"] == "phone"
        assert data["status"] == "new"
        assert "id" in data
        assert "aiSummary" in data and data["aiSummary"]
        assert "suggestedReply" in data and data["suggestedReply"]
        assert "parsed" in data
        # verify GET shows item in 'new'
        list_r = requests.get(f"{API}/bookings/inbox?status=new&limit=200", timeout=15)
        assert list_r.status_code == 200
        ids = [i["id"] for i in list_r.json()]
        assert data["id"] in ids
        pytest._iter34_inbox_id = data["id"]

    def test_convert_to_reservation(self):
        item_id = getattr(pytest, "_iter34_inbox_id", None)
        if not item_id:
            pytest.skip("ingest test did not run")
        r = requests.post(
            f"{API}/bookings/inbox/{item_id}/ack",
            json={"convertToReservation": True, "user": "TEST_iter34"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("status") == "converted"
        assert data.get("reservationId"), "reservationId should be set after conversion"

        # confirm inbox item now shows converted via list
        items = requests.get(f"{API}/bookings/inbox?limit=500", timeout=15).json()
        match = next((i for i in items if i["id"] == item_id), None)
        assert match is not None
        assert match["status"] == "converted"
        assert match.get("reservationId") == data["reservationId"]

    def test_dismiss_404_for_missing(self):
        r = requests.post(f"{API}/bookings/inbox/does-not-exist/dismiss", timeout=10)
        assert r.status_code == 404


# ----------------------- AWARDS / SUPER -----------------------
class TestAwards:
    def test_catalogue_has_4_au_awards(self):
        r = requests.get(f"{API}/awards/catalogue?country=AU", timeout=10)
        assert r.status_code == 200
        codes = {a["code"] for a in r.json()}
        for c in ("MA000119", "MA000009", "MA000003", "MA000004"):
            assert c in codes, f"missing AU award {c}"
        for a in r.json():
            assert a["country"] == "AU"
            assert a["superRate"] == 11.5
            assert len(a.get("classifications", [])) >= 3

    def test_catalogue_country_filter_nz_uk_us(self):
        for country in ("NZ", "UK", "US"):
            r = requests.get(f"{API}/awards/catalogue?country={country}", timeout=10)
            assert r.status_code == 200
            data = r.json()
            assert len(data) >= 1
            assert all(a["country"] == country for a in data)

    def test_install_then_uninstall(self):
        # Cleanup if present
        requests.delete(f"{API}/awards/MA000119", timeout=10)

        r = requests.post(f"{API}/awards/install", json={"code": "MA000119"}, timeout=10)
        assert r.status_code == 200, r.text
        installed = requests.get(f"{API}/awards/installed", timeout=10).json()
        codes = [a["code"] for a in installed]
        assert "MA000119" in codes

        d = requests.delete(f"{API}/awards/MA000119", timeout=10)
        assert d.status_code == 200

    def test_super_by_award(self):
        # Ensure MA000119 installed
        requests.post(f"{API}/awards/install", json={"code": "MA000119"}, timeout=10)
        body = {
            "awardCode": "MA000119",
            "period": "week",
            "payrun": {
                "staffPayroll": [
                    {"name": "Alice", "role": "Server", "grossPay": 1000},
                    {"name": "Bob", "role": "Cook", "grossPay": 2000},
                ]
            },
        }
        r = requests.post(f"{API}/payruns/super-by-award", json=body, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["totalSuper"] == 345.0  # 11.5% of 3000
        assert len(data["staffSuper"]) == 2
        for row in data["staffSuper"]:
            assert row["superRate"] == 11.5
            assert row["awardName"] == "Restaurant Industry Award"
            assert "superContribution" in row
        # cleanup
        requests.delete(f"{API}/awards/MA000119", timeout=10)


# ----------------------- INTEGRATIONS HUB -----------------------
class TestIntegrationsHub:
    def test_banks_au_and_payment_terminals_present(self):
        r = requests.get(f"{API}/integrations", timeout=10)
        assert r.status_code == 200
        data = r.json()
        cats = {x.get("category") for x in data}
        assert "Banks (AU)" in cats
        assert "Payment Terminals" in cats

        banks = [x["name"] for x in data if x.get("category") == "Banks (AU)"]
        for n in ("CBA", "Westpac", "ANZ", "NAB", "Macquarie"):
            assert any(n.lower() in b.lower() for b in banks), f"missing AU bank match for {n}: {banks}"

        terms = [x["name"] for x in data if x.get("category") == "Payment Terminals"]
        for n in ("Tyro", "Smartpay", "Zeller", "Square Terminal", "Verifone", "Ingenico", "PAX", "Adyen", "PayPal Zettle"):
            assert any(n.lower() in t.lower() for t in terms), f"missing terminal {n}: {terms}"


# ----------------------- BULK EDIT MODES -----------------------
class TestBulkEditModes:
    def _create_product(self, sess):
        body = {
            "name": f"TEST_iter34_{uuid.uuid4().hex[:6]}",
            "price": 10.0,
            "category": "drinks",
            "image": "https://example.com/x.png",
            "cost": 5.0,
            "stock": 0,
            "sku": f"TEST34{uuid.uuid4().hex[:5]}",
        }
        r = sess.post(f"{API}/products", json=body, timeout=10)
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]

    def test_fast_path_update_many(self, owner_session):
        pid = self._create_product(owner_session)
        body = {"productIds": [pid], "category": "snacks"}
        r = owner_session.post(f"{API}/products/bulk-edit", json=body, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["mode"] == "update_many"
        assert data["updated"] >= 1
        # verify persisted
        g = owner_session.get(f"{API}/products", timeout=10)
        prods = [p for p in g.json() if p["id"] == pid]
        assert prods and prods[0]["category"] == "snacks"
        owner_session.delete(f"{API}/products/{pid}")

    def test_per_row_with_price_percent_delta(self, owner_session):
        pid = self._create_product(owner_session)
        body = {"productIds": [pid], "pricePercentDelta": 10}
        r = owner_session.post(f"{API}/products/bulk-edit", json=body, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["mode"] == "per_row"
        assert data["updated"] >= 1
        g = owner_session.get(f"{API}/products", timeout=10)
        prods = [p for p in g.json() if p["id"] == pid]
        assert prods and round(float(prods[0]["price"]), 2) == 11.0
        owner_session.delete(f"{API}/products/{pid}")

    def test_per_row_with_modifier_ops(self, owner_session):
        pid = self._create_product(owner_session)
        body = {"productIds": [pid], "addModifierIds": ["mod-test-iter34"]}
        r = owner_session.post(f"{API}/products/bulk-edit", json=body, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["mode"] == "per_row"
        owner_session.delete(f"{API}/products/{pid}")


# ----------------------- PRODUCT-IMAGES AUTH -----------------------
class TestProductImagesAuth:
    TINY_PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgAAIAAAUAAen63NgAAAAASUVORK5CYII="

    def _payload(self, name="x"):
        return {"name": name, "dataUrl": self.TINY_PNG, "contentType": "image/png", "tags": []}

    def test_post_without_auth_is_blocked(self):
        r = requests.post(f"{API}/product-images", json=self._payload(), timeout=10)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code} {r.text[:200]}"

    def test_get_without_auth_is_blocked(self):
        r = requests.get(f"{API}/product-images", timeout=10)
        assert r.status_code in (401, 403)

    def test_cashier_cannot_post(self, cashier_session):
        r = cashier_session.post(f"{API}/product-images", json=self._payload(), timeout=10)
        assert r.status_code == 403, f"cashier should be forbidden: {r.status_code} {r.text[:200]}"

    def test_cashier_can_list(self, cashier_session):
        r = cashier_session.get(f"{API}/product-images", timeout=10)
        assert r.status_code == 200

    def test_owner_can_post_and_delete(self, owner_session):
        payload = self._payload("TEST_iter34_img")
        payload["tags"] = ["test"]
        r = owner_session.post(f"{API}/product-images", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        img_id = r.json()["id"]
        d_anon = requests.delete(f"{API}/product-images/{img_id}", timeout=10)
        assert d_anon.status_code in (401, 403)
        d = owner_session.delete(f"{API}/product-images/{img_id}", timeout=10)
        assert d.status_code == 200
