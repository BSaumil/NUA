"""Deposits and Budgets each had a one-way door: a deposit could be taken and
applied but never refunded (no endpoint existed even though the model's
`status` field already had a "refunded" value nothing could ever set), and a
budget could be created but never edited or deleted. Both are ordinary
data-entry mistakes an owner needs to be able to correct — a cancelled
booking's deposit has to go back to the customer, a budget line typo has to
be fixable without deleting and recreating the whole year.
"""
from conftest import req


def _seed_coa(client, owner_headers):
    req(client, "POST", "/api/accounting/seed", headers=owner_headers)


def test_a_held_deposit_can_be_refunded_but_not_refunded_twice(client, owner_headers):
    created = req(client, "POST", "/api/accounting/deposits", headers=owner_headers, json={
        "customerId": "cust-1", "customerName": "Jane Diner", "bookingId": "bk-1",
        "amount": 200, "receivedAt": "2026-08-01", "method": "card"})
    assert created.status_code == 200, created.text[:200]
    dep_id = created.json()["id"]

    refunded = req(client, "POST", f"/api/accounting/deposits/{dep_id}/refund", headers=owner_headers)
    assert refunded.status_code == 200, refunded.text[:200]

    listed = req(client, "GET", "/api/accounting/deposits", headers=owner_headers).json()
    row = next(d for d in listed if d["id"] == dep_id)
    assert row["status"] == "refunded"

    again = req(client, "POST", f"/api/accounting/deposits/{dep_id}/refund", headers=owner_headers)
    assert again.status_code == 400


def test_refunding_a_deposit_requires_owner_or_manager(client, owner_headers):
    created = req(client, "POST", "/api/accounting/deposits", headers=owner_headers, json={
        "customerId": "cust-2", "customerName": "Sam Guest", "amount": 50,
        "receivedAt": "2026-08-01", "method": "cash"})
    dep_id = created.json()["id"]

    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Deposit Cashier", "email": "deposit.cashier@nua.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={
        "email": "deposit.cashier@nua.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    cashier_headers = {"Authorization": f"Bearer {tok['token']}"}

    r = req(client, "POST", f"/api/accounting/deposits/{dep_id}/refund", headers=cashier_headers)
    assert r.status_code == 403


def test_a_budget_can_be_edited_and_deleted(client, owner_headers):
    _seed_coa(client, owner_headers)

    created = req(client, "POST", "/api/accounting/budgets", headers=owner_headers, json={
        "name": "FY26 Budget", "fyStart": "2026-07-01", "fyEnd": "2027-06-30",
        "lines": [{"accountCode": "6100", "monthlyAmount": 1000}]})
    assert created.status_code == 200, created.text[:200]
    budget_id = created.json()["id"]

    updated = req(client, "PUT", f"/api/accounting/budgets/{budget_id}", headers=owner_headers, json={
        "name": "FY26 Budget (revised)",
        "lines": [{"accountCode": "6100", "monthlyAmount": 1200}]})
    assert updated.status_code == 200, updated.text[:200]
    assert updated.json()["name"] == "FY26 Budget (revised)"
    assert updated.json()["lines"][0]["monthlyAmount"] == 1200
    # fyStart/fyEnd weren't in the PUT body — must survive untouched.
    assert updated.json()["fyStart"] == "2026-07-01"

    deleted = req(client, "DELETE", f"/api/accounting/budgets/{budget_id}", headers=owner_headers)
    assert deleted.status_code == 200

    listed = req(client, "GET", "/api/accounting/budgets", headers=owner_headers).json()
    assert all(b["id"] != budget_id for b in listed)

    again = req(client, "DELETE", f"/api/accounting/budgets/{budget_id}", headers=owner_headers)
    assert again.status_code == 404


def test_editing_and_deleting_a_budget_requires_owner_or_manager(client, owner_headers):
    _seed_coa(client, owner_headers)
    created = req(client, "POST", "/api/accounting/budgets", headers=owner_headers, json={
        "name": "Locked Budget", "fyStart": "2026-07-01", "fyEnd": "2027-06-30",
        "lines": [{"accountCode": "6100", "monthlyAmount": 500}]})
    budget_id = created.json()["id"]

    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Budget Cashier", "email": "budget.cashier@nua.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={
        "email": "budget.cashier@nua.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    cashier_headers = {"Authorization": f"Bearer {tok['token']}"}

    r = req(client, "PUT", f"/api/accounting/budgets/{budget_id}", headers=cashier_headers, json={"name": "Hacked"})
    assert r.status_code == 403
    r = req(client, "DELETE", f"/api/accounting/budgets/{budget_id}", headers=cashier_headers)
    assert r.status_code == 403
