"""Iteration 30 — Inventory & Accounting (ingredients, recipes, invoices, stock-take, BAS, notifications)."""
import os
import pytest
import requests
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/') or "http://localhost:8001"
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- ingredients ----------
def test_create_ingredient_g(H):
    name = f"TEST_Coffee_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/ingredients", json={
        "name": name, "baseUnit": "g", "stock": 5000, "unitCost": 0.05,
        "reorderLevel": 1000, "supplierName": "TEST_Roaster"
    }, headers=H)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["baseUnit"] == "g"
    assert d["stock"] == 5000
    assert d["id"].startswith("ING-")
    pytest.coffee_id = d["id"]


def test_create_ingredient_ml(H):
    name = f"TEST_Milk_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/ingredients", json={
        "name": name, "baseUnit": "mL", "stock": 10000, "unitCost": 0.002,
        "reorderLevel": 2000
    }, headers=H)
    assert r.status_code == 200
    pytest.milk_id = r.json()["id"]


def test_reject_invalid_base_unit(H):
    r = requests.post(f"{API}/ingredients", json={
        "name": "TEST_Bad", "baseUnit": "litre", "stock": 1
    }, headers=H)
    assert r.status_code == 400
    assert "baseUnit" in r.json().get("detail", "")


def test_update_ingredient(H):
    r = requests.put(f"{API}/ingredients/{pytest.coffee_id}",
                     json={"unitCost": 0.06}, headers=H)
    assert r.status_code == 200
    assert r.json()["updated"] is True


def test_low_stock_filter(H):
    # Create an ingredient with stock <= reorderLevel
    name = f"TEST_LowItem_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/ingredients", json={
        "name": name, "baseUnit": "g", "stock": 50, "unitCost": 0.1,
        "reorderLevel": 100
    }, headers=H)
    assert r.status_code == 200
    low_id = r.json()["id"]

    r2 = requests.get(f"{API}/ingredients/low-stock", headers=H)
    assert r2.status_code == 200
    rows = r2.json()
    ids = [x["id"] for x in rows]
    assert low_id in ids
    # Every row must have stock <= reorderLevel and reorderLevel > 0
    for row in rows:
        assert row["stock"] <= row["reorderLevel"]
        assert row["reorderLevel"] > 0
    requests.delete(f"{API}/ingredients/{low_id}", headers=H)


# ---------- recipes ----------
def test_recipe_kg_to_g_conversion_and_cost(H):
    # Use first existing product
    pr = requests.get(f"{API}/products", headers=H)
    assert pr.status_code == 200
    products = pr.json()
    assert len(products) > 0
    pytest.test_product_id = products[0]["id"]

    body = {"lines": [
        {"ingredientId": pytest.coffee_id, "qty": 0.018, "unit": "kg"},   # 18g
        {"ingredientId": pytest.milk_id,   "qty": 0.25,  "unit": "L"},    # 250mL
    ]}
    r = requests.put(f"{API}/recipes/product/{pytest.test_product_id}",
                     json=body, headers=H)
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["lines"]) == 2
    # kg→g: 0.018kg => 18g
    line_c = next(l for l in d["lines"] if l["ingredientId"] == pytest.coffee_id)
    assert abs(line_c["qtyBase"] - 18.0) < 0.001
    # L→mL: 0.25L => 250mL
    line_m = next(l for l in d["lines"] if l["ingredientId"] == pytest.milk_id)
    assert abs(line_m["qtyBase"] - 250.0) < 0.001
    # cost = 18 * 0.06 + 250 * 0.002 = 1.08 + 0.5 = 1.58
    assert abs(d["computedCost"] - 1.58) < 0.01

    # Product cost was pushed back
    pr2 = requests.get(f"{API}/products", headers=H).json()
    p = next(x for x in pr2 if x["id"] == pytest.test_product_id)
    assert abs(p["cost"] - 1.58) < 0.01


def test_recipe_rejects_incompatible_conversion(H):
    # g (weight) → mL (volume) is invalid
    body = {"lines": [
        {"ingredientId": pytest.milk_id, "qty": 10, "unit": "g"},  # incompatible
    ]}
    r = requests.put(f"{API}/recipes/product/{pytest.test_product_id}",
                     json=body, headers=H)
    assert r.status_code == 400


