"""Two gift-card money endpoints had no role check at all — any logged-in
cashier could mint an arbitrary-value gift card (POST /gift-cards/schedule)
or top up an existing one by any amount (POST /gift-cards/{id}/reload).
Every sibling endpoint that mints value (POST /vouchers, POST
/vouchers/bulk) requires owner/manager; these two were the odd ones out.
"""
from conftest import req


def _cashier_headers(client, owner_headers, email="giftcard.cashier@nua.com"):
    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Gift Card Cashier", "email": email,
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={"email": email, "password": "CashierPass1!"}).json()
    client.cookies.clear()
    return {"Authorization": f"Bearer {tok['token']}"}


def test_scheduling_a_gift_card_requires_owner_or_manager(client, owner_headers):
    ch = _cashier_headers(client, owner_headers)
    r = req(client, "POST", "/api/gift-cards/schedule", headers=ch, json={
        "amount": 500, "deliverAt": "2026-12-25", "recipientEmail": "guest@example.com"})
    assert r.status_code == 403

    r = req(client, "POST", "/api/gift-cards/schedule", headers=owner_headers, json={
        "amount": 50, "deliverAt": "2026-12-25", "recipientEmail": "guest@example.com"})
    assert r.status_code == 200, r.text[:200]


def test_reloading_a_gift_card_requires_owner_or_manager(client, owner_headers):
    created = req(client, "POST", "/api/gift-cards/schedule", headers=owner_headers, json={
        "amount": 25, "deliverAt": "2026-12-25", "recipientEmail": "guest2@example.com"})
    voucher_id = created.json()["id"]

    ch = _cashier_headers(client, owner_headers, email="giftcard.cashier2@nua.com")
    r = req(client, "POST", f"/api/gift-cards/{voucher_id}/reload", headers=ch, json={"amount": 10000})
    assert r.status_code == 403

    r = req(client, "POST", f"/api/gift-cards/{voucher_id}/reload", headers=owner_headers, json={"amount": 10})
    assert r.status_code == 200, r.text[:200]
    assert r.json()["newBalance"] == 35
