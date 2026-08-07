from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timedelta
from database import db
from deps import get_user
import logging
import os
import uuid

router = APIRouter()


async def _mark_online_order_paid_if_applicable(session_id: str):
    """A payment_transactions doc tagged kind='online_order' (set by
    routes/online_orders.py's checkout endpoint) means this Stripe session
    is paying for an online order, not a POS sale — flip that order's
    paymentStatus too, not just the generic payment ledger, so staff and the
    guest's tracking page both see it as paid."""
    payment = await db.payment_transactions.find_one({"sessionId": session_id}, {"_id": 0})
    if not payment or payment.get("kind") != "online_order" or not payment.get("orderId"):
        return
    await db.online_orders.update_one(
        {"id": payment["orderId"]},
        {"$set": {"paymentStatus": "paid", "paidAt": datetime.utcnow().isoformat()}},
    )


async def refund_stripe_payment(session_id: str) -> bool:
    """Refund, in full, the Stripe payment behind a Checkout Session.

    Uses the official `stripe` SDK directly (already a pinned dependency in
    requirements.txt) rather than the emergentintegrations wrapper used
    elsewhere in this file — that wrapper only exposes checkout-session
    creation/status/webhook, no refund call. The SDK is synchronous, so the
    actual network calls run in a thread so they don't block the event loop.
    Returns False (never raises) on any failure — callers decide what a
    failed refund means for the action that triggered it.
    """
    import stripe
    import asyncio

    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        return False

    def _do_refund():
        stripe.api_key = api_key
        session = stripe.checkout.Session.retrieve(session_id)
        payment_intent = session.get("payment_intent")
        if not payment_intent:
            return False
        # Guards a double-refund attempt (e.g. staff double-clicking cancel
        # before the first request's response comes back) at the source of
        # truth — Stripe's own charge record — rather than trusting only our
        # own payment_transactions doc, which could itself be out of sync.
        intent = stripe.PaymentIntent.retrieve(payment_intent)
        charges = (intent.get("charges") or {}).get("data") or []
        if any(c.get("refunded") for c in charges):
            return True  # already refunded — the desired end state already holds
        stripe.Refund.create(payment_intent=payment_intent)
        return True

    try:
        return await asyncio.to_thread(_do_refund)
    except Exception as e:
        # Stripe itself rejects a second refund on an already-fully-refunded
        # charge with an InvalidRequestError — that's not a failure, it's
        # confirmation the money is already back with the guest.
        if "already been refunded" in str(e).lower() or "has already been refunded" in str(e).lower():
            return True
        logging.getLogger(__name__).error(f"Stripe refund failed for session {session_id}: {e}")
        return False


async def _finalize_pos_sale_if_applicable(session_id: str):
    """A payment_transactions doc tagged kind='pos_sale' carries the exact
    cart/discount/loyalty payload the POS had built at the moment the
    cashier sent the guest to Stripe — Stripe Checkout redirects the whole
    browser away and back, so nothing survives in POSTerminal's React state
    to finalize the sale once the guest returns. The Stripe redirect used to
    be the entire flow: pay, then land back on a page that only confirmed
    *money moved*, never actually rang anything up — no transaction, no
    stock deduction, no receipt, no loyalty earn.

    Runs the exact same POST /transactions code path a cash/card sale uses
    (imported and called directly, not re-implemented), so this gets
    everything that endpoint already does — server-side pricing, loyalty,
    gift cards — for free. Claims the payment doc atomically first so the
    status-poll and the webhook, which can both observe "paid" for the same
    session, can't both create the sale.

    The claim carries a timestamp and is reclaimable after 2 minutes — if
    the process crashes between claiming and finishing (not an exception,
    an actual process death), the except-block's un-claim never runs, and
    without a staleness window that would strand the sale at "pending"
    forever with no automatic retry. Stripe retries its webhook for days on
    failure, so a stale claim gets picked up by the next delivery attempt.
    """
    stale_cutoff = (datetime.utcnow() - timedelta(minutes=2)).isoformat()
    claimed = await db.payment_transactions.find_one_and_update(
        {"sessionId": session_id, "kind": "pos_sale", "$or": [
            {"transactionId": {"$exists": False}},
            {"transactionId": "pending", "transactionClaimedAt": {"$lt": stale_cutoff}},
        ]},
        {"$set": {"transactionId": "pending", "transactionClaimedAt": datetime.utcnow().isoformat()}},
    )
    if not claimed:
        return
    try:
        from models.transaction import TransactionCreate
        from routes.transactions import create_transaction
        txn = await create_transaction(TransactionCreate(**claimed["salePayload"]), user=claimed["cashierUser"])
        await db.payment_transactions.update_one(
            {"sessionId": session_id}, {"$set": {"transactionId": txn.id}}
        )
    except Exception as e:
        logging.getLogger(__name__).error(
            f"Stripe payment {session_id} confirmed paid but sale creation failed — needs manual reconciliation: {e}"
        )
        # Un-claim so a retried poll/webhook can try again immediately
        # rather than waiting out the staleness window above.
        await db.payment_transactions.update_one(
            {"sessionId": session_id}, {"$unset": {"transactionId": "", "transactionClaimedAt": ""}}
        )


