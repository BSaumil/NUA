"""Crypto checkout (Bitcoin + USDC via Coinbase Commerce).

This sandbox has no outbound network path to any third-party host, so
"verified against Coinbase Commerce" here means: every httpx call the
client makes is routed through an httpx.MockTransport returning real,
documented Coinbase Commerce response shapes
(https://commerce.coinbase.com/docs/api/), and we assert the client
parses/normalizes it correctly and that the checkout route actually rings
up the sale once a charge is confirmed — same finalize path Stripe
checkout already uses (routes/integrations.py's
_finalize_pos_sale_if_applicable), reused rather than re-implemented.
"""
import hashlib
import hmac
import json

import httpx
import pytest

from conftest import req


_RealAsyncClient = httpx.AsyncClient


def _mock_client_factory(handler):
    def factory(*args, **kwargs):
        return _RealAsyncClient(transport=httpx.MockTransport(handler), timeout=kwargs.get("timeout", 10))
    return factory


# --------------------------------------------------------------- unconfigured

def test_checkout_refuses_when_not_configured(client, owner_headers, monkeypatch):
    import services.coinbase_commerce as cc
    monkeypatch.delenv("COINBASE_COMMERCE_API_KEY", raising=False)
    r = req(client, "POST", "/api/crypto/checkout", headers=owner_headers,
            json={"amount": 25.0, "originUrl": "https://pos.example.com"})
    assert r.status_code == 500
    assert "aren't set up" in r.json()["detail"].lower()


def test_status_reports_unconfigured_cleanly(client, owner_headers, monkeypatch):
    monkeypatch.delenv("COINBASE_COMMERCE_API_KEY", raising=False)
    r = req(client, "GET", "/api/crypto/checkout/status/some-code", headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["configured"] is False


def test_checkout_requires_auth(anon):
    assert req(anon, "POST", "/api/crypto/checkout", json={"amount": 10}).status_code == 401


# ------------------------------------------------------------------ checkout

def test_create_checkout_creates_a_charge_and_payment_record(client, owner_headers, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/charges"
        assert request.headers["X-CC-Api-Key"] == "cc-test-key"
        body = json.loads(request.content)
        assert body["local_price"] == {"amount": "42.50", "currency": "AUD"}
        return httpx.Response(200, json={"data": {
            "id": "charge-uuid-1", "code": "ABCD1234",
            "hosted_url": "https://commerce.coinbase.com/charges/ABCD1234",
            "timeline": [{"status": "NEW"}],
        }})

    import services.coinbase_commerce as cc
    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_client_factory(handler))

    r = req(client, "POST", "/api/crypto/checkout", headers=owner_headers, json={
        "amount": 42.50, "orderId": "ORD-TEST1", "originUrl": "https://pos.example.com",
        "sale": {"items": [], "paymentMethod": "crypto", "location": "Main", "cashier": "Test Owner"},
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"] == "https://commerce.coinbase.com/charges/ABCD1234"
    assert body["sessionId"] == "ABCD1234"

    from database import db
    import asyncio
    doc = asyncio.get_event_loop().run_until_complete(
        db.payment_transactions.find_one({"sessionId": "ABCD1234"}, {"_id": 0}))
    assert doc["provider"] == "crypto_coinbase"
    assert doc["kind"] == "pos_sale"
    assert doc["paymentStatus"] == "pending"


def test_create_checkout_rejects_a_non_positive_amount(client, owner_headers, monkeypatch):
    import services.coinbase_commerce as cc
    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")
    r = req(client, "POST", "/api/crypto/checkout", headers=owner_headers, json={"amount": 0})
    assert r.status_code == 400


def test_create_checkout_surfaces_a_processor_error_as_502(client, owner_headers, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad request")

    import services.coinbase_commerce as cc
    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_client_factory(handler))
    r = req(client, "POST", "/api/crypto/checkout", headers=owner_headers, json={"amount": 10})
    assert r.status_code == 502


# ------------------------------------------------------------- status + sale

def test_status_poll_finalizes_the_sale_once_the_charge_confirms(client, owner_headers, monkeypatch):
    import routes.transactions
    import services.coinbase_commerce as cc
    from database import db
    import asyncio

    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")

    finalize_calls = []

    class FakeTxn:
        id = "TXN-CRYPTO-1"

    async def fake_create_transaction(payload, user):
        finalize_calls.append((payload, user))
        return FakeTxn()

    monkeypatch.setattr(routes.transactions, "create_transaction", fake_create_transaction)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {
            "id": "charge-uuid-2", "code": "PAID9999",
            "timeline": [{"status": "NEW"}, {"status": "PENDING"}, {"status": "COMPLETED"}],
        }})
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_client_factory(handler))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.payment_transactions.insert_one({
        "id": "CPAY-1", "sessionId": "PAID9999", "kind": "pos_sale",
        "paymentStatus": "pending", "provider": "crypto_coinbase",
        "salePayload": {"items": [], "paymentMethod": "crypto", "location": "Main", "cashier": "Test Owner"},
        "cashierUser": {"id": "U1", "name": "Test Owner", "role": "owner"},
    }))
    try:
        r = req(client, "GET", "/api/crypto/checkout/status/PAID9999", headers=owner_headers)
        assert r.status_code == 200, r.text
        assert r.json() == {"configured": True, "status": "paid", "paymentStatus": "paid"}
        assert len(finalize_calls) == 1

        doc = loop.run_until_complete(db.payment_transactions.find_one({"sessionId": "PAID9999"}, {"_id": 0}))
        assert doc["paymentStatus"] == "paid"
        assert doc["transactionId"] == "TXN-CRYPTO-1"
    finally:
        loop.run_until_complete(db.payment_transactions.delete_one({"sessionId": "PAID9999"}))


