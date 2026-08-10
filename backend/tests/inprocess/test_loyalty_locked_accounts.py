"""Confirming a point-farming fraud flag sets customers.loyaltyLocked=true
(routes/loyalty_engine.py's resolve_fraud_flag), and an unlock endpoint
already existed to reverse it — but nothing ever listed WHO was locked, so
the unlock endpoint had no way to be reached from the UI without already
knowing the customerId. Added GET /loyalty/reports/locked-accounts as the
missing other half.
"""
import asyncio

from conftest import req


def test_locked_accounts_report_lists_locked_customers_and_unlock_clears_them(client, owner_headers):
    created = req(client, "POST", "/api/customers", headers=owner_headers, json={
        "name": "Farmer Customer", "email": "farmer@nua.com", "phone": "0400000000"})
    assert created.status_code == 200, created.text[:200]
    customer_id = created.json()["id"]

    loop = asyncio.get_event_loop()
    from database import db
    loop.run_until_complete(db.customers.update_one(
        {"id": customer_id}, {"$set": {"loyaltyLocked": True, "points": 250}}))

    r = req(client, "GET", "/api/loyalty/reports/locked-accounts", headers=owner_headers)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert any(a["id"] == customer_id for a in body["accounts"])

    unlocked = req(client, "POST", f"/api/loyalty/customers/{customer_id}/unlock", headers=owner_headers)
    assert unlocked.status_code == 200, unlocked.text[:200]

    r2 = req(client, "GET", "/api/loyalty/reports/locked-accounts", headers=owner_headers)
    assert all(a["id"] != customer_id for a in r2.json()["accounts"])


def test_locked_accounts_report_requires_owner_or_manager(client, owner_headers):
    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Loyalty Cashier", "email": "loyalty.cashier@nua.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={
        "email": "loyalty.cashier@nua.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    cashier_headers = {"Authorization": f"Bearer {tok['token']}"}

    r = req(client, "GET", "/api/loyalty/reports/locked-accounts", headers=cashier_headers)
    assert r.status_code == 403
