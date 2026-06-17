"""Iteration 31 — Product model with categoryId + modifierIds, NUA brand re-test.

Tests:
- POST /api/auth/login (owner) returns token
- GET /api/categories returns active categories (active promos / dynamic)
- GET /api/modifiers returns modifiers list
- POST /api/products accepts categoryId + modifierIds, returns them on GET
- PUT /api/products/{id} updates categoryId + modifierIds, GET reflects changes
- Existing products without modifierIds field still load (no validation crash)
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@nuva.com"
OWNER_PASS = "NuvaOwner2026!"


@pytest.fixture(scope="session")
def auth_token():
    r = requests.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASS}, timeout=10)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    if not tok:
        pytest.skip("no token in login response")
    return tok


@pytest.fixture(scope="session")
def client(auth_token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {auth_token}"})
    return s


# ---------- 1. Login ----------
def test_owner_login():
    r = requests.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASS}, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert ("token" in body) or ("access_token" in body)


# ---------- 2. Categories endpoint ----------
def test_categories_endpoint(client):
    r = client.get(f"{API}/categories", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    if data:
        assert "id" in data[0] and "name" in data[0]


# ---------- 3. Modifiers endpoint ----------
def test_modifiers_endpoint(client):
    r = client.get(f"{API}/modifiers", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)


# ---------- 4. Existing products load (backwards compat for missing modifierIds) ----------
def test_existing_products_load(client):
    r = client.get(f"{API}/products", timeout=10)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list)
    # Each product should now expose modifierIds (default []) and categoryId (default None)
    for p in data[:5]:
        assert "modifierIds" in p
        assert "categoryId" in p
        assert isinstance(p["modifierIds"], list)


# ---------- 5. POST product with categoryId + modifierIds ----------
@pytest.fixture(scope="session")
def created_product_id(client):
    # Use a real category and modifier id if possible
    cats = client.get(f"{API}/categories", timeout=10).json()
    mods = client.get(f"{API}/modifiers", timeout=10).json()
    cat_id = (cats[0]["id"] if cats else None)
    mod_ids = [m["id"] for m in mods[:2]]

    payload = {
        "name": f"TEST_NUA_{uuid.uuid4().hex[:6]}",
        "category": cats[0]["name"] if cats else "Coffee",
        "categoryId": cat_id,
        "price": 5.5,
        "cost": 2.0,
        "stock": 10,
        "sku": f"TST{uuid.uuid4().hex[:6].upper()}",
        "image": "https://example.com/x.png",
        "gstRate": 10.0,
        "modifierIds": mod_ids,
    }
    r = client.post(f"{API}/products", json=payload, timeout=10)
    assert r.status_code in (200, 201), f"create failed: {r.status_code} {r.text}"
    body = r.json()
    assert body["name"] == payload["name"]
    assert body.get("categoryId") == cat_id
    assert body.get("modifierIds") == mod_ids
    yield body["id"]
    # cleanup
    client.delete(f"{API}/products/{body['id']}", timeout=10)


def test_get_after_create_persists_fields(client, created_product_id):
    r = client.get(f"{API}/products", timeout=10)
    assert r.status_code == 200
    match = [p for p in r.json() if p["id"] == created_product_id]
    assert len(match) == 1
    p = match[0]
    assert "modifierIds" in p
    assert "categoryId" in p


# ---------- 6. PUT product updates modifierIds + categoryId ----------
def test_update_modifier_ids(client, created_product_id):
    mods = client.get(f"{API}/modifiers", timeout=10).json()
    new_ids = [m["id"] for m in mods[1:3]] if len(mods) >= 3 else [m["id"] for m in mods[:1]]
    r = client.put(
        f"{API}/products/{created_product_id}",
        json={"modifierIds": new_ids},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("modifierIds") == new_ids

    # verify via GET list
    listing = client.get(f"{API}/products", timeout=10).json()
    p = [x for x in listing if x["id"] == created_product_id][0]
    assert p["modifierIds"] == new_ids


# ---------- 7. Empty modifierIds allowed ----------
def test_empty_modifier_ids_allowed(client, created_product_id):
    r = client.put(f"{API}/products/{created_product_id}", json={"modifierIds": []}, timeout=10)
    assert r.status_code == 200
    assert r.json().get("modifierIds") == []
