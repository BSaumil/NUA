"""
Iteration 33 — Items page features (bulk-edit + Image Library)
Tests:
  - POST /api/products/bulk-edit — pricePercentDelta, cost, gst, category, eightySixed
  - Modifier ops: add, remove, replace
  - Invalid productIds → recorded under failed[], does not 500
  - GET/POST/DELETE /api/product-images — data URL validation, oversize 413
"""
import os
import base64
import pytest
import requests

def _load_backend_url():
    env_url = os.environ.get("REACT_APP_BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")
    fe = "/app/frontend/.env"
    if os.path.exists(fe):
        with open(fe) as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL is not set")

BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

OWNER = {"email": "owner@nua.com", "password": "NuaOwner2026!"}


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def auth_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=OWNER, timeout=20)
    assert r.status_code == 200, f"Login failed {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"No token in login response: {r.json()}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def seeded_products(auth_session):
    """Create three throwaway products for bulk-edit tests."""
    ids = []
    base = {"price": 10.0, "cost": 4.0, "stock": 50, "category": "Coffee",
            "gstRate": 10.0, "eightySixed": False, "image": "https://example.com/x.png"}
    for i in range(3):
        p = {**base, "name": f"TEST_iter33_prod_{i}", "sku": f"TEST33-{i}"}
        r = auth_session.post(f"{API}/products", json=p, timeout=15)
        assert r.status_code in (200, 201), f"Create failed: {r.status_code} {r.text}"
        ids.append(r.json()["id"])
    yield ids
    # cleanup
    for pid in ids:
        try:
            auth_session.delete(f"{API}/products/{pid}", timeout=10)
        except Exception:
            pass


# ---------- bulk-edit tests ----------
class TestBulkEdit:
    def test_bulk_edit_price_percent_delta(self, auth_session, seeded_products):
        payload = {"productIds": seeded_products, "pricePercentDelta": 10}
        r = auth_session.post(f"{API}/products/bulk-edit", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["updated"] == 3
        assert body["failed"] == []
        # verify persisted: 10 * 1.10 = 11.00
        for pid in seeded_products:
            g = auth_session.get(f"{API}/products", timeout=10)
            prod = next(p for p in g.json() if p["id"] == pid)
            assert prod["price"] == pytest.approx(11.0, abs=0.01), f"{prod['price']}"

    def test_bulk_edit_cost_gst_category(self, auth_session, seeded_products):
        payload = {"productIds": seeded_products, "cost": 5.5,
                   "gstRate": 8, "category": "Tea", "eightySixed": True}
        r = auth_session.post(f"{API}/products/bulk-edit", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["updated"] == 3
        g = auth_session.get(f"{API}/products", timeout=10).json()
        for pid in seeded_products:
            prod = next(p for p in g if p["id"] == pid)
            assert prod["cost"] == 5.5
            assert prod["gstRate"] == 8
            assert prod["category"] == "Tea"
            assert prod["eightySixed"] is True

    def test_bulk_edit_unset_eightysixed(self, auth_session, seeded_products):
        r = auth_session.post(f"{API}/products/bulk-edit",
                              json={"productIds": seeded_products, "eightySixed": False},
                              timeout=20)
        assert r.status_code == 200
        g = auth_session.get(f"{API}/products", timeout=10).json()
        for pid in seeded_products:
            prod = next(p for p in g if p["id"] == pid)
            assert prod["eightySixed"] is False

    def test_bulk_edit_invalid_ids_recorded(self, auth_session):
        payload = {"productIds": ["does-not-exist-1", "does-not-exist-2"],
                   "cost": 1.0}
        r = auth_session.post(f"{API}/products/bulk-edit", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["updated"] == 0
        assert set(body["failed"]) == {"does-not-exist-1", "does-not-exist-2"}

    def test_bulk_edit_empty_ids_rejected(self, auth_session):
        r = auth_session.post(f"{API}/products/bulk-edit",
                              json={"productIds": []}, timeout=10)
        assert r.status_code == 400

    def test_bulk_modifier_add_remove_replace(self, auth_session, seeded_products):
        # add A,B
        r = auth_session.post(f"{API}/products/bulk-edit",
                              json={"productIds": seeded_products,
                                    "addModifierIds": ["modA", "modB"]}, timeout=15)
        assert r.status_code == 200
        g = auth_session.get(f"{API}/products", timeout=10).json()
        for pid in seeded_products:
            prod = next(p for p in g if p["id"] == pid)
            assert set(prod.get("modifierIds", [])) >= {"modA", "modB"}

        # remove A
        auth_session.post(f"{API}/products/bulk-edit",
                          json={"productIds": seeded_products,
                                "removeModifierIds": ["modA"]}, timeout=15)
        g = auth_session.get(f"{API}/products", timeout=10).json()
        for pid in seeded_products:
            prod = next(p for p in g if p["id"] == pid)
            assert "modA" not in prod.get("modifierIds", [])
            assert "modB" in prod.get("modifierIds", [])

        # replace wholly
        auth_session.post(f"{API}/products/bulk-edit",
                          json={"productIds": seeded_products,
                                "replaceModifierIds": ["onlyX"]}, timeout=15)
        g = auth_session.get(f"{API}/products", timeout=10).json()
        for pid in seeded_products:
            prod = next(p for p in g if p["id"] == pid)
            assert prod.get("modifierIds", []) == ["onlyX"]


# ---------- product-images tests ----------
class TestImageLibrary:
    tiny_png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Z"
        "Z+r3IAAAAASUVORK5CYII="
    )

    def _data_url(self):
        return f"data:image/png;base64,{self.tiny_png_b64}"

    def test_upload_valid_image_and_list_and_delete(self, auth_session):
        body = {"name": "TEST_iter33_img", "contentType": "image/png",
                "dataUrl": self._data_url(), "tags": ["test"]}
        r = auth_session.post(f"{API}/product-images", json=body, timeout=15)
        assert r.status_code == 200, r.text
        img = r.json()
        assert img["id"]
        assert img["sizeBytes"] > 0
        img_id = img["id"]

        # GET list
        r2 = auth_session.get(f"{API}/product-images", timeout=10)
        assert r2.status_code == 200
        assert any(x["id"] == img_id for x in r2.json())

        # DELETE
        r3 = auth_session.delete(f"{API}/product-images/{img_id}", timeout=10)
        assert r3.status_code == 200
        assert r3.json().get("deleted") is True

        # Confirm gone
        r4 = auth_session.get(f"{API}/product-images", timeout=10)
        assert not any(x["id"] == img_id for x in r4.json())

    def test_upload_rejects_non_data_url(self, auth_session):
        body = {"name": "TEST_iter33_bad", "contentType": "image/png",
                "dataUrl": "https://example.com/foo.png"}
        r = auth_session.post(f"{API}/product-images", json=body, timeout=10)
        assert r.status_code == 400, r.text

    def test_upload_rejects_oversize(self, auth_session):
        # Build a >1.5MB data URL
        big_payload = base64.b64encode(b"A" * 1_600_000).decode()
        body = {"name": "TEST_iter33_oversize", "contentType": "image/png",
                "dataUrl": f"data:image/png;base64,{big_payload}"}
        r = auth_session.post(f"{API}/product-images", json=body, timeout=20)
        assert r.status_code == 413, f"expected 413 got {r.status_code} {r.text}"

    def test_delete_nonexistent_image_404(self, auth_session):
        r = auth_session.delete(f"{API}/product-images/does-not-exist", timeout=10)
        assert r.status_code == 404
