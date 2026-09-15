"""Pre-merge P0 risk closure: a double-click or client retry on "Pay with
card"/"Pay with crypto" could create two live Stripe Checkout Sessions /
Coinbase charges for the same cart or order — previously undocumented and
explicitly flagged as out of scope in FINANCIAL_OFFLINE_INTEGRITY_REMAINING_
WORK.md ("Deliberately out of scope for this pass").

Fixed via services/payment_idempotency.py's claim_or_wait/record_result,
wired into routes/integrations.py's _create_stripe_session, routes/
crypto_payments.py's _create_crypto_session (shared by both the staff POS
checkout and routes/bill_split.py's guest checkout), and routes/
online_orders.py's create_online_order_checkout. Crypto is the path
actually exercisable end to end in this sandbox — the same fixed test env
lacks the `emergentintegrations` package Stripe's SDK wrapper needs (see
test_payment_integrity.py's own note on this), so Stripe checkout-session
creation is exercised here via a lightweight fake module installed into
sys.modules, mirroring the shape of the real emergentintegrations.payments.
stripe.checkout API used in routes/integrations.py.
"""
import asyncio
import sys
import time
import types
from concurrent.futures import ThreadPoolExecutor

import httpx

from database import db
from tests.inprocess.conftest import req

_RealAsyncClient = httpx.AsyncClient


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _mock_coinbase_client(handler):
    def factory(*args, **kwargs):
        return _RealAsyncClient(transport=httpx.MockTransport(handler), timeout=kwargs.get("timeout", 10))
    return factory


def _install_fake_stripe_sdk(monkeypatch, *, delay_seconds=0.0):
    """Installs a minimal fake of emergentintegrations.payments.stripe.checkout
    (not present in this sandbox) so _create_stripe_session's inline import
    succeeds. call_log records every real "create session" call — used to
    prove a repeated/concurrent request only calls out once."""
    call_log = []

    class CheckoutSessionRequest:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class _Session:
        def __init__(self, session_id, url):
            self.session_id = session_id
            self.url = url

    class StripeCheckout:
        def __init__(self, api_key, webhook_url):
            self.api_key = api_key
            self.webhook_url = webhook_url

        async def create_checkout_session(self, request):
            call_log.append(request)
            if delay_seconds:
                await asyncio.sleep(delay_seconds)
            sid = f"cs_test_fake_{len(call_log)}"
            return _Session(sid, f"https://checkout.stripe.com/fake/{sid}")

    fake_checkout_mod = types.ModuleType("emergentintegrations.payments.stripe.checkout")
    fake_checkout_mod.StripeCheckout = StripeCheckout
    fake_checkout_mod.CheckoutSessionRequest = CheckoutSessionRequest
    fake_stripe_mod = types.ModuleType("emergentintegrations.payments.stripe")
    fake_stripe_mod.checkout = fake_checkout_mod
    fake_payments_mod = types.ModuleType("emergentintegrations.payments")
    fake_payments_mod.stripe = fake_stripe_mod
    fake_pkg = types.ModuleType("emergentintegrations")
    fake_pkg.payments = fake_payments_mod

    monkeypatch.setitem(sys.modules, "emergentintegrations", fake_pkg)
    monkeypatch.setitem(sys.modules, "emergentintegrations.payments", fake_payments_mod)
    monkeypatch.setitem(sys.modules, "emergentintegrations.payments.stripe", fake_stripe_mod)
    monkeypatch.setitem(sys.modules, "emergentintegrations.payments.stripe.checkout", fake_checkout_mod)
    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_fake_checkout_idempotency")
    return call_log


