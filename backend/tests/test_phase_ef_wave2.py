"""Phase E + F Wave 2 backend tests + diagnostic regression for /api/reservations and /api/purchase-orders."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@nuva.com"
OWNER_PASSWORD = "NuvaOwner2026!"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    body = r.json()
    token = body.get("token") or body.get("access_token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# ---- Diagnostic regression ------------------------------------------------
class TestDiagnosticRegression:
    def test_reservations_returns_200(self, session):
        r = session.get(f"{API}/reservations", timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        data = r.json()
        assert isinstance(data, list)

    def test_purchase_orders_returns_200(self, session):
        r = session.get(f"{API}/purchase-orders", timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
        data = r.json()
        assert isinstance(data, (list, dict))


# ---- Phase E Wave 2 -------------------------------------------------------
class TestPhaseEWave2:
    def test_upsell_empty_cart(self, session):
        r = session.post(f"{API}/ai/upsell", json={"cart": []}, timeout=60)
        assert r.status_code == 200
        assert r.json().get("suggestions") == []

    def test_upsell_with_cart(self, session):
        prods = session.get(f"{API}/products", timeout=30).json()
        assert prods, "No products in DB"
        cart = [{"productId": prods[0]["id"], "name": prods[0]["name"],
                 "price": prods[0]["price"], "quantity": 1}]
        r = session.post(f"{API}/ai/upsell", json={"cart": cart}, timeout=90)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
        assert len(data["suggestions"]) <= 3
        for s in data["suggestions"]:
            assert "productId" in s and "name" in s and "price" in s and "reason" in s

    def test_price_tune_get(self, session):
        r = session.get(f"{API}/ai/price-tune", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "medianVelocity" in data
        assert "recommendations" in data and isinstance(data["recommendations"], list)

    def test_price_tune_apply(self, session):
        prods = session.get(f"{API}/products", timeout=30).json()
        assert prods, "No products"
        p = prods[0]
        original = float(p["price"])
        new_price = round(original + 0.01, 2)
        r = session.post(f"{API}/ai/price-tune/apply",
                         json={"productId": p["id"], "newPrice": new_price}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body.get("updated") is True
        assert body.get("newPrice") == new_price
        # Verify persistence
        prods2 = session.get(f"{API}/products", timeout=30).json()
        same = next((x for x in prods2 if x["id"] == p["id"]), None)
        assert same and float(same["price"]) == new_price
        # Revert
        session.post(f"{API}/ai/price-tune/apply",
                     json={"productId": p["id"], "newPrice": original}, timeout=30)

    def test_overbooking_check(self, session):
        r = session.post(f"{API}/ai/overbooking-check",
                         json={"date": "2026-02-14", "time": "19:00", "partySize": 4}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        for k in ["allow", "capacity", "withBuffer", "available", "reason"]:
            assert k in data, f"Missing field: {k}"


# ---- Phase F Wave 2 -------------------------------------------------------
class TestPhaseFWave2:
    def test_cost_coach(self, session):
        r = session.get(f"{API}/ai/cost-coach", timeout=120)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        for k in ["overallCostPct", "targetCostPct", "offenders", "actions"]:
            assert k in data, f"Missing: {k}"
        assert isinstance(data["offenders"], list)

    def test_labor_forecast(self, session):
        r = session.get(f"{API}/ai/labor-forecast", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "weeks_analyzed" in data
        assert "forecast" in data
        assert isinstance(data["forecast"], list)
        assert len(data["forecast"]) == 7
        for day in data["forecast"]:
            assert "date" in day and "dayOfWeek" in day and "hours" in day
            assert "peakHour" in day and "totalStaffHours" in day
            assert isinstance(day["hours"], list)
            if day["hours"]:
                h0 = day["hours"][0]
                for k in ["hour", "avgOrders", "foh", "boh", "total"]:
                    assert k in h0, f"Missing hour field: {k}"

    def test_surge_recommendations(self, session):
        r = session.get(f"{API}/ai/surge-recommendations", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_surge_apply_and_active(self, session):
        rules = [{"dow": 5, "hour": 19, "multiplier": 1.15, "reason": "test"}]
        r = session.post(f"{API}/ai/surge/apply", json={"rules": rules}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("applied") == 1
        # Clear
        session.post(f"{API}/ai/surge/apply", json={"rules": []}, timeout=30)

    def test_voice_recipe_text(self, session):
        r = session.post(f"{API}/ai/voice-recipe",
                         json={"text": "Pan-seared salmon with lemon butter sauce, asparagus, 4 portions."},
                         timeout=120)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "name" in data
        assert "ingredients" in data and isinstance(data["ingredients"], list)
        assert "steps" in data and isinstance(data["steps"], list)

    def test_kitchen_load(self, session):
        r = session.get(f"{API}/ai/kitchen-load", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "stations" in data and isinstance(data["stations"], list)
        assert "suggestions" in data and isinstance(data["suggestions"], list)