def test_status_poll_does_not_refinalize_an_already_paid_charge(client, owner_headers, monkeypatch):
    import routes.transactions
    import services.coinbase_commerce as cc
    from database import db
    import asyncio

    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")
    finalize_calls = []

    async def fake_create_transaction(payload, user):
        finalize_calls.append(1)
        class T: id = "SHOULD-NOT-HAPPEN"
        return T()
    monkeypatch.setattr(routes.transactions, "create_transaction", fake_create_transaction)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"code": "ALREADY9999", "timeline": [{"status": "COMPLETED"}]}})
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_client_factory(handler))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.payment_transactions.insert_one({
        "id": "CPAY-2", "sessionId": "ALREADY9999", "kind": "pos_sale", "paymentStatus": "paid",
        "transactionId": "TXN-ALREADY", "provider": "crypto_coinbase",
        "salePayload": {"items": [], "paymentMethod": "crypto", "location": "Main", "cashier": "Test Owner"},
        "cashierUser": {"id": "U1", "name": "Test Owner", "role": "owner"},
    }))
    try:
        r = req(client, "GET", "/api/crypto/checkout/status/ALREADY9999", headers=owner_headers)
        assert r.status_code == 200
        assert len(finalize_calls) == 0, "a charge already marked paid must never be re-finalized"
    finally:
        loop.run_until_complete(db.payment_transactions.delete_one({"sessionId": "ALREADY9999"}))


def test_status_reports_expired(client, owner_headers, monkeypatch):
    import services.coinbase_commerce as cc
    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"code": "EXP1", "timeline": [{"status": "NEW"}, {"status": "EXPIRED"}]}})
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_client_factory(handler))

    r = req(client, "GET", "/api/crypto/checkout/status/EXP1", headers=owner_headers)
    assert r.json() == {"configured": True, "status": "expired", "paymentStatus": "unpaid"}


# ---------------------------------------------------------- status by order

def test_status_by_order_resolves_to_the_charge_code(client, owner_headers, monkeypatch):
    """Coinbase's redirect back doesn't echo the charge code, only whatever
    the merchant put in redirect_url — which is order_id (see
    create_crypto_checkout). This is the lookup that makes that work."""
    import services.coinbase_commerce as cc
    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")

    def create_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {
            "code": "ORDERLOOKUP1", "hosted_url": "https://commerce.coinbase.com/charges/ORDERLOOKUP1",
            "timeline": [{"status": "NEW"}],
        }})
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_client_factory(create_handler))

    create = req(client, "POST", "/api/crypto/checkout", headers=owner_headers,
                 json={"amount": 15.0, "orderId": "ORD-LOOKUP-1", "originUrl": "https://pos.example.com"})
    assert create.status_code == 200, create.text
    assert create.json()["sessionId"] == "ORDERLOOKUP1"

    def status_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"code": "ORDERLOOKUP1", "timeline": [{"status": "COMPLETED"}]}})
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_client_factory(status_handler))

    r = req(client, "GET", "/api/crypto/checkout/status-by-order/ORD-LOOKUP-1", headers=owner_headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"configured": True, "status": "paid", "paymentStatus": "paid"}


def test_status_by_order_404s_for_an_unknown_order(client, owner_headers, monkeypatch):
    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")
    r = req(client, "GET", "/api/crypto/checkout/status-by-order/NO-SUCH-ORDER", headers=owner_headers)
    assert r.status_code == 404


