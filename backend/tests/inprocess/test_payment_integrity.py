"""Payment-integrity paths added across the Stripe/online-order rounds had no
test coverage at all — every one of these was previously verified only by
reading the diff. Three real failure modes, each with a fix already in
production code, get pinned here:

1. An online order's stock must go back on the shelf when a paid,
   already-accepted order is cancelled — and NOT when a still-pending
   order (never deducted) is cancelled, which would over-restock.
2. refund_stripe_payment must not call Stripe's refund API a second time
   against a charge that's already fully refunded (Stripe itself would
   reject it, but the guard exists so a flaky retry doesn't even try).
3. The Stripe-session -> POS-transaction finalizer's claim must be
   reclaimable after a crash (stale claim) but left alone while another
   request is still actively working it (fresh claim) — otherwise either
   a crashed process strands a paid sale forever, or two concurrent
   pollers ring up the same sale twice.
"""
import asyncio
from datetime import datetime, timedelta

from conftest import req


def test_online_order_stock_deducts_on_accept_and_restores_on_cancel(client, owner_headers):
    loop = asyncio.get_event_loop()
    from database import db

    loop.run_until_complete(db.products.insert_one(
        {"id": "PAYINT-PROD-1", "name": "Test Burger", "category": "Mains",
         "stock": 10, "price": 15.0, "active": True}
    ))
    try:
        r = req(client, "POST", "/api/online/orders", json={
            "channel": "pickup", "customerName": "Stock Test",
            "items": [{"productId": "PAYINT-PROD-1", "name": "Test Burger", "price": 15.0, "quantity": 3,
                       "category": "Mains"}],
        })
        assert r.status_code == 200, r.text[:200]
        order_id = r.json()["id"]

        # Still pending — accepting hasn't happened yet, stock is untouched.
        prod = loop.run_until_complete(db.products.find_one({"id": "PAYINT-PROD-1"}, {"_id": 0}))
        assert prod["stock"] == 10

        r = req(client, "PATCH", f"/api/online/orders/{order_id}/status", headers=owner_headers,
                json={"status": "accepted"})
        assert r.status_code == 200, r.text[:200]
        prod = loop.run_until_complete(db.products.find_one({"id": "PAYINT-PROD-1"}, {"_id": 0}))
        assert prod["stock"] == 7, "accepting an online order should deduct stock like a POS sale"

        r = req(client, "PATCH", f"/api/online/orders/{order_id}/status", headers=owner_headers,
                json={"status": "cancelled"})
        assert r.status_code == 200, r.text[:200]
        prod = loop.run_until_complete(db.products.find_one({"id": "PAYINT-PROD-1"}, {"_id": 0}))
        assert prod["stock"] == 10, "cancelling an accepted order should restore the deducted stock"
    finally:
        loop.run_until_complete(db.products.delete_one({"id": "PAYINT-PROD-1"}))


def test_cancelling_a_never_accepted_order_does_not_over_restock(client, owner_headers):
    loop = asyncio.get_event_loop()
    from database import db

    loop.run_until_complete(db.products.insert_one(
        {"id": "PAYINT-PROD-2", "name": "Test Fries", "category": "Sides",
         "stock": 5, "price": 6.0, "active": True}
    ))
    try:
        r = req(client, "POST", "/api/online/orders", json={
            "channel": "pickup", "customerName": "Never Accepted",
            "items": [{"productId": "PAYINT-PROD-2", "name": "Test Fries", "price": 6.0, "quantity": 2,
                       "category": "Sides"}],
        })
        order_id = r.json()["id"]

        # Cancel directly from "pending" — stock was never deducted, so
        # cancelling must not add stock back (that would inflate on-hand
        # count above the true total).
        r = req(client, "PATCH", f"/api/online/orders/{order_id}/status", headers=owner_headers,
                json={"status": "cancelled"})
        assert r.status_code == 200, r.text[:200]
        prod = loop.run_until_complete(db.products.find_one({"id": "PAYINT-PROD-2"}, {"_id": 0}))
        assert prod["stock"] == 5
    finally:
        loop.run_until_complete(db.products.delete_one({"id": "PAYINT-PROD-2"}))


def test_refund_stripe_payment_skips_an_already_refunded_charge(monkeypatch):
    import stripe
    from routes.integrations import refund_stripe_payment

    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_fake")
    create_calls = []
    monkeypatch.setattr(stripe.checkout.Session, "retrieve", lambda session_id: {"payment_intent": "pi_already_refunded"})
    monkeypatch.setattr(stripe.PaymentIntent, "retrieve",
                         lambda pi: {"charges": {"data": [{"refunded": True}]}})
    monkeypatch.setattr(stripe.Refund, "create", lambda **kw: create_calls.append(kw))

    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(refund_stripe_payment("cs_test_already_refunded"))

    assert result is True
    assert create_calls == [], "must not call Stripe's refund API against an already-refunded charge"


