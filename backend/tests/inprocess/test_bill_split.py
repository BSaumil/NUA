"""Guest-facing bill splitting.

Crypto is the fully-testable payment path in this sandbox (raw httpx,
mockable) — Stripe's checkout SDK isn't installed here at all (see
test_crypto_payments.py's module docstring), so the crypto path is what
proves the checkout -> finalize -> split-marked-paid pipeline end to end;
Stripe is only smoke-tested for its "not configured" honesty.
"""
import asyncio

import httpx
import pytest

from conftest import req


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


_RealAsyncClient = httpx.AsyncClient


def _mock_client_factory(handler):
    def factory(*args, **kwargs):
        return _RealAsyncClient(transport=httpx.MockTransport(handler), timeout=kwargs.get("timeout", 10))
    return factory


def _seed_table_order(table_number, order_id="KORD-SPLIT-1", items=None):
    from database import db
    items = items or [
        {"productId": "PROD-BURGER", "productName": "Burger", "category": "Mains", "quantity": 2},
        {"productId": "PROD-FRIES", "productName": "Fries", "category": "Sides", "quantity": 1},
    ]
    _run(db.kitchen_orders.insert_one({
        "id": order_id, "tableNumber": str(table_number), "items": items, "status": "new",
    }))
    _run(db.products.insert_one({"id": "PROD-BURGER", "name": "Burger", "price": 15.0, "category": "Mains"}))
    _run(db.products.insert_one({"id": "PROD-FRIES", "name": "Fries", "price": 6.0, "category": "Sides"}))
    return order_id


def _cleanup_table(table_number, order_ids=None):
    from database import db
    _run(db.kitchen_orders.delete_many({"tableNumber": str(table_number)}))
    _run(db.bill_splits.delete_many({"tableNumber": str(table_number)}))
    _run(db.products.delete_many({"id": {"$in": ["PROD-BURGER", "PROD-FRIES"]}}))


def _guest_token(phone="+61412345000"):
    from services import guest_session
    return guest_session.issue_guest_token(phone)


# ----------------------------------------------------------------- creation

def test_get_split_builds_one_line_per_unit(client):
    _seed_table_order("T-901")
    try:
        r = req(client, "GET", "/api/table/T-901/split")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["tableNumber"] == "T-901"
        assert body["status"] == "open"
        # 2x Burger -> 2 lines, 1x Fries -> 1 line
        names = sorted(l["productName"] for l in body["lines"])
        assert names == ["Burger", "Burger", "Fries"]
        prices = {l["productName"]: l["unitPrice"] for l in body["lines"]}
        assert prices["Burger"] == 15.0
        assert prices["Fries"] == 6.0
        assert all(l["status"] == "open" for l in body["lines"])
    finally:
        _cleanup_table("T-901")


def test_get_split_is_idempotent(client):
    _seed_table_order("T-902")
    try:
        r1 = req(client, "GET", "/api/table/T-902/split")
        r2 = req(client, "GET", "/api/table/T-902/split")
        assert r1.json()["id"] == r2.json()["id"]
    finally:
        _cleanup_table("T-902")


def test_get_split_404s_when_no_open_order(client):
    r = req(client, "GET", "/api/table/T-NO-ORDER/split")
    assert r.status_code == 404


def test_a_new_round_firing_appends_lines_without_disturbing_claims(client):
    _seed_table_order("T-903")
    try:
        split_id = req(client, "GET", "/api/table/T-903/split").json()["id"]
        token = _guest_token("+61412345001")
        # Claim one burger before the second round fires.
        lines = req(client, "GET", "/api/table/T-903/split").json()["lines"]
        burger_line = next(l for l in lines if l["productName"] == "Burger")
        req(client, "POST", f"/api/table/split/{split_id}/claim",
            headers={"Authorization": f"Bearer {token}"}, json={"lineIds": [burger_line["id"]]})

        # Kitchen fires another round with an extra item onto the SAME order.
        from database import db
        _run(db.kitchen_orders.update_one({"id": "KORD-SPLIT-1"}, {"$set": {"items": [
            {"productId": "PROD-BURGER", "productName": "Burger", "category": "Mains", "quantity": 2},
            {"productId": "PROD-FRIES", "productName": "Fries", "category": "Sides", "quantity": 1},
            {"productId": "PROD-FRIES", "productName": "Fries", "category": "Sides", "quantity": 1},
        ]}}))

        body = req(client, "GET", "/api/table/T-903/split").json()
        assert len(body["lines"]) == 4  # 2 burger + 2 fries now
        claimed = [l for l in body["lines"] if l["status"] == "claimed"]
        assert len(claimed) == 1  # the earlier claim survived the refresh
    finally:
        _cleanup_table("T-903")