# --------------------------------------------------------------------- webhook

def test_webhook_rejects_a_bad_signature(client):
    r = req(client, "POST", "/api/webhook/coinbase",
            json={"event": {"type": "charge:confirmed", "data": {"code": "X"}}},
            headers={"X-CC-Webhook-Signature": "not-the-real-signature"})
    assert r.status_code == 401


def test_webhook_confirms_a_sale_with_a_valid_signature(client, owner_headers, monkeypatch):
    import routes.transactions
    from database import db
    import asyncio

    monkeypatch.setenv("COINBASE_COMMERCE_WEBHOOK_SECRET", "whsec-test")

    finalize_calls = []

    async def fake_create_transaction(payload, user):
        finalize_calls.append(1)
        class T: id = "TXN-WEBHOOK-1"
        return T()
    monkeypatch.setattr(routes.transactions, "create_transaction", fake_create_transaction)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.payment_transactions.insert_one({
        "id": "CPAY-3", "sessionId": "WEBHOOK9999", "kind": "pos_sale", "paymentStatus": "pending",
        "provider": "crypto_coinbase",
        "salePayload": {"items": [], "paymentMethod": "crypto", "location": "Main", "cashier": "Test Owner"},
        "cashierUser": {"id": "U1", "name": "Test Owner", "role": "owner"},
    }))
    try:
        payload = json.dumps({"event": {"type": "charge:confirmed", "data": {"code": "WEBHOOK9999"}}}).encode()
        signature = hmac.new(b"whsec-test", payload, hashlib.sha256).hexdigest()

        r = client.post("/api/webhook/coinbase", content=payload,
                         headers={"X-CC-Webhook-Signature": signature, "Content-Type": "application/json"})
        assert r.status_code == 200, r.text
        assert len(finalize_calls) == 1

        doc = loop.run_until_complete(db.payment_transactions.find_one({"sessionId": "WEBHOOK9999"}, {"_id": 0}))
        assert doc["paymentStatus"] == "paid"
        assert doc["transactionId"] == "TXN-WEBHOOK-1"
    finally:
        loop.run_until_complete(db.payment_transactions.delete_one({"sessionId": "WEBHOOK9999"}))


# ------------------------------------------------------------- unit: status collapse

def test_charge_status_collapses_timeline_correctly():
    from services.coinbase_commerce import charge_status
    assert charge_status({"timeline": [{"status": "NEW"}]}) == "pending"
    assert charge_status({"timeline": [{"status": "NEW"}, {"status": "COMPLETED"}]}) == "paid"
    assert charge_status({"timeline": [{"status": "NEW"}, {"status": "RESOLVED"}]}) == "paid"
    assert charge_status({"timeline": [{"status": "NEW"}, {"status": "EXPIRED"}]}) == "expired"
    assert charge_status({"timeline": [{"status": "NEW"}, {"status": "CANCELED"}]}) == "expired"
    assert charge_status({"timeline": []}) == "pending"


def test_verify_webhook_signature():
    from services.coinbase_commerce import verify_webhook_signature
    import os
    os.environ["COINBASE_COMMERCE_WEBHOOK_SECRET"] = "my-secret"
    body = b'{"event": {"type": "charge:confirmed"}}'
    good_sig = hmac.new(b"my-secret", body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, good_sig) is True
    assert verify_webhook_signature(body, "wrong") is False
    assert verify_webhook_signature(body, "") is False


# --------------------------------------------------- Integrations registry

def test_crypto_provider_is_honestly_not_implemented_when_unconfigured(client, owner_headers, monkeypatch):
    monkeypatch.delenv("COINBASE_COMMERCE_API_KEY", raising=False)
    r = req(client, "GET", "/api/integrations", headers=owner_headers)
    assert r.status_code == 200
    providers = {p["slug"]: p for p in r.json()}
    assert providers["crypto-coinbase"]["status"] == "not_implemented"
    # Adding a second preconfigured provider must not make Stripe (or vice
    # versa) borrow the wrong provider's env-var check.
    assert providers["stripe"]["status"] == "not_implemented"


def test_crypto_provider_reports_preconfigured_once_the_key_is_set(client, owner_headers, monkeypatch):
    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")
    monkeypatch.delenv("STRIPE_API_KEY", raising=False)
    r = req(client, "GET", "/api/integrations", headers=owner_headers)
    providers = {p["slug"]: p for p in r.json()}
    assert providers["crypto-coinbase"]["status"] == "preconfigured"
    assert providers["stripe"]["status"] == "not_implemented", \
        "crypto's env var being set must not make Stripe appear configured too"