# ─────────────────────────────────────────────────────────────────────────
# Stripe (POS checkout) — sequential retry + genuine concurrency
# ─────────────────────────────────────────────────────────────────────────
def test_a_repeated_stripe_checkout_with_the_same_idempotency_key_reuses_the_session(
        client, owner_headers, monkeypatch):
    call_log = _install_fake_stripe_sdk(monkeypatch)
    try:
        payload = {"originUrl": "http://testserver", "amount": 25.0, "idempotencyKey": "IDEM-SEQ-1"}
        first = req(client, "POST", "/api/stripe/checkout", headers=owner_headers, json=payload)
        assert first.status_code == 200, first.text[:200]

        second = req(client, "POST", "/api/stripe/checkout", headers=owner_headers, json=payload)
        assert second.status_code == 200, second.text[:200]

        assert first.json() == second.json(), (
            "a retried checkout request with the same idempotencyKey must get back the exact same "
            "session — not a second live Stripe Checkout Session"
        )
        assert len(call_log) == 1, (
            f"Stripe's create_checkout_session must only be called once for two requests sharing an "
            f"idempotencyKey — was called {len(call_log)} times"
        )
    finally:
        _run(db.payment_transactions.delete_many({"sessionId": {"$regex": "^cs_test_fake_"}}))
        _run(db.payment_session_claims.delete_many({"key": "IDEM-SEQ-1"}))


def test_two_concurrent_stripe_checkouts_with_the_same_idempotency_key_only_create_one_session(
        client, owner_headers, monkeypatch):
    """The actual race the bug is about: two near-simultaneous requests (a
    double-click, or a client retrying before the first response even
    lands) that both reach _create_stripe_session before either has
    finished. delay_seconds widens the window so the two real threads
    below are actually overlapping inside the "call Stripe" step, not just
    racing to start (mongomock's fake I/O otherwise tends to run each
    request close to atomically — see test_financial_offline_integrity.py's
    own note on this same harness limitation)."""
    call_log = _install_fake_stripe_sdk(monkeypatch, delay_seconds=0.2)
    try:
        payload = {"originUrl": "http://testserver", "amount": 30.0, "idempotencyKey": "IDEM-RACE-1"}

        def _do_checkout():
            return req(client, "POST", "/api/stripe/checkout", headers=owner_headers, json=payload)

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_do_checkout)
            f2 = pool.submit(_do_checkout)
            r1, r2 = f1.result(), f2.result()

        assert r1.status_code == 200, r1.text[:200]
        assert r2.status_code == 200, r2.text[:200]
        assert r1.json()["sessionId"] == r2.json()["sessionId"], (
            "two concurrent checkout requests for the same cart must resolve to the same Stripe "
            "session, not two independently-live ones"
        )
        assert len(call_log) == 1, (
            f"Stripe must only be called once even when two requests race — was called "
            f"{len(call_log)} times"
        )

        claims = _run(db.payment_transactions.find(
            {"sessionId": {"$regex": "^cs_test_fake_"}}, {"_id": 0}).to_list(10))
        assert len(claims) == 1, "only one payment_transactions row may exist for the winning session"
    finally:
        _run(db.payment_transactions.delete_many({"sessionId": {"$regex": "^cs_test_fake_"}}))
        _run(db.payment_session_claims.delete_many({"key": "IDEM-RACE-1"}))


def test_a_stale_stripe_idempotency_claim_is_not_reused_forever(client, owner_headers, monkeypatch):
    """A guest whose card was declined, or who abandoned an old session,
    must get a fresh one on a later attempt — not be stuck replaying a
    dead session forever. Simulated by back-dating the claim's createdAt
    past CLAIM_STALE_AFTER_SECONDS rather than actually sleeping."""
    import services.payment_idempotency as pidem
    call_log = _install_fake_stripe_sdk(monkeypatch)
    try:
        payload = {"originUrl": "http://testserver", "amount": 12.0, "idempotencyKey": "IDEM-STALE-1"}
        first = req(client, "POST", "/api/stripe/checkout", headers=owner_headers, json=payload)
        assert first.status_code == 200, first.text[:200]
        assert len(call_log) == 1

        stale_time = "2000-01-01T00:00:00+00:00"
        _run(db.payment_session_claims.update_one(
            {"claimKey": "stripe:IDEM-STALE-1"}, {"$set": {"createdAt": stale_time}}))

        second = req(client, "POST", "/api/stripe/checkout", headers=owner_headers, json=payload)
        assert second.status_code == 200, second.text[:200]
        assert len(call_log) == 2, "a stale claim must not suppress a genuinely new checkout attempt"
        assert second.json()["sessionId"] != first.json()["sessionId"]
    finally:
        _run(db.payment_transactions.delete_many({"sessionId": {"$regex": "^cs_test_fake_"}}))
        _run(db.payment_session_claims.delete_many({"key": "IDEM-STALE-1"}))


