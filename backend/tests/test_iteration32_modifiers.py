"""
Iteration 32 — Verify POS modifier flow round-trip persists
TransactionItem.modifiers correctly to backend.
"""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or os.environ["REACT_APP_BACKEND_URL"]
BASE_URL = BASE_URL.rstrip("/")

OWNER_EMAIL = "owner@nuva.com"
OWNER_PASSWORD = "NuvaOwner2026!"


@pytest.fixture(scope="module")
def auth_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Auth failed: {r.status_code} {r.text}")
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="module")
def headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"} if auth_token else {}


# ----- products + modifiers existence -----
def test_modifiers_endpoint_returns_list():
    r = requests.get(f"{BASE_URL}/api/modifiers", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0, "no modifier defs"


def test_flat_white_has_modifier_ids():
    r = requests.get(f"{BASE_URL}/api/products", timeout=15)
    assert r.status_code == 200
    items = r.json()
    fw = next((p for p in items if p.get("name", "").lower() == "flat white"), None)
    assert fw is not None, "Flat White product missing"
    assert isinstance(fw.get("modifierIds"), list) and len(fw["modifierIds"]) > 0, \
        f"Flat White has no modifierIds: {fw.get('modifierIds')}"


def test_create_transaction_persists_modifiers(headers):
    """POST /api/transactions with modifiers array → verify GET returns them."""
    products = requests.get(f"{BASE_URL}/api/products", timeout=15).json()
    mods = requests.get(f"{BASE_URL}/api/modifiers", timeout=15).json()

    fw = next((p for p in products if p.get("name", "").lower() == "flat white"), None)
    assert fw is not None
    # pick a modifier with options
    target_mod = next((m for m in mods if m.get("id") in (fw.get("modifierIds") or []) and (m.get("options") or [])), None)
    if target_mod is None:
        # fallback: any mod with options
        target_mod = next((m for m in mods if m.get("options")), None)
    assert target_mod is not None, "no modifier with options available"
    opt = target_mod["options"][0]

    selected_mod = {
        "modifierId": target_mod["id"],
        "modifierName": target_mod["name"],
        "optionId": opt["name"],
        "optionName": opt["name"],
        "price": float(opt.get("price") or 0),
    }

    payload = {
        "items": [{
            "productId": fw["id"],
            "productName": fw["name"],
            "quantity": 1,
            "price": float(fw["price"]) + float(opt.get("price") or 0),
            "modifiers": [selected_mod],
        }],
        "paymentMethod": "Cash",
        "location": "TEST_LOC",
        "cashier": "TEST_iter32",
    }
    r = requests.post(f"{BASE_URL}/api/transactions", json=payload, headers=headers, timeout=20)
    assert r.status_code in (200, 201), f"create tx failed: {r.status_code} {r.text}"
    body = r.json()
    tx_id = body.get("id")
    assert tx_id, f"no tx id in response: {body}"

    # Persistence: GET by id or list, find tx and confirm modifiers present
    r2 = requests.get(f"{BASE_URL}/api/transactions/{tx_id}", headers=headers, timeout=15)
    if r2.status_code == 404:
        # fallback to list endpoint
        r2 = requests.get(f"{BASE_URL}/api/transactions", headers=headers, timeout=20)
        assert r2.status_code == 200
        all_tx = r2.json()
        fetched = next((t for t in all_tx if t.get("id") == tx_id), None)
        assert fetched, "tx not found in list"
    else:
        assert r2.status_code == 200, f"GET tx failed: {r2.status_code} {r2.text}"
        fetched = r2.json()

    assert "_id" not in fetched, "Mongo _id leaked"
    items = fetched.get("items") or []
    assert len(items) == 1
    item_mods = items[0].get("modifiers") or []
    assert len(item_mods) >= 1, f"modifiers not persisted: {items[0]}"
    sm = item_mods[0]
    assert sm["modifierId"] == target_mod["id"]
    assert sm["modifierName"] == target_mod["name"]
    assert sm["optionName"] == opt["name"]


def test_create_transaction_without_modifiers_still_works(headers):
    """Ensure legacy items (no modifiers) still create successfully."""
    products = requests.get(f"{BASE_URL}/api/products", timeout=15).json()
    legacy = next((p for p in products if not (p.get("modifierIds") or [])), None)
    if legacy is None:
        pytest.skip("no product without modifiers")
    payload = {
        "items": [{
            "productId": legacy["id"],
            "productName": legacy["name"],
            "quantity": 1,
            "price": float(legacy["price"]),
            "modifiers": [],
        }],
        "paymentMethod": "Cash",
        "location": "TEST_LOC",
        "cashier": "TEST_iter32_legacy",
    }
    r = requests.post(f"{BASE_URL}/api/transactions", json=payload, headers=headers, timeout=20)
    assert r.status_code in (200, 201), f"{r.status_code} {r.text}"
    body = r.json()
    assert body.get("id")
    assert body["items"][0].get("modifiers", []) == []
