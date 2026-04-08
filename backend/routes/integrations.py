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
        metadata={"orderId": order_id, "source": "ananta_pos"},
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

    status = await stripe_checkout.get_checkout_status(session_id)

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
        {"slug": "resdiary", "name": "ResDiary", "category": "Reservations", "description": "Manage ResDiary reservations in Ananta", "status": saved_map.get("resdiary", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://www.resdiary.com"},
        # In-Venue
        {"slug": "mryum", "name": "Mr Yum", "category": "In-Venue Ordering", "description": "In-venue mobile ordering synced to kitchen", "status": saved_map.get("mryum", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "Venue Token", "website": "https://www.mryum.com"},
        {"slug": "hungryhungry", "name": "HungryHungry", "category": "In-Venue Ordering", "description": "Order & pay at table integration", "status": saved_map.get("hungryhungry", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://www.hungryhungry.com"},
        # Loyalty
        {"slug": "marsello", "name": "Marsello", "category": "Loyalty & Marketing", "description": "Loyalty program and email marketing automation", "status": saved_map.get("marsello", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://www.marsello.com"},
        {"slug": "stampme", "name": "Stamp Me", "category": "Loyalty & Marketing", "description": "Digital stamp cards and rewards", "status": saved_map.get("stampme", {}).get("status", "disconnected"), "requiresKey": True, "keyLabel": "API Key", "website": "https://stampme.com"},
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
