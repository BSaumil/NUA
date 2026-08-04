from fastapi import APIRouter, HTTPException, Request
from typing import Optional
from datetime import datetime
from database import db
import os
import uuid

router = APIRouter()

# ============ STRIPE CHECKOUT API ============
@router.post("/stripe/checkout")
async def create_stripe_checkout(data: dict, http_request: Request):
    """Create a Stripe checkout session for a POS transaction"""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    origin_url = data.get("originUrl", str(http_request.base_url).rstrip("/"))
    order_id = data.get("orderId", f"ORD-{str(uuid.uuid4())[:8].upper()}")
    amount = data.get("amount", 0)

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
    await db.payment_transactions.insert_one(payment_doc)
    payment_doc.pop("_id", None)

    return {"url": session.url, "sessionId": session.session_id}

@router.get("/stripe/checkout/status/{session_id}")
async def get_stripe_checkout_status(session_id: str, http_request: Request):
    """Poll Stripe checkout session status"""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout

    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

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

    return {
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
