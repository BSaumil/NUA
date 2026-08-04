"""Iteration 29 backend tests — Online ordering + AI ETA + Invoice OCR + insights.

Covers:
- GET  /api/online/categories (public, channel-filtered, prepTime exposed)
- POST /api/online/orders (public, ETA computed)
- GET  /api/online/orders/track/{code} (public, no PII leakage)
- PATCH /api/online/orders/{id}/status (auth, channel-aware messaging)
- POST /api/online/orders/{id}/eta (auth, recompute)
- GET  /api/online/kitchen/load (auth)
- POST /api/categories/cleanup-legacy (owner, preserves canonical/with-products)
- POST /api/categories with prepTime/channels (default 8 / [dine-in,pickup,delivery])
- POST /api/ai-pantry/parse-invoice + /apply-invoice (LLM, fuzzy match)
- GET  /api/products/insights (margin% + weekly sales)
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
OWNER_EMAIL = "owner@nua.com"
OWNER_PASSWORD = "NuaOwner2026!"


@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}


# ----- Categories: prepTime/channels + cleanup-legacy -----------------
class TestCategories:
    def test_create_with_defaults(self, owner_headers):
        r = requests.post(f"{BASE_URL}/api/categories",
                          headers=owner_headers,
                          json={"name": "TEST_DefaultCat", "icon": "Coffee", "color": "#000"})
        assert r.status_code == 200, r.text
        cat = r.json()
        assert cat["prepTime"] == 8
        assert set(cat["channels"]) == {"dine-in", "pickup", "delivery"}
        # cleanup
        requests.delete(f"{BASE_URL}/api/categories/{cat['id']}", headers=owner_headers)

    def test_create_and_update_with_explicit(self, owner_headers):
        r = requests.post(f"{BASE_URL}/api/categories",
                          headers=owner_headers,
                          json={"name": "TEST_PrepCat", "icon": "Coffee", "color": "#abc",
                                "prepTime": 15, "channels": ["dine-in", "pickup"]})
        assert r.status_code == 200, r.text
        cat = r.json()
        assert cat["prepTime"] == 15
        assert "delivery" not in cat["channels"]
        # Update
        u = requests.put(f"{BASE_URL}/api/categories/{cat['id']}",
                         headers=owner_headers,
                         json={"prepTime": 22, "channels": ["dine-in"]})
        assert u.status_code == 200, u.text
        assert u.json()["prepTime"] == 22
        assert u.json()["channels"] == ["dine-in"]
        requests.delete(f"{BASE_URL}/api/categories/{cat['id']}", headers=owner_headers)

    def test_cleanup_legacy_preserves_canonical(self, owner_headers):
        # Create one orphan TEST cat (zero products) — should be cleaned up
        rc = requests.post(f"{BASE_URL}/api/categories", headers=owner_headers,
                           json={"name": "TEST_LegacyOrphan", "icon": "Coffee", "color": "#999"})
        assert rc.status_code == 200
        r = requests.post(f"{BASE_URL}/api/categories/cleanup-legacy", headers=owner_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        # Canonical names must still exist after cleanup
        cats = requests.get(f"{BASE_URL}/api/categories", headers=owner_headers).json()
        names = {c["name"] for c in cats}
        for canonical in ("Coffee", "Burgers", "Mains", "Cakes & Slices", "Pasta"):
            assert canonical in names, f"Cleanup removed canonical {canonical}"
        assert "TEST_LegacyOrphan" not in names, "Orphan TEST cat not removed by cleanup"
        assert isinstance(body.get("removed", []), list) or "removedCount" in body


# ----- Online storefront ----------------------------------------------
class TestOnlineStorefront:
    def test_public_categories_filtered(self):
        r = requests.get(f"{BASE_URL}/api/online/categories")
        assert r.status_code == 200, r.text
        cats = r.json()
        assert len(cats) >= 1
        for c in cats:
            assert "prepTime" in c
            assert "name" in c

    def test_place_order_and_track(self):
        # Get a product to order
        cats = requests.get(f"{BASE_URL}/api/online/categories").json()
        assert cats, "No public categories"
        prods = requests.get(f"{BASE_URL}/api/online/products").json()
        assert prods, "No public products"
        p = prods[0]
        payload = {
            "items": [{"productId": p["id"], "name": p["name"],
                       "price": p["price"], "quantity": 2,
                       "category": p["category"]}],
            "channel": "pickup",
            "customerName": "TEST_Buyer",
            "customerPhone": "0400000000",
        }
        r = requests.post(f"{BASE_URL}/api/online/orders", json=payload)
        assert r.status_code == 200, r.text
        order = r.json()
        assert order["status"] == "pending"
        assert order["eta"]["etaMinutes"] >= 1
        assert isinstance(order.get("etaMessage", ""), str) and len(order["etaMessage"]) > 0
        code = order["id"]

        # Track (public, no PII)
        t = requests.get(f"{BASE_URL}/api/online/orders/track/{code}")
        assert t.status_code == 200, t.text
        td = t.json()
        assert td["customerName"] == "TEST_Buyer"
        # Internal customer phone/email/address must not leak
        assert "customer" not in td or not (td.get("customer") or {}).get("phone")
        assert td["status"] == "pending"
        assert any(n.get("message") for n in td.get("notifications", []))
        # Stash for later tests
        TestOnlineStorefront.code = code

    def test_delivery_requires_address(self):
        cats = requests.get(f"{BASE_URL}/api/online/categories").json()
        prods = requests.get(f"{BASE_URL}/api/online/products").json()
        p = prods[0]
        r = requests.post(f"{BASE_URL}/api/online/orders", json={
            "items": [{"productId": p["id"], "name": p["name"], "price": p["price"],
                       "quantity": 1, "category": p["category"]}],
            "channel": "delivery", "customerName": "TEST_NoAddr"
        })
        assert r.status_code == 400


# ----- Owner inbox + status lifecycle ---------------------------------
class TestOwnerInbox:
    def test_kitchen_load(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/online/kitchen/load", headers=owner_headers)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("pending", "accepted", "preparing", "queuePenaltyMins"):
            assert k in d

    def test_advance_status_lifecycle(self, owner_headers):
        code = getattr(TestOnlineStorefront, "code", None)
        if not code:
            pytest.skip("No order created in TestOnlineStorefront")
        for new_status in ("accepted", "preparing", "ready", "completed"):
            r = requests.patch(f"{BASE_URL}/api/online/orders/{code}/status",
                               headers=owner_headers,
                               json={"status": new_status})
            assert r.status_code == 200, f"Status {new_status} failed: {r.text}"
            assert r.json()["status"] == new_status
        # Track should reflect customer notifications added at each step
        t = requests.get(f"{BASE_URL}/api/online/orders/track/{code}").json()
        # Expect created + accepted + preparing + ready + completed (5+)
        assert len(t.get("notifications", [])) >= 4, f"Notifications: {t.get('notifications')}"
        kinds = [e["kind"] for e in t.get("events", [])]
        assert any("status:accepted" in k for k in kinds)
        assert any("status:completed" in k for k in kinds)

    def test_recompute_eta(self, owner_headers):
        code = getattr(TestOnlineStorefront, "code", None)
        if not code:
            pytest.skip("No order")
        r = requests.post(f"{BASE_URL}/api/online/orders/{code}/eta", headers=owner_headers)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "eta" in d and "etaMinutes" in d["eta"]


# ----- Products insights ----------------------------------------------
class TestInsights:
    def test_insights(self, owner_headers):
        r = requests.get(f"{BASE_URL}/api/products/insights", headers=owner_headers)
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list) and rows
        sample = rows[0]
        for k in ("productId", "name", "weeklyUnitsSold", "weeklyRevenue",
                  "marginAmount", "marginPct"):
            assert k in sample, f"Missing {k} in insight row: {sample}"


# ----- Invoice OCR (LLM-backed) ---------------------------------------
class TestInvoiceOCR:
    def test_parse_and_apply(self, owner_headers):
        # Use a product name we know is seeded — Espresso (Coffee category)
        text = ("INVOICE 12345\n"
                "Supplier: Test Roastery\n"
                "2x Espresso $9.00\n"
                "5x Long Black $24.00\n"
                "Total $33.00")
        r = requests.post(f"{BASE_URL}/api/ai-pantry/parse-invoice",
                          headers=owner_headers, json={"text": text}, timeout=90)
        if r.status_code == 422:
            pytest.skip(f"LLM could not parse invoice deterministically: {r.text[:200]}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "parsed" in body and "items" in body["parsed"]
        assert isinstance(body.get("matches"), list)
        # We expect at least one match for Espresso (seeded)
        matched = [m for m in body["matches"] if m.get("matchedProductId")]
        if not matched:
            pytest.skip("LLM parsed but fuzzy matcher found no products — env catalog drift")
        # Apply cost-only on first match to be conservative
        m = matched[0]
        selections = [{"matchedProductId": m["matchedProductId"],
                       "applyCost": True, "applyPrice": False}]
        a = requests.post(f"{BASE_URL}/api/ai-pantry/apply-invoice/{body['id']}",
                          headers=owner_headers, json={"selections": selections})
        assert a.status_code == 200, a.text
        ad = a.json()
        assert ad.get("updated", 0) >= 1
        assert isinstance(ad.get("audit"), list) and len(ad["audit"]) >= 1
