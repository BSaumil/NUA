"""POST /products/{id}/adjust-stock had no role check at all — any logged-in
cashier could arbitrarily inflate or deplete a product's stock count, unlike
every other stock-mutating endpoint (inventory_accounting.py's ingredient
adjustments) which already required owner/manager.
"""
from conftest import req


def test_adjusting_stock_requires_owner_or_manager(client, owner_headers):
    created = req(client, "POST", "/api/products", headers=owner_headers, json={
        "name": "Stock Test Widget", "price": 5, "cost": 2, "category": "Test",
        "stock": 10, "sku": "STOCK-TEST-1"})
    assert created.status_code == 200, created.text[:200]
    product_id = created.json()["id"]

    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Stock Cashier", "email": "stock.cashier@nua.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={
        "email": "stock.cashier@nua.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    cashier_headers = {"Authorization": f"Bearer {tok['token']}"}

    r = req(client, "POST", f"/api/products/{product_id}/adjust-stock", headers=cashier_headers,
            json={"adjustment": 500, "reason": "self-serve restock"})
    assert r.status_code == 403

    r = req(client, "POST", f"/api/products/{product_id}/adjust-stock", headers=owner_headers,
            json={"adjustment": 5, "reason": "owner restock"})
    assert r.status_code == 200, r.text[:200]
    assert r.json()["newStock"] == 15