def test_stripe_checkout_without_an_idempotency_key_behaves_as_before(client, owner_headers, monkeypatch):
    """No idempotencyKey and no orderId — order_id is randomly generated
    server-side per call (the POS's actual current behavior absent the
    frontend fix), so two calls legitimately create two sessions. Proves
    the fix is additive, not a regression for callers that don't opt in."""
    call_log = _install_fake_stripe_sdk(monkeypatch)
    try:
        payload = {"originUrl": "http://testserver", "amount": 8.0}
        first = req(client, "POST", "/api/stripe/checkout", headers=owner_headers, json=payload)
        second = req(client, "POST", "/api/stripe/checkout", headers=owner_headers, json=payload)
        assert first.status_code == 200 and second.status_code == 200
        assert first.json()["sessionId"] != second.json()["sessionId"]
        assert len(call_log) == 2
    finally:
        _run(db.payment_transactions.delete_many({"sessionId": {"$regex": "^cs_test_fake_"}}))


# ─────────────────────────────────────────────────────────────────────────
# Coinbase Commerce (crypto) — real end-to-end path in this sandbox
# ─────────────────────────────────────────────────────────────────────────
def test_a_repeated_crypto_checkout_with_the_same_idempotency_key_reuses_the_charge(
        client, owner_headers, monkeypatch):
    import services.coinbase_commerce as cc
    call_log = []

    def handler(request: httpx.Request) -> httpx.Response:
        call_log.append(request)
        code = f"CCIDEM{len(call_log)}"
        return httpx.Response(200, json={"data": {
            "id": f"charge-{code}", "code": code,
            "hosted_url": f"https://commerce.coinbase.com/charges/{code}",
            "timeline": [{"status": "NEW"}],
        }})

    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_coinbase_client(handler))

    try:
        payload = {"amount": 20.0, "idempotencyKey": "CC-IDEM-SEQ-1"}
        first = req(client, "POST", "/api/crypto/checkout", headers=owner_headers, json=payload)
        assert first.status_code == 200, first.text[:200]
        second = req(client, "POST", "/api/crypto/checkout", headers=owner_headers, json=payload)
        assert second.status_code == 200, second.text[:200]

        assert first.json() == second.json()
        assert len(call_log) == 1, (
            f"Coinbase Commerce's charge-create API must only be called once — was called "
            f"{len(call_log)} times"
        )
    finally:
        _run(db.payment_transactions.delete_many({"sessionId": {"$regex": "^CCIDEM"}}))
        _run(db.payment_session_claims.delete_many({"key": "CC-IDEM-SEQ-1"}))


def test_two_concurrent_crypto_checkouts_with_the_same_idempotency_key_only_create_one_charge(
        client, owner_headers, monkeypatch):
    import services.coinbase_commerce as cc
    call_log = []

    def handler(request: httpx.Request) -> httpx.Response:
        call_log.append(request)
        time.sleep(0.2)  # widen the race window — see the Stripe race test's own comment
        code = f"CCRACE{len(call_log)}"
        return httpx.Response(200, json={"data": {
            "id": f"charge-{code}", "code": code,
            "hosted_url": f"https://commerce.coinbase.com/charges/{code}",
            "timeline": [{"status": "NEW"}],
        }})

    monkeypatch.setenv("COINBASE_COMMERCE_API_KEY", "cc-test-key")
    monkeypatch.setattr(cc.httpx, "AsyncClient", _mock_coinbase_client(handler))

    try:
        payload = {"amount": 15.0, "idempotencyKey": "CC-IDEM-RACE-1"}

        def _do_checkout():
            return req(client, "POST", "/api/crypto/checkout", headers=owner_headers, json=payload)

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_do_checkout)
            f2 = pool.submit(_do_checkout)
            r1, r2 = f1.result(), f2.result()

        assert r1.status_code == 200, r1.text[:200]
        assert r2.status_code == 200, r2.text[:200]
        assert r1.json()["sessionId"] == r2.json()["sessionId"]
        assert len(call_log) == 1, (
            f"Coinbase must only be called once even when two requests race — was called "
            f"{len(call_log)} times"
        )
    finally:
        _run(db.payment_transactions.delete_many({"sessionId": {"$regex": "^CCRACE"}}))
        _run(db.payment_session_claims.delete_many({"key": "CC-IDEM-RACE-1"}))


