"""
Iteration 47 backend regression tests — Promotion enhancements.

Coverage:
  - POST /api/promotions accepts full new shape (pricingMode, bundlePrice,
    categories, minQuantity/maxQuantity, stackable, products)
  - PUT /api/promotions/{id} persists partial updates for all new fields
  - GET /api/promotions returns all rows including new fields (no 500 on legacy)
  - POST /api/v26/cart/apply-promos with fixed-price bundle returns correct shape
  - POST /api/v26/cart/apply-promos with percentage promo — no regression
  - Category-OR-product filter fires when any cart line matches
  - minQuantity gate — bundle does NOT fire when cart qty below threshold
"""
import os
import pytest
import requests

def _read_env_url():
    # Prefer runtime env; fall back to frontend/.env for pytest CLI runs.
    val = os.environ.get("REACT_APP_BACKEND_URL")
    if val:
        return val.rstrip("/")
    try:
        with open("/app/frontend/.env", "r") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except FileNotFoundError:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not configured")


BASE_URL = _read_env_url()

OWNER_EMAIL = "owner@nuva.com"
OWNER_PASS = "NuvaOwner2026!"


# ─────────────────────────── fixtures ───────────────────────────
@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASS},
        timeout=15,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"no token in login response: {r.json()}"
    return tok


@pytest.fixture(scope="module")
def owner_client(owner_token):
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"Bearer {owner_token}",
            "Content-Type": "application/json",
        }
    )
    return s


@pytest.fixture(scope="module")
def created_promos(owner_client):
    """Track ids so we can clean up at the end of the module."""
    ids = []
    yield ids
    for pid in ids:
        try:
            owner_client.delete(f"{BASE_URL}/api/promotions/{pid}", timeout=10)
        except Exception:
            pass