# ---------- POS deducts ingredient stock ----------
def test_pos_sale_deducts_ingredient_stock(H):
    # Re-save the valid recipe (previous test left it intact since the failure was before update)
    body = {"lines": [
        {"ingredientId": pytest.coffee_id, "qty": 0.018, "unit": "kg"},
        {"ingredientId": pytest.milk_id,   "qty": 0.25,  "unit": "L"},
    ]}
    requests.put(f"{API}/recipes/product/{pytest.test_product_id}", json=body, headers=H)

    # Get pre-sale stock for both ingredients
    ings = requests.get(f"{API}/ingredients", headers=H).json()
    pre_coffee = next(i for i in ings if i["id"] == pytest.coffee_id)["stock"]
    pre_milk = next(i for i in ings if i["id"] == pytest.milk_id)["stock"]

    # Sell 2x of the product
    pr = requests.get(f"{API}/products", headers=H).json()
    prod = next(p for p in pr if p["id"] == pytest.test_product_id)
    txn_body = {
        "items": [{"productId": prod["id"], "name": prod["name"], "productName": prod["name"],
                   "price": prod["price"], "quantity": 2, "category": prod.get("category", "")}],
        "paymentMethod": "cash", "location": "Main", "cashier": "Owner"
    }
    rt = requests.post(f"{API}/transactions", json=txn_body, headers=H)
    assert rt.status_code == 200, rt.text

    # Verify ingredient deduction: -36g coffee, -500mL milk
    ings2 = requests.get(f"{API}/ingredients", headers=H).json()
    post_coffee = next(i for i in ings2 if i["id"] == pytest.coffee_id)["stock"]
    post_milk = next(i for i in ings2 if i["id"] == pytest.milk_id)["stock"]
    assert abs((pre_coffee - post_coffee) - 36.0) < 0.001, f"coffee delta {pre_coffee-post_coffee}"
    assert abs((pre_milk - post_milk) - 500.0) < 0.001, f"milk delta {pre_milk-post_milk}"


# ---------- invoice -> ingredient assignment with weighted moving average ----------
def test_invoice_assign_stock_wma(H):
    # Seed a minimal invoice doc directly (parse-invoice is LLM-driven; we don't need OCR for this test)
    from pymongo import MongoClient
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "test_database")
    client = MongoClient(mongo_url)
    inv_id = f"INV-TEST-{uuid.uuid4().hex[:6]}"
    client[db_name].invoices.insert_one({
        "id": inv_id, "uploadedAt": datetime.now(timezone.utc).isoformat(),
        "parsed": {"supplier": "TEST_Sup", "invoiceNumber": "TI-1", "total": 60.0},
        "applied": True, "matches": [],
    })

    # Get pre state
    ings = requests.get(f"{API}/ingredients", headers=H).json()
    pre = next(i for i in ings if i["id"] == pytest.coffee_id)
    prev_stock, prev_cost = pre["stock"], pre["unitCost"]

    # Assign 1kg @ $60 → 1000g new at $0.06/g; combined with prev should weighted average
    r = requests.post(f"{API}/invoices/{inv_id}/assign-stock", json={
        "assignments": [{"ingredientId": pytest.coffee_id, "qty": 1, "unit": "kg", "lineTotal": 60.0}]
    }, headers=H)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["movements"]) == 1
    mv = body["movements"][0]
    assert mv["qtyBase"] == 1000.0
    assert mv["type"] == "receive"

    # Verify ingredient updated
    ings2 = requests.get(f"{API}/ingredients", headers=H).json()
    post = next(i for i in ings2 if i["id"] == pytest.coffee_id)
    assert abs(post["stock"] - (prev_stock + 1000.0)) < 0.01
    expected_wma = ((prev_stock * prev_cost) + 60.0) / (prev_stock + 1000.0)
    assert abs(post["unitCost"] - round(expected_wma, 4)) < 0.001

    # Recipes were re-rolled (cascade)
    assert body["recipesRolledUp"] >= 1

    client.close()


