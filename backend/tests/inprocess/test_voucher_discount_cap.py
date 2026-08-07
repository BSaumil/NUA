"""A voucher-linked POS discount trusted the client's dollar amount: nothing
compared d["amount"] against the voucher's own value before it was baked
into the transaction total, so an inflated amount would just be honoured.
Worse, once "consumed" the voucher was stamped status="used" — a value
_validate_voucher_rules (commerce_v29.py) never checks, since the rest of
the voucher lifecycle only ever writes "redeemed"/"partial"/"expired" —
so a spent voucher stayed eligible for a second, full-value redemption
through /vouchers/redeem. Both are fixed together: the discount is capped
to the voucher's real value before the sale is priced, and the voucher is
now marked "redeemed" so every other code path that checks status agrees
it's spent.
"""
from conftest import req


def _sale(client, headers, *, amount, voucher_id):
    return req(client, "POST", "/api/transactions", headers=headers, json={
        "items": [{"productId": "no-such-product", "productName": "Custom item",
                   "quantity": 1, "price": 100}],
        "paymentMethod": "cash", "location": "Main", "cashier": "Test Cashier",
        "appliedDiscounts": [{"label": "Voucher", "amount": amount, "voucherId": voucher_id}],
    })


def test_a_voucher_discount_is_capped_to_the_vouchers_real_value(client, owner_headers):
    issued = req(client, "POST", "/api/vouchers", headers=owner_headers, json={
        "label": "Test $20 off", "valueType": "amount", "value": 20})
    assert issued.status_code == 200, issued.text[:200]
    voucher_id = issued.json()["id"]

    # Client asks for $9000 off a $100 item against a voucher only worth $20.
    r = _sale(client, owner_headers, amount=9000, voucher_id=voucher_id)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body["appliedDiscounts"][0]["amount"] == 20
    assert body["total"] > 0, "a $9000 discount on a $100 item must not zero out (or go negative on) the bill"


def test_a_redeemed_voucher_cannot_be_applied_again(client, owner_headers):
    issued = req(client, "POST", "/api/vouchers", headers=owner_headers, json={
        "label": "Test $15 off", "valueType": "amount", "value": 15})
    voucher_id = issued.json()["id"]

    first = _sale(client, owner_headers, amount=15, voucher_id=voucher_id)
    assert first.status_code == 200, first.text[:200]
    assert first.json()["appliedDiscounts"][0]["amount"] == 15

    # Same voucher, second sale — must not be honoured a second time.
    second = _sale(client, owner_headers, amount=15, voucher_id=voucher_id)
    assert second.status_code == 200, second.text[:200]
    assert second.json()["appliedDiscounts"][0]["amount"] == 0


def test_a_used_wallet_voucher_is_rejected_by_the_vouchers_redeem_endpoint_too(client, owner_headers):
    """This is the actual cross-path bug: status="used" (the old value) was
    invisible to _validate_voucher_rules, which only rejects "expired",
    "revoked" and "redeemed". Confirm the new status value closes that."""
    issued = req(client, "POST", "/api/vouchers", headers=owner_headers, json={
        "label": "Test $10 off", "valueType": "amount", "value": 10})
    voucher = issued.json()
    voucher_id, code = voucher["id"], voucher["code"]

    spent = _sale(client, owner_headers, amount=10, voucher_id=voucher_id)
    assert spent.status_code == 200
    assert spent.json()["appliedDiscounts"][0]["amount"] == 10

    redeem_again = req(client, "POST", "/api/vouchers/redeem", headers=owner_headers,
                        json={"code": code, "amount": 10})
    assert redeem_again.status_code == 400
    assert "redeemed" in redeem_again.json()["detail"].lower()