# ───────────────────── POST /api/promotions (new shape) ─────────────────────
class TestCreatePromotion:
    def test_create_fixed_price_bundle_full_shape(self, owner_client, created_promos):
        payload = {
            "name": "TEST_iter47 Family Feast",
            "type": "bundle",
            "pricingMode": "fixed_price",
            "bundlePrice": 25.0,
            "minQuantity": 3,
            "maxQuantity": 5,
            "stackable": True,
            "categories": ["Mains"],
            "products": ["prod-1", "prod-2", "prod-3"],
            "active": True,
            "schedule": "Family Feast",
        }
        r = owner_client.post(f"{BASE_URL}/api/promotions", json=payload, timeout=15)
        assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text}"
        data = r.json()
        # Echo all fields back
        assert data["name"] == payload["name"]
        assert data["type"] == "bundle"
        assert data["pricingMode"] == "fixed_price"
        assert data["bundlePrice"] == 25.0
        assert data["minQuantity"] == 3
        assert data["maxQuantity"] == 5
        assert data["stackable"] is True
        assert data["categories"] == ["Mains"]
        assert set(data["products"]) == {"prod-1", "prod-2", "prod-3"}
        assert data["active"] is True
        assert "id" in data and isinstance(data["id"], str)
        created_promos.append(data["id"])

        # GET → verify persistence
        g = owner_client.get(f"{BASE_URL}/api/promotions", timeout=10)
        assert g.status_code == 200
        rows = g.json()
        found = next((p for p in rows if p["id"] == data["id"]), None)
        assert found is not None, "created promo not returned by GET"
        assert found["pricingMode"] == "fixed_price"
        assert found["bundlePrice"] == 25.0
        assert found["minQuantity"] == 3
        assert found["stackable"] is True

    def test_create_percentage_promo_still_ok(self, owner_client, created_promos):
        payload = {
            "name": "TEST_iter47 15% Off Mains",
            "type": "category",
            "pricingMode": "percentage",
            "discount": 15.0,
            "categories": ["Mains"],
            "active": True,
        }
        r = owner_client.post(f"{BASE_URL}/api/promotions", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["pricingMode"] == "percentage"
        assert data["discount"] == 15.0
        assert data["categories"] == ["Mains"]
        created_promos.append(data["id"])


# ───────────────────── PUT /api/promotions/{id} ─────────────────────
class TestUpdatePromotion:
    def test_partial_update_persists_all_new_fields(self, owner_client, created_promos):
        # First create a baseline promo to mutate
        base = owner_client.post(
            f"{BASE_URL}/api/promotions",
            json={
                "name": "TEST_iter47 Update Me",
                "type": "bundle",
                "pricingMode": "percentage",
                "discount": 5.0,
                "active": True,
            },
            timeout=15,
        )
        assert base.status_code == 200, base.text
        pid = base.json()["id"]
        created_promos.append(pid)

        patch = {
            "bundlePrice": 30.0,
            "pricingMode": "fixed_price",
            "categories": ["Mains", "Sides"],
            "minQuantity": 4,
            "maxQuantity": 6,
            "stackable": True,
        }
        u = owner_client.put(
            f"{BASE_URL}/api/promotions/{pid}", json=patch, timeout=15
        )
        assert u.status_code == 200, f"PUT failed: {u.status_code} {u.text}"
        updated = u.json()
        for k, v in patch.items():
            actual = updated.get(k)
            if isinstance(v, list):
                assert sorted(actual or []) == sorted(v), f"{k} mismatch: {actual} vs {v}"
            else:
                assert actual == v, f"{k} mismatch: {actual} vs {v}"

        # GET again to make sure it persisted in DB (not just echoed)
        g = owner_client.get(f"{BASE_URL}/api/promotions", timeout=10)
        assert g.status_code == 200
        row = next((p for p in g.json() if p["id"] == pid), None)
        assert row is not None
        assert row["bundlePrice"] == 30.0
        assert row["pricingMode"] == "fixed_price"
        assert sorted(row["categories"]) == ["Mains", "Sides"]
        assert row["minQuantity"] == 4
        assert row["maxQuantity"] == 6
        assert row["stackable"] is True


# ───────────────────── GET /api/promotions ─────────────────────
class TestListPromotions:
    def test_list_returns_new_fields_no_500_on_legacy(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/promotions", timeout=15)
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list)
        # Every row must at least have the new fields present (defaults from
        # safe_parse_list applying the Promotion model).
        required_new_fields = {
            "pricingMode",
            "bundlePrice",
            "categories",
            "minQuantity",
            "stackable",
        }
        for row in rows:
            missing = required_new_fields - set(row.keys())
            assert (
                not missing
            ), f"row {row.get('id')} missing new fields: {missing}"


# ───────────────────── /v26/cart/apply-promos ─────────────────────
class TestApplyPromosToCart:
    def test_fixed_price_bundle_returns_correct_shape(self, owner_client, created_promos):
        # Create a fixed-price bundle: any 3 items with productId in list = $25
        promo = owner_client.post(
            f"{BASE_URL}/api/promotions",
            json={
                "name": "TEST_iter47 Bundle Apply",
                "type": "bundle",
                "pricingMode": "fixed_price",
                "bundlePrice": 25.0,
                "minQuantity": 3,
                "products": ["test-p1", "test-p2", "test-p3"],
                "active": True,
            },
            timeout=15,
        )
        assert promo.status_code == 200, promo.text
        created_promos.append(promo.json()["id"])

        cart = [
            {"productId": "test-p1", "price": 12.0, "quantity": 1, "category": "Mains"},
            {"productId": "test-p2", "price": 12.0, "quantity": 1, "category": "Mains"},
            {"productId": "test-p3", "price": 12.0, "quantity": 1, "category": "Sides"},
        ]
        r = owner_client.post(
            f"{BASE_URL}/api/v26/cart/apply-promos", json={"cart": cart}, timeout=15
        )
        assert r.status_code == 200, r.text
        data = r.json()
        applied = [a for a in data.get("applied", []) if a["name"] == "TEST_iter47 Bundle Apply"]
        assert applied, f"bundle did NOT fire; response={data}"
        a = applied[0]
        assert a["pricingMode"] == "fixed_price"
        assert a["bundlePrice"] == 25.0
        assert a["originalTotal"] == 36.0
        assert a["discount"] == 11.0  # 36 - 25
        assert "savingsPct" in a
        assert a["savingsPct"] > 0

    def test_percentage_promo_still_fires(self, owner_client, created_promos):
        promo = owner_client.post(
            f"{BASE_URL}/api/promotions",
            json={
                "name": "TEST_iter47 Percent Apply",
                "type": "category",
                "pricingMode": "percentage",
                "discount": 20.0,
                "categories": ["TESTCatPct47"],
                "active": True,
            },
            timeout=15,
        )
        assert promo.status_code == 200
        created_promos.append(promo.json()["id"])

        cart = [
            {"productId": "px", "price": 10.0, "quantity": 2, "category": "TESTCatPct47"},
        ]
        r = owner_client.post(
            f"{BASE_URL}/api/v26/cart/apply-promos", json={"cart": cart}, timeout=15
        )
        assert r.status_code == 200
        applied = [a for a in r.json().get("applied", []) if a["name"] == "TEST_iter47 Percent Apply"]
        assert applied, "percentage promo did NOT fire"
        a = applied[0]
        assert a["pricingMode"] == "percentage"
        assert a["percentage"] == 20.0
        assert a["discount"] == 4.0  # 20 * 20%

    def test_categories_or_products_match(self, owner_client, created_promos):
        """A promo with categories:['Mains'] must fire when any cart line has category='Mains'."""
        promo = owner_client.post(
            f"{BASE_URL}/api/promotions",
            json={
                "name": "TEST_iter47 CatMatch",
                "type": "category",
                "pricingMode": "percentage",
                "discount": 10.0,
                "categories": ["TESTMainsCat47"],
                "active": True,
            },
            timeout=15,
        )
        assert promo.status_code == 200
        created_promos.append(promo.json()["id"])

        cart = [
            {"productId": "unrelated-1", "price": 5.0, "quantity": 1, "category": "Drinks"},
            {"productId": "match-2", "price": 20.0, "quantity": 1, "category": "TESTMainsCat47"},
        ]
        r = owner_client.post(
            f"{BASE_URL}/api/v26/cart/apply-promos", json={"cart": cart}, timeout=15
        )
        assert r.status_code == 200
        applied = [a for a in r.json().get("applied", []) if a["name"] == "TEST_iter47 CatMatch"]
        assert applied, "category-match promo did NOT fire"
        # Only the matched line ($20) should be discounted → 10% = $2
        assert applied[0]["discount"] == 2.0

    def test_min_quantity_gate_blocks_when_below_threshold(self, owner_client, created_promos):
        promo = owner_client.post(
            f"{BASE_URL}/api/promotions",
            json={
                "name": "TEST_iter47 MinQtyGate",
                "type": "bundle",
                "pricingMode": "fixed_price",
                "bundlePrice": 25.0,
                "minQuantity": 3,
                "products": ["gate-p1", "gate-p2", "gate-p3"],
                "active": True,
            },
            timeout=15,
        )
        assert promo.status_code == 200
        created_promos.append(promo.json()["id"])

        # only 2 matching items → below threshold → must NOT fire
        cart = [
            {"productId": "gate-p1", "price": 12.0, "quantity": 1},
            {"productId": "gate-p2", "price": 12.0, "quantity": 1},
        ]
        r = owner_client.post(
            f"{BASE_URL}/api/v26/cart/apply-promos", json={"cart": cart}, timeout=15
        )
        assert r.status_code == 200
        applied = [a for a in r.json().get("applied", []) if a["name"] == "TEST_iter47 MinQtyGate"]
        assert not applied, f"bundle fired below minQuantity: {applied}"