# ============ STRIPE CHECKOUT API ============
@router.post("/stripe/checkout")
async def create_stripe_checkout(data: dict, http_request: Request, user: dict = Depends(get_user)):
    """Create a Stripe checkout session for a POS transaction.

    An optional "sale" object — the same shape POST /transactions takes
    (items, paymentMethod, customerId, location, cashier, orderType,
    tableNumber, discounts, points…) — gets stashed against this session so
    the sale can actually be rung up once Stripe confirms payment. Without
    it (or for any other caller of this generic endpoint) this behaves
    exactly as before: a payment session with nothing else attached.
    """
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    origin_url = data.get("originUrl", str(http_request.base_url).rstrip("/"))
    order_id = data.get("orderId", f"ORD-{str(uuid.uuid4())[:8].upper()}")
    amount = data.get("amount", 0)
    sale_payload = data.get("sale")

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    host_url = str(http_request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    success_url = f"{origin_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/pos"

    checkout_request = CheckoutSessionRequest(
        amount=float(amount),
        currency="aud",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"orderId": order_id, "source": "nua_pos"},
    )

    session = await stripe_checkout.create_checkout_session(checkout_request)

    # Save payment transaction
    payment_doc = {
        "id": f"SPAY-{str(uuid.uuid4())[:8].upper()}",
        "sessionId": session.session_id,
        "orderId": order_id,
        "amount": float(amount),
        "currency": "aud",
        "status": "initiated",
        "paymentStatus": "pending",
        "provider": "stripe",
        "createdAt": datetime.utcnow().isoformat(),
    }
    if sale_payload:
        payment_doc["kind"] = "pos_sale"
        payment_doc["salePayload"] = sale_payload
        payment_doc["cashierUser"] = user
    await db.payment_transactions.insert_one(payment_doc)
    payment_doc.pop("_id", None)

    return {"url": session.url, "sessionId": session.session_id}