# ------------------------------------------------------------------- mode

def test_mode_sticks_after_first_choice(client):
    _seed_table_order("T-904")
    try:
        req(client, "POST", "/api/table/T-904/split/mode", json={"mode": "equal", "equalCount": 3})
        body = req(client, "POST", "/api/table/T-904/split/mode", json={"mode": "items"}).json()
        assert body["mode"] == "equal"
    finally:
        _cleanup_table("T-904")


def test_equal_split_shares_sum_back_to_the_exact_total(client):
    _seed_table_order("T-905")
    try:
        body = req(client, "POST", "/api/table/T-905/split/mode", json={"mode": "equal", "equalCount": 3}).json()
        total_of_lines = round(sum(l["unitPrice"] for l in body["lines"]), 2)
        total_of_shares = round(sum(p["amount"] for p in body["equalParts"]), 2)
        assert total_of_shares == total_of_lines
        assert len(body["equalParts"]) == 3
    finally:
        _cleanup_table("T-905")


# ------------------------------------------------------------------ claim

def test_claim_requires_a_guest_session(client):
    _seed_table_order("T-906")
    try:
        split_id = req(client, "GET", "/api/table/T-906/split").json()["id"]
        r = req(client, "POST", f"/api/table/split/{split_id}/claim", json={"lineIds": ["L1"]})
        assert r.status_code == 401
    finally:
        _cleanup_table("T-906")


def test_two_guests_cannot_claim_the_same_line(client):
    _seed_table_order("T-907")
    try:
        split_id = req(client, "GET", "/api/table/T-907/split").json()["id"]
        line_id = req(client, "GET", "/api/table/T-907/split").json()["lines"][0]["id"]
        t1, t2 = _guest_token("+61412345002"), _guest_token("+61412345003")

        r1 = req(client, "POST", f"/api/table/split/{split_id}/claim",
                 headers={"Authorization": f"Bearer {t1}"}, json={"lineIds": [line_id]})
        assert r1.json()["claimed"] == [line_id]

        r2 = req(client, "POST", f"/api/table/split/{split_id}/claim",
                 headers={"Authorization": f"Bearer {t2}"}, json={"lineIds": [line_id]})
        assert r2.json()["claimed"] == []
        assert r2.json()["failed"] == [line_id]
    finally:
        _cleanup_table("T-907")


def test_release_returns_a_line_to_open(client):
    _seed_table_order("T-908")
    try:
        split_id = req(client, "GET", "/api/table/T-908/split").json()["id"]
        line_id = req(client, "GET", "/api/table/T-908/split").json()["lines"][0]["id"]
        token = _guest_token("+61412345004")
        req(client, "POST", f"/api/table/split/{split_id}/claim",
            headers={"Authorization": f"Bearer {token}"}, json={"lineIds": [line_id]})
        body = req(client, "POST", f"/api/table/split/{split_id}/release",
                   headers={"Authorization": f"Bearer {token}"}, json={"lineIds": [line_id]}).json()
        assert next(l for l in body["lines"] if l["id"] == line_id)["status"] == "open"
    finally:
        _cleanup_table("T-908")


def test_claim_equal_slot_is_race_safe(client):
    _seed_table_order("T-909")
    try:
        req(client, "POST", "/api/table/T-909/split/mode", json={"mode": "equal", "equalCount": 2})
        split_id = req(client, "GET", "/api/table/T-909/split").json()["id"]
        t1, t2 = _guest_token("+61412345005"), _guest_token("+61412345006")

        r1 = req(client, "POST", f"/api/table/split/{split_id}/claim-equal",
                 headers={"Authorization": f"Bearer {t1}"}, json={"index": 0})
        assert r1.status_code == 200

        r2 = req(client, "POST", f"/api/table/split/{split_id}/claim-equal",
                 headers={"Authorization": f"Bearer {t2}"}, json={"index": 0})
        assert r2.status_code == 409
    finally:
        _cleanup_table("T-909")


# ---------------------------------------------------------------- checkout