def test_refund_stripe_payment_refunds_an_unrefunded_charge(monkeypatch):
    import stripe
    from routes.integrations import refund_stripe_payment

    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_fake")
    create_calls = []
    monkeypatch.setattr(stripe.checkout.Session, "retrieve", lambda session_id: {"payment_intent": "pi_needs_refund"})
    monkeypatch.setattr(stripe.PaymentIntent, "retrieve",
                         lambda pi: {"charges": {"data": [{"refunded": False}]}})
    monkeypatch.setattr(stripe.Refund, "create", lambda **kw: create_calls.append(kw))

    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(refund_stripe_payment("cs_test_needs_refund"))

    assert result is True
    assert create_calls == [{"payment_intent": "pi_needs_refund"}]


def test_finalize_pos_sale_recovers_a_stale_claim(monkeypatch):
    """A claim left in 'pending' for over 2 minutes means the process that
    claimed it died before finishing — the next poll/webhook must be able
    to pick it back up rather than leaving the sale stranded forever."""
    import routes.transactions
    from routes.integrations import _finalize_pos_sale_if_applicable
    from database import db

    finalize_calls = []

    class FakeTxn:
        id = "TXN-RECOVERED"

    async def fake_create_transaction(payload, user):
        finalize_calls.append((payload, user))
        return FakeTxn()

    monkeypatch.setattr(routes.transactions, "create_transaction", fake_create_transaction)

    loop = asyncio.get_event_loop()
    stale_claim_time = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
    loop.run_until_complete(db.payment_transactions.insert_one({
        "id": "SPAY-STALE", "sessionId": "cs_stale_claim", "kind": "pos_sale",
        "transactionId": "pending", "transactionClaimedAt": stale_claim_time,
        "salePayload": {"items": [], "paymentMethod": "card", "location": "front", "cashier": "Test Cashier"},
        "cashierUser": {"id": "U1", "name": "Test Cashier", "role": "cashier"},
    }))
    try:
        loop.run_until_complete(_finalize_pos_sale_if_applicable("cs_stale_claim"))
        assert len(finalize_calls) == 1, "a stale (crashed) claim should be reclaimed and finalized"
        doc = loop.run_until_complete(db.payment_transactions.find_one({"sessionId": "cs_stale_claim"}, {"_id": 0}))
        assert doc["transactionId"] == "TXN-RECOVERED"
    finally:
        loop.run_until_complete(db.payment_transactions.delete_one({"sessionId": "cs_stale_claim"}))


def test_finalize_pos_sale_leaves_a_fresh_claim_alone(monkeypatch):
    """A claim made moments ago is presumably still being worked by another
    in-flight request — a concurrent poll/webhook for the same session must
    not re-finalize it, or the same sale would be rung up twice."""
    import routes.transactions
    from routes.integrations import _finalize_pos_sale_if_applicable
    from database import db

    finalize_calls = []

    async def fake_create_transaction(payload, user):
        finalize_calls.append((payload, user))
        class FakeTxn: id = "TXN-SHOULD-NOT-HAPPEN"
        return FakeTxn()

    monkeypatch.setattr(routes.transactions, "create_transaction", fake_create_transaction)

    loop = asyncio.get_event_loop()
    fresh_claim_time = datetime.utcnow().isoformat()
    loop.run_until_complete(db.payment_transactions.insert_one({
        "id": "SPAY-FRESH", "sessionId": "cs_fresh_claim", "kind": "pos_sale",
        "transactionId": "pending", "transactionClaimedAt": fresh_claim_time,
        "salePayload": {"items": [], "paymentMethod": "card", "location": "front", "cashier": "Test Cashier"},
        "cashierUser": {"id": "U1", "name": "Test Cashier", "role": "cashier"},
    }))
    try:
        loop.run_until_complete(_finalize_pos_sale_if_applicable("cs_fresh_claim"))
        assert finalize_calls == [], "a fresh, still-in-flight claim must not be reclaimed"
        doc = loop.run_until_complete(db.payment_transactions.find_one({"sessionId": "cs_fresh_claim"}, {"_id": 0}))
        assert doc["transactionId"] == "pending"
    finally:
        loop.run_until_complete(db.payment_transactions.delete_one({"sessionId": "cs_fresh_claim"}))