# ---------- stock-take ----------
def test_stock_take_variance(H):
    ings = requests.get(f"{API}/ingredients", headers=H).json()
    pre_coffee = next(i for i in ings if i["id"] == pytest.coffee_id)
    counted = pre_coffee["stock"] - 50  # simulate shrinkage 50g
    r = requests.post(f"{API}/stock-takes", json={
        "counts": [{"ingredientId": pytest.coffee_id, "countedBase": counted}],
        "notes": "TEST_stocktake"
    }, headers=H)
    assert r.status_code == 200
    d = r.json()
    assert d["id"].startswith("STK-")
    assert len(d["variances"]) == 1
    v = d["variances"][0]
    assert abs(v["variance"] - (-50.0)) < 0.01
    # shrinkage should be > 0 (variance * unitCost negated)
    assert d["totalShrinkageValue"] < 0


# ---------- BAS ----------
def test_bas_report_window(H):
    r = requests.get(f"{API}/accounting/bas",
                     params={"monthStart": "2026-05-01", "monthEnd": "2026-06-30"}, headers=H)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("g1TotalSales", "oneA_gstOnSales", "g11TotalPurchases",
              "oneB_gstCredits", "netGstPayable", "salesCount", "purchasesCount"):
        assert k in d
    # 1A = total/11 invariant
    assert abs(d["oneA_gstOnSales"] - round(d["g1TotalSales"] / 11.0, 2)) < 0.02
    # net = 1A - 1B
    assert abs(d["netGstPayable"] - round(d["oneA_gstOnSales"] - d["oneB_gstCredits"], 2)) < 0.02


def test_bas_csv_download(H):
    r = requests.get(f"{API}/accounting/bas.csv",
                     params={"fy": 2026, "quarter": "Q3"}, headers=H)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "attachment" in r.headers.get("content-disposition", "")
    assert "G1 Total sales" in r.text


# ---------- online order notification fallback (no SendGrid/Twilio) ----------
def test_online_order_notify_no_keys():
    # Public placement
    r = requests.post(f"{API}/online/orders", json={
        "customerName": "TEST_NotifyBuyer", "customerEmail": "test@example.com",
        "customerPhone": "+61400000000",
        "channel": "pickup",
        "items": [{"productId": "x", "name": "Long Black", "price": 5, "quantity": 1, "category": "Coffee"}]
    })
    assert r.status_code == 200, r.text
    order = r.json()
    assert "deliveryReceipts" in order
    # Both channels should report not_configured
    assert isinstance(order["deliveryReceipts"], list)
    for receipt in order["deliveryReceipts"]:
        assert receipt["delivered"] is False
        assert receipt["reason"] == "not_configured"


def test_online_status_update_notify_no_keys(H):
    # Place order then patch status — should not crash + return not_configured
    r = requests.post(f"{API}/online/orders", json={
        "customerName": "TEST_StatusBuyer", "customerEmail": "test2@example.com",
        "channel": "pickup",
        "items": [{"productId": "y", "name": "Long Black", "price": 5, "quantity": 1, "category": "Coffee"}]
    })
    assert r.status_code == 200
    order_id = r.json()["id"]

    r2 = requests.patch(f"{API}/online/orders/{order_id}/status",
                        json={"status": "accepted"}, headers=H)
    assert r2.status_code == 200
    updated = r2.json()
    assert updated["status"] == "accepted"
    assert "deliveryReceipts" in updated
    # New receipts from this status update appended
    not_configured_count = sum(
        1 for x in updated["deliveryReceipts"] if x.get("reason") == "not_configured")
    assert not_configured_count >= 1


# ---------- cleanup ----------
def test_delete_blocks_when_in_recipe(H):
    r = requests.delete(f"{API}/ingredients/{pytest.coffee_id}", headers=H)
    assert r.status_code == 400
    assert "recipe" in r.json().get("detail", "").lower()


def test_zzz_cleanup(H):
    # Remove recipe + ingredients
    requests.put(f"{API}/recipes/product/{pytest.test_product_id}",
                 json={"lines": []}, headers=H)
    requests.delete(f"{API}/ingredients/{pytest.coffee_id}", headers=H)
    requests.delete(f"{API}/ingredients/{pytest.milk_id}", headers=H)