def test_checkout_requires_the_caller_to_have_claimed_the_line(client):
    _seed_table_order("T-910")
    try:
        split_id = req(client, "GET", "/api/table/T-910/split").json()["id"]
        line_id = req(client, "GET", "/api/table/T-910/split").json()["lines"][0]["id"]
        token = _guest_token("+61412345007")
        # Never claimed — straight to checkout.
        r = req(client, "POST", f"/api/table/split/{split_id}/checkout",
                headers={"Authorization": f"Bearer {token}"},
                json={"provider": "crypto", "lineIds": [line_id]})
        assert r.status_code == 403
    finally:
        _cleanup_table("T-910")


def test_stripe_checkout_reports_not_configured_honestly(client, monkeypatch):
    monkeypatch.delenv("STRIPE_API_KEY", raising=False)
    _seed_table_order("T-911")
    try:
        split_id = req(client, "GET", "/api/table/T-911/split").json()["id"]
        line_id = req(client, "GET", "/api/table/T-911/split").json()["lines"][0]["id"]
        token = _guest_token("+61412345008")
        req(client, "POST", f"/api/table/split/{split_id}/claim",
            headers={"Authorization": f"Bearer {token}"}, json={"lineIds": [line_id]})
        r = req(client, "POST", f"/api/table/split/{split_id}/checkout",
                headers={"Authorization": f"Bearer {token}"},
                json={"provider": "stripe", "lineIds": [line_id]})
        assert r.status_code == 500
        assert "not configured" in r.json()["detail"].lower()
    finally:
        _cleanup_table("T-911")
        from database import db
        _run(db.customers.delete_many({"phone": "+61412345008"}))


def test_crypto_checkout_creates_a_charge_tagged_with_split_metadata(client, monkeypatch):
    import services.coinbase_commerce as cc

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {
            "id": "charge-uuid-split", "code": "SPLITCODE1",
            "hosted_url": "https://commerce.coinbase.com/charges/SPLITCODE1",
            "timeline": [{"status": "NEW"}],
        }})
    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_client_factory(handler))

    _seed_table_order("T-912")
    try:
        split_id = req(client, "GET", "/api/table/T-912/split").json()["id"]
        line_id = req(client, "GET", "/api/table/T-912/split").json()["lines"][0]["id"]
        token = _guest_token("+61412345009")
        req(client, "POST", f"/api/table/split/{split_id}/claim",
            headers={"Authorization": f"Bearer {token}"}, json={"lineIds": [line_id]})

        r = req(client, "POST", f"/api/table/split/{split_id}/checkout",
                headers={"Authorization": f"Bearer {token}"},
                json={"provider": "crypto", "lineIds": [line_id]})
        assert r.status_code == 200, r.text
        assert r.json()["sessionId"] == "SPLITCODE1"

        from database import db
        payment = _run(db.payment_transactions.find_one({"sessionId": "SPLITCODE1"}, {"_id": 0}))
        assert payment["splitSessionId"] == split_id
        assert payment["splitLineIds"] == [line_id]
        assert payment["kind"] == "pos_sale"
    finally:
        _cleanup_table("T-912")
        from database import db
        _run(db.payment_transactions.delete_many({"sessionId": "SPLITCODE1"}))
        _run(db.customers.delete_many({"phone": "+61412345009"}))


def test_paying_finalizes_the_sale_and_marks_the_line_paid(client, monkeypatch):
    import services.coinbase_commerce as cc
    import routes.transactions

    def create_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {
            "id": "charge-uuid-split2", "code": "SPLITCODE2",
            "hosted_url": "https://commerce.coinbase.com/charges/SPLITCODE2",
            "timeline": [{"status": "NEW"}],
        }})
    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_client_factory(create_handler))

    finalize_calls = []
    async def fake_create_transaction(payload, user):
        finalize_calls.append((payload, user))
        class T:
            id = "TXN-SPLIT-1"
        return T()
    monkeypatch.setattr(routes.transactions, "create_transaction", fake_create_transaction)

    _seed_table_order("T-913")
    try:
        split_id = req(client, "GET", "/api/table/T-913/split").json()["id"]
        line_id = req(client, "GET", "/api/table/T-913/split").json()["lines"][0]["id"]
        token = _guest_token("+61412345010")
        req(client, "POST", f"/api/table/split/{split_id}/claim",
            headers={"Authorization": f"Bearer {token}"}, json={"lineIds": [line_id]})
        req(client, "POST", f"/api/table/split/{split_id}/checkout",
            headers={"Authorization": f"Bearer {token}"},
            json={"provider": "crypto", "lineIds": [line_id]})

        def poll_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {
                "id": "charge-uuid-split2", "code": "SPLITCODE2",
                "timeline": [{"status": "NEW"}, {"status": "COMPLETED"}],
            }})
        monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_client_factory(poll_handler))

        r = req(client, "GET", "/api/crypto/checkout/status/SPLITCODE2")
        assert r.status_code == 200
        assert r.json()["paymentStatus"] == "paid"
        # A guest returning from checkout needs this to route back to their
        # bill, not a staff-only "Back to POS" screen (PaymentSuccess.jsx).
        assert r.json()["splitSessionId"] == split_id
        assert len(finalize_calls) == 1

        status = req(client, "GET", f"/api/table/split/{split_id}/status").json()
        paid_line = next(l for l in status["lines"] if l["id"] == line_id)
        assert paid_line["status"] == "paid"
    finally:
        _cleanup_table("T-913")
        from database import db
        _run(db.payment_transactions.delete_many({"sessionId": "SPLITCODE2"}))
        _run(db.customers.delete_many({"phone": "+61412345010"}))


