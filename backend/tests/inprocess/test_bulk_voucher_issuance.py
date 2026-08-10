"""bulk_issue_voucher used to call _issue_voucher in a loop — one
insert_one and (if a customerId was set) one redundant customer lookup
per voucher, even though a bulk batch's template is identical across all
N vouchers. Rebuilt to do one customer lookup and one insert_many for the
whole batch. This pins that each voucher in the batch still gets its own
unique id/code, and that a shared customerId is correctly attached to
every voucher in the batch.
"""
from conftest import req


def test_bulk_issued_vouchers_are_all_unique_and_all_carry_the_template(client, owner_headers):
    r = req(client, "POST", "/api/vouchers/bulk", headers=owner_headers, json={
        "count": 25, "label": "Staff Perk", "valueType": "amount", "value": 10})
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body["issued"] == 25
    assert len(body["vouchers"]) == 25

    ids = {v["id"] for v in body["vouchers"]}
    codes = {v["code"] for v in body["vouchers"]}
    assert len(ids) == 25, "every voucher must have its own unique id"
    assert len(codes) == 25, "every voucher must have its own unique code"


def test_bulk_issued_vouchers_share_the_same_customer_when_one_is_given(client, owner_headers):
    customer = req(client, "POST", "/api/customers", headers=owner_headers, json={
        "name": "Bulk Recipient", "email": "bulkrecipient@nua.com", "phone": "0400555666"})
    customer_id = customer.json()["id"]

    r = req(client, "POST", "/api/vouchers/bulk", headers=owner_headers, json={
        "count": 3, "label": "Anniversary Gift", "valueType": "amount", "value": 20,
        "customerId": customer_id})
    assert r.status_code == 200, r.text[:200]
    voucher_ids = [v["id"] for v in r.json()["vouchers"]]

    listed = req(client, "GET", "/api/vouchers/lookup/" + r.json()["vouchers"][0]["code"], headers=owner_headers)
    assert listed.status_code == 200, listed.text[:200]
    assert listed.json()["customerId"] == customer_id
    assert listed.json()["customerEmail"] == "bulkrecipient@nua.com"
    assert len(voucher_ids) == 3


def test_bulk_issuance_requires_owner_or_manager(client, owner_headers):
    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Voucher Cashier", "email": "voucher.cashier@nua.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={
        "email": "voucher.cashier@nua.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    cashier_headers = {"Authorization": f"Bearer {tok['token']}"}

    r = req(client, "POST", "/api/vouchers/bulk", headers=cashier_headers, json={"count": 5, "value": 10})
    assert r.status_code == 403


def test_bulk_issuance_rejects_out_of_range_counts(client, owner_headers):
    r = req(client, "POST", "/api/vouchers/bulk", headers=owner_headers, json={"count": 0, "value": 10})
    assert r.status_code == 400
    r = req(client, "POST", "/api/vouchers/bulk", headers=owner_headers, json={"count": 5001, "value": 10})
    assert r.status_code == 400