@router.get("/stripe/checkout/status/{session_id}")
async def get_stripe_checkout_status(session_id: str, http_request: Request):
    """Poll Stripe checkout session status.

    Returns {"configured": False, ...} rather than a 500 when Stripe isn't
    configured — matches create_online_order_checkout's style, and means a
    caller polling with a stale/bookmarked session_id from before Stripe was
    ever set up (or after a key gets removed) gets a normal response to
    branch on instead of having to catch an exception.
    """
    from emergentintegrations.payments.stripe.checkout import StripeCheckout

    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        return {"configured": False, "status": None, "paymentStatus": None, "amountTotal": None, "currency": None}

    host_url = str(http_request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    try:
        status = await stripe_checkout.get_checkout_status(session_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Checkout session not found")

    # Update payment transaction
    existing = await db.payment_transactions.find_one({"sessionId": session_id})
    if existing:
        new_status = "completed" if status.payment_status == "paid" else (
            "expired" if status.status == "expired" else "pending"
        )
        # Only update if not already completed (prevent double processing)
        if existing.get("paymentStatus") != "paid":
            await db.payment_transactions.update_one(
                {"sessionId": session_id},
                {"$set": {"status": new_status, "paymentStatus": status.payment_status, "updatedAt": datetime.utcnow().isoformat()}}
            )
            if status.payment_status == "paid":
                await _mark_online_order_paid_if_applicable(session_id)
                await _finalize_pos_sale_if_applicable(session_id)

    return {
        "configured": True,
        "status": status.status,
        "paymentStatus": status.payment_status,
        "amountTotal": status.amount_total,
        "currency": status.currency,
    }

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout

    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    try:
        event = await stripe_checkout.handle_webhook(body, signature)
        if event.payment_status == "paid":
            await db.payment_transactions.update_one(
                {"sessionId": event.session_id},
                {"$set": {"status": "completed", "paymentStatus": "paid", "updatedAt": datetime.utcnow().isoformat()}}
            )
            await _mark_online_order_paid_if_applicable(event.session_id)
            await _finalize_pos_sale_if_applicable(event.session_id)
        return {"received": True}
    except Exception as e:
        return {"received": True, "note": str(e)}

# ============ INTEGRATIONS HUB API ============
@router.get("/integrations")
async def get_integrations():
    """Get all available integrations and their status"""
    saved = await db.integrations.find({}, {"_id": 0}).to_list(100)
    saved_map = {s["slug"]: s for s in saved}

    integrations = [
        # Delivery
        {"slug": "uber-eats", "name": "Uber Eats", "category": "Delivery", "description": "Receive and manage Uber Eats orders directly in your POS", "status": saved_map.get("uber-eats", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://merchants.ubereats.com"},
        {"slug": "doordash", "name": "DoorDash", "category": "Delivery", "description": "Sync DoorDash orders into your kitchen display", "status": saved_map.get("doordash", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://merchants.doordash.com"},
        {"slug": "menulog", "name": "Menulog", "category": "Delivery", "description": "Manage Menulog orders and menu sync", "status": saved_map.get("menulog", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://www.menulog.com.au/restaurants"},
        # Middleware
        {"slug": "doshii", "name": "Doshii", "category": "Middleware", "description": "Connect 20+ hospitality apps via one integration. Powers Uber Eats, DoorDash, Deputy, and more.", "status": saved_map.get("doshii", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Location Token", "website": "https://doshii.com"},
        # Payments
        {"slug": "stripe", "name": "Stripe", "category": "Payments", "description": "Accept card payments with Stripe Checkout", "status": "connected" if os.environ.get("STRIPE_API_KEY") else "disconnected", "requiresKey": False, "preconfigured": True},
        {"slug": "square", "name": "Square", "category": "Payments", "description": "Process payments via Square terminals", "status": saved_map.get("square", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Access Token", "website": "https://developer.squareup.com"},
        {"slug": "commbank", "name": "CommBank Smart", "category": "Payments", "description": "CommBank EFTPOS and pay-at-table via Doshii", "status": saved_map.get("commbank", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Merchant ID", "website": "https://www.commbank.com.au/business/payments/hospitality.html"},
        # Accounting
        {"slug": "xero", "name": "Xero", "category": "Accounting", "description": "Auto-sync daily sales, expenses, and GST to Xero", "status": saved_map.get("xero", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "OAuth Client ID", "website": "https://www.xero.com/au/"},
        {"slug": "myob", "name": "MYOB", "category": "Accounting", "description": "Push transactions and BAS data to MYOB", "status": saved_map.get("myob", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://www.myob.com/au"},
        {"slug": "quickbooks", "name": "QuickBooks", "category": "Accounting", "description": "Sync sales data with QuickBooks Online", "status": saved_map.get("quickbooks", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Client ID", "website": "https://quickbooks.intuit.com/au/"},
        # Rostering
        {"slug": "deputy", "name": "Deputy", "category": "Rostering", "description": "Auto-sync sales data for smart rostering and compliance", "status": saved_map.get("deputy", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Token", "website": "https://www.deputy.com"},
        {"slug": "tanda", "name": "Tanda", "category": "Rostering", "description": "Workforce management with live POS data", "status": saved_map.get("tanda", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Token", "website": "https://www.tanda.co"},
        # Reservations
        {"slug": "opentable", "name": "OpenTable", "category": "Reservations", "description": "Sync OpenTable bookings with your floor plan", "status": saved_map.get("opentable", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Restaurant ID", "website": "https://restaurant.opentable.com"},
        {"slug": "resdiary", "name": "ResDiary", "category": "Reservations", "description": "Manage ResDiary reservations in NUA", "status": saved_map.get("resdiary", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://www.resdiary.com"},
        # In-Venue
        {"slug": "mryum", "name": "Mr Yum", "category": "In-Venue Ordering", "description": "In-venue mobile ordering synced to kitchen", "status": saved_map.get("mryum", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Venue Token", "website": "https://www.mryum.com"},
        {"slug": "hungryhungry", "name": "HungryHungry", "category": "In-Venue Ordering", "description": "Order & pay at table integration", "status": saved_map.get("hungryhungry", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://www.hungryhungry.com"},
        # Loyalty
        {"slug": "marsello", "name": "Marsello", "category": "Loyalty & Marketing", "description": "Loyalty program and email marketing automation", "status": saved_map.get("marsello", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://www.marsello.com"},
        {"slug": "stampme", "name": "Stamp Me", "category": "Loyalty & Marketing", "description": "Digital stamp cards and rewards", "status": saved_map.get("stampme", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://stampme.com"},

        # ============ AUSTRALIAN BANKS ============
        {"slug": "cba", "name": "Commonwealth Bank (CBA)", "category": "Banks (AU)", "description": "Reconcile NUA sales with CBA business accounts via Open Banking (CDR).", "status": saved_map.get("cba", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "CDR Client Token", "website": "https://www.commbank.com.au/business.html"},
        {"slug": "westpac", "name": "Westpac", "category": "Banks (AU)", "description": "Westpac business banking reconciliation + EFTPOS settlements.", "status": saved_map.get("westpac", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "CDR Client Token", "website": "https://www.westpac.com.au/business-banking/"},
        {"slug": "anz", "name": "ANZ", "category": "Banks (AU)", "description": "ANZ Plus Business reconciliation + Worldline EFTPOS pairing.", "status": saved_map.get("anz", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "CDR Client Token", "website": "https://www.anz.com.au/business/"},
        {"slug": "nab", "name": "NAB", "category": "Banks (AU)", "description": "NAB Business Everyday + EasyTap on iPhone reconciliation.", "status": saved_map.get("nab", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "CDR Client Token", "website": "https://www.nab.com.au/business"},
        {"slug": "macquarie", "name": "Macquarie Bank", "category": "Banks (AU)", "description": "Macquarie Business Banking — daily settlement feed.", "status": saved_map.get("macquarie", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "CDR Client Token", "website": "https://www.macquarie.com.au/business-banking.html"},
        {"slug": "bendigo", "name": "Bendigo Bank", "category": "Banks (AU)", "description": "Bendigo Business account feed via CDR.", "status": saved_map.get("bendigo", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "CDR Client Token", "website": "https://www.bendigobank.com.au/business/"},
        {"slug": "bankwest", "name": "Bankwest", "category": "Banks (AU)", "description": "Bankwest business feed + EFTPOS reconciliation.", "status": saved_map.get("bankwest", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "CDR Client Token", "website": "https://www.bankwest.com.au/business"},
        {"slug": "suncorp", "name": "Suncorp Bank", "category": "Banks (AU)", "description": "Suncorp business banking reconciliation.", "status": saved_map.get("suncorp", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "CDR Client Token", "website": "https://www.suncorpbank.com.au/business"},
        {"slug": "hsbc-au", "name": "HSBC Australia", "category": "Banks (AU)", "description": "HSBC business banking + cross-border settlement.", "status": saved_map.get("hsbc-au", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "CDR Client Token", "website": "https://www.business.hsbc.com.au/"},
        {"slug": "ing-au", "name": "ING Direct", "category": "Banks (AU)", "description": "ING business everyday account feed.", "status": saved_map.get("ing-au", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "CDR Client Token", "website": "https://www.ing.com.au/business.html"},
        {"slug": "boq", "name": "Bank of Queensland", "category": "Banks (AU)", "description": "BOQ Business banking reconciliation.", "status": saved_map.get("boq", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "CDR Client Token", "website": "https://www.boq.com.au/business"},
        {"slug": "judo", "name": "Judo Bank", "category": "Banks (AU)", "description": "Judo SME term deposits + business loans visibility.", "status": saved_map.get("judo", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Token", "website": "https://www.judo.bank/"},

        # ============ PAYMENT TERMINALS / EFTPOS ============
        {"slug": "tyro", "name": "Tyro EFTPOS", "category": "Payment Terminals", "description": "Tyro integrated EFTPOS — auto-print receipt + tip prompt + surcharging.", "status": saved_map.get("tyro", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Merchant ID", "website": "https://www.tyro.com"},
        {"slug": "smartpay", "name": "Smartpay", "category": "Payment Terminals", "description": "Smartpay integrated EFTPOS terminals + cloud reporting.", "status": saved_map.get("smartpay", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Merchant ID", "website": "https://www.smartpay.com.au"},
        {"slug": "qiki", "name": "QIKI", "category": "Payment Terminals", "description": "QIKI BYO terminal + surcharging across all card schemes.", "status": saved_map.get("qiki", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Merchant ID", "website": "https://qiki.com.au"},
        {"slug": "westpac-eftpos", "name": "Westpac EFTPOS Air", "category": "Payment Terminals", "description": "Westpac Air all-in-one Android terminal.", "status": saved_map.get("westpac-eftpos", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Merchant ID", "website": "https://www.westpac.com.au/business-banking/merchant-services/"},
        {"slug": "anz-worldline", "name": "ANZ Worldline", "category": "Payment Terminals", "description": "ANZ Worldline integrated payments + reporting.", "status": saved_map.get("anz-worldline", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Merchant ID", "website": "https://www.anzworldline.com.au"},
        {"slug": "nab-easytap", "name": "NAB Easy Tap (Tap to Pay)", "category": "Payment Terminals", "description": "NAB tap-on-iPhone — no terminal needed.", "status": saved_map.get("nab-easytap", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Merchant ID", "website": "https://www.nab.com.au/business/payments-and-merchants/easy-tap"},
        {"slug": "square-terminal", "name": "Square Terminal", "category": "Payment Terminals", "description": "Square's all-in-one card reader + register.", "status": saved_map.get("square-terminal", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Access Token", "website": "https://squareup.com/au/en/hardware/terminal"},
        {"slug": "zeller", "name": "Zeller", "category": "Payment Terminals", "description": "Zeller smart terminal + business banking.", "status": saved_map.get("zeller", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://www.myzeller.com"},
        {"slug": "mx51", "name": "mx51 / Linkly", "category": "Payment Terminals", "description": "Multi-bank EFTPOS broker — connect any major AU terminal.", "status": saved_map.get("mx51", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Merchant ID", "website": "https://mx51.io"},
        {"slug": "verifone", "name": "Verifone", "category": "Payment Terminals", "description": "Verifone V200c / V400m terminals (global).", "status": saved_map.get("verifone", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Terminal ID", "website": "https://www.verifone.com"},
        {"slug": "ingenico", "name": "Ingenico", "category": "Payment Terminals", "description": "Ingenico Lane and Move series terminals.", "status": saved_map.get("ingenico", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Terminal ID", "website": "https://www.ingenico.com"},
        {"slug": "pax", "name": "PAX Technology", "category": "Payment Terminals", "description": "PAX A920 / A77 Android smart terminals.", "status": saved_map.get("pax", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Terminal ID", "website": "https://www.pax.com"},
        {"slug": "adyen", "name": "Adyen", "category": "Payment Terminals", "description": "Adyen omnichannel terminals — global enterprise.", "status": saved_map.get("adyen", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://www.adyen.com"},
        {"slug": "razorpay", "name": "Razorpay", "category": "Payment Terminals", "description": "Razorpay POS terminals + payment links (IN / SE Asia).", "status": saved_map.get("razorpay", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://razorpay.com"},
        {"slug": "paypal-zettle", "name": "PayPal Zettle", "category": "Payment Terminals", "description": "PayPal Zettle card readers + business accounts.", "status": saved_map.get("paypal-zettle", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://www.zettle.com"},
    ]

    return integrations

@router.post("/integrations/{slug}/connect")
async def connect_integration(slug: str, data: dict):
    """Connect/configure an integration"""
    api_key = data.get("apiKey", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="API key required")

    doc = {
        "slug": slug,
        "apiKey": api_key,
        "status": "connected",
        "connectedAt": datetime.utcnow().isoformat(),
        "lastSync": None,
    }
    await db.integrations.update_one({"slug": slug}, {"$set": doc}, upsert=True)
    return {"status": "connected", "message": f"{slug} connected successfully"}

@router.post("/integrations/{slug}/disconnect")
async def disconnect_integration(slug: str):
    """Disconnect an integration"""
    await db.integrations.update_one(
        {"slug": slug},
        {"$set": {"status": "disconnected", "disconnectedAt": datetime.utcnow().isoformat()}}
    )
    return {"status": "disconnected"}

@router.post("/integrations/{slug}/sync")
async def sync_integration(slug: str):
    """Trigger a manual sync for an integration"""
    integration = await db.integrations.find_one({"slug": slug}, {"_id": 0})
    if not integration or integration.get("status") != "connected":
        raise HTTPException(status_code=400, detail="Integration not connected")

    await db.integrations.update_one(
        {"slug": slug},
        {"$set": {"lastSync": datetime.utcnow().isoformat()}}
    )
    return {"message": f"Sync triggered for {slug}", "lastSync": datetime.utcnow().isoformat()}