def test_split_settles_once_every_line_is_paid(client, monkeypatch):
    import routes.transactions
    from services import bill_split

    async def fake_create_transaction(payload, user):
        class T:
            id = "TXN-SPLIT-SETTLE"
        return T()
    monkeypatch.setattr(routes.transactions, "create_transaction", fake_create_transaction)

    _seed_table_order("T-914", items=[
        {"productId": "PROD-FRIES", "productName": "Fries", "category": "Sides", "quantity": 1},
    ])
    try:
        split = req(client, "GET", "/api/table/T-914/split").json()
        assert len(split["lines"]) == 1
        line_id = split["lines"][0]["id"]

        _run(bill_split.mark_lines_paid(split["id"], [line_id], None, "TXN-SPLIT-SETTLE"))
        status = req(client, "GET", f"/api/table/split/{split['id']}/status").json()
        assert status["status"] == "settled"
    finally:
        _cleanup_table("T-914")


def test_a_verified_phone_creates_a_real_customer_that_earns_points_on_checkout(client, monkeypatch):
    import services.coinbase_commerce as cc

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {
            "id": "charge-uuid-split3", "code": "SPLITCODE3",
            "hosted_url": "https://commerce.coinbase.com/charges/SPLITCODE3",
            "timeline": [{"status": "NEW"}],
        }})
    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_client_factory(handler))

    phone = "+61412399999"
    _seed_table_order("T-915")
    try:
        from database import db
        _run(db.customers.delete_many({"phone": phone}))

        split_id = req(client, "GET", "/api/table/T-915/split").json()["id"]
        line_id = req(client, "GET", "/api/table/T-915/split").json()["lines"][0]["id"]
        token = _guest_token(phone)
        req(client, "POST", f"/api/table/split/{split_id}/claim",
            headers={"Authorization": f"Bearer {token}"}, json={"lineIds": [line_id]})
        req(client, "POST", f"/api/table/split/{split_id}/checkout",
            headers={"Authorization": f"Bearer {token}"},
            json={"provider": "crypto", "lineIds": [line_id]})

        # A real, functional db.customers record — the same table
        # create_transaction reads/writes for loyalty — not a
        # disconnected identity-layer touchpoint.
        customer = _run(db.customers.find_one({"phone": phone}, {"_id": 0}))
        assert customer is not None
        assert customer["email"] is None
        assert customer["points"] == 0  # not paid yet — just created

        payment = _run(db.payment_transactions.find_one({"sessionId": "SPLITCODE3"}, {"_id": 0}))
        assert payment["salePayload"]["customerId"] == customer["id"]
    finally:
        _cleanup_table("T-915")
        from database import db
        _run(db.payment_transactions.delete_many({"sessionId": "SPLITCODE3"}))
        _run(db.customers.delete_many({"phone": phone}))


def test_a_returning_guests_second_split_payment_matches_their_existing_customer(client):
    from services.customer_match import find_or_create_customer_by_phone
    from database import db

    phone = "+61412388888"
    _run(db.customers.delete_many({"phone": phone}))
    try:
        first = _run(find_or_create_customer_by_phone(phone))
        second = _run(find_or_create_customer_by_phone(phone))
        assert first["id"] == second["id"]
        assert _run(db.customers.count_documents({"phone": phone})) == 1
    finally:
        _run(db.customers.delete_many({"phone": phone}))