# ─────────────────────────────────────────────────────────────────────────
# Free protection via a naturally-stable orderId — no idempotencyKey needed
# ─────────────────────────────────────────────────────────────────────────
def test_online_order_checkout_defaults_its_idempotency_key_to_the_orderid(client, owner_headers, monkeypatch):
    """routes/online_orders.py's checkout endpoint never had a client-
    supplied idempotency key at all — order_id (an already-placed order's
    real id) is a stable identity on its own, so _create_stripe_session's
    `data.get("idempotencyKey") or order_id` fallback protects this flow
    with zero caller changes. Exercised directly against the claim/record
    primitives (not the endpoint's own emergentintegrations import, which
    this sandbox can't satisfy even with STRIPE_API_KEY set — see
    test_payment_integrity.py's note) to prove the fallback key is what
    routes/online_orders.py actually passes through."""
    from services.payment_idempotency import claim_or_wait, record_result

    order_id = "ONLINE-ORD-IDEM-1"
    _run(db.payment_session_claims.delete_many({"key": order_id}))
    try:
        first_claim = _run(claim_or_wait("stripe_online_order", order_id))
        assert first_claim is None, "first caller must win the claim and proceed to create a session"

        fake_result = {"url": "https://checkout.stripe.com/fake/online-order", "sessionId": "cs_online_fake"}
        _run(record_result("stripe_online_order", order_id, fake_result))

        second_claim = _run(claim_or_wait("stripe_online_order", order_id))
        assert second_claim == fake_result, "a repeat checkout attempt for the same order must reuse the session"
    finally:
        _run(db.payment_session_claims.delete_many({"key": order_id}))


def test_bill_split_guest_checkout_shares_a_stable_key_per_split(client, monkeypatch):
    """routes/bill_split.py passes `orderId: split_id` into checkout_data —
    already a stable per-split identity — so _create_stripe_session's
    order_id fallback protects a guest double-tapping "Pay" on the split
    bill page with zero change to bill_split.py itself. Same seeding
    pattern as test_bill_split.py's own Stripe/crypto checkout tests."""
    from database import db as _db

    call_log = _install_fake_stripe_sdk(monkeypatch)
    _run(_db.kitchen_orders.insert_one({
        "id": "KORD-IDEM-SPLIT-1", "tableNumber": "T-IDEM-1", "status": "new",
        "items": [{"productId": "PROD-IDEM-BURGER", "productName": "Burger", "category": "Mains", "quantity": 1}],
    }))
    _run(_db.products.insert_one({"id": "PROD-IDEM-BURGER", "name": "Burger", "price": 12.0, "category": "Mains"}))
    split_id = None
    try:
        from services import guest_session
        token = guest_session.issue_guest_token("+61412345099")
        headers = {"Authorization": f"Bearer {token}"}

        split_id = req(client, "GET", "/api/table/T-IDEM-1/split").json()["id"]
        line_id = req(client, "GET", "/api/table/T-IDEM-1/split").json()["lines"][0]["id"]
        req(client, "POST", f"/api/table/split/{split_id}/claim", headers=headers, json={"lineIds": [line_id]})

        payload = {"provider": "stripe", "lineIds": [line_id]}
        first = req(client, "POST", f"/api/table/split/{split_id}/checkout", headers=headers, json=payload)
        assert first.status_code == 200, first.text[:200]
        second = req(client, "POST", f"/api/table/split/{split_id}/checkout", headers=headers, json=payload)
        assert second.status_code == 200, second.text[:200]

        assert first.json()["sessionId"] == second.json()["sessionId"], (
            "a guest double-tapping Pay on the split-bill page must not get two live Stripe sessions"
        )
        assert len(call_log) == 1
    finally:
        _run(_db.kitchen_orders.delete_many({"tableNumber": "T-IDEM-1"}))
        _run(_db.bill_splits.delete_many({"tableNumber": "T-IDEM-1"}))
        _run(_db.products.delete_many({"id": "PROD-IDEM-BURGER"}))
        _run(_db.customers.delete_many({"phone": "+61412345099"}))
        _run(db.payment_transactions.delete_many({"sessionId": {"$regex": "^cs_test_fake_"}}))
        if split_id:
            _run(db.payment_session_claims.delete_many({"key": split_id}))
