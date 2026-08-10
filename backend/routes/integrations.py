from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
from datetime import datetime
from database import db
from deps import get_user, require_owner_or_manager
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

# ============ NUA CONNECT — INTEGRATIONS HUB API ============
# Real registry-driven integration hub. Status is never faked: a provider is
# "connected" only once its connector's test_connection has actually
# succeeded against that provider's real API, "pending_accreditation" for
# the 11 CDR banks always (regardless of credentials), and
# "not_implemented" for every provider that doesn't have connector code yet
# — never silently presented as available. See services/connect/.
from services.connect.registry import all_providers, get_provider
from services.connect import manager
from services.connect.base import ConnectorError


@router.get("/integrations")
async def get_integrations(user: dict = Depends(get_user)):
    """Every provider NUA Connect knows about, with this business's real,
    live status for each — not a hardcoded flag."""
    business_id = user.get("businessId")
    return [await manager.describe_provider(business_id, meta) for meta in all_providers()]


@router.get("/integrations/{slug}")
async def get_integration_detail(slug: str, user: dict = Depends(get_user)):
    meta = get_provider(slug)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown provider")
    return await manager.describe_provider(user.get("businessId"), meta)


@router.post("/integrations/{slug}/connect")
async def connect_integration(slug: str, data: dict, user: dict = Depends(require_owner_or_manager)):
    """Store credentials and (for providers with a real connector) actually
    test them against the provider before ever reporting 'connected'."""
    meta = get_provider(slug)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown provider")
    if not data:
        raise HTTPException(status_code=400, detail="Credentials required")
    try:
        result = await manager.connect_provider(user.get("businessId"), slug, data)
    except manager.NotImplementedProvider:
        raise HTTPException(status_code=501, detail=f"{meta.name} does not have a working connector yet")
    if result.get("status") == "error":
        raise HTTPException(status_code=502, detail=f"Could not verify {meta.name} credentials: {result.get('error')}")
    return result


@router.post("/integrations/{slug}/disconnect")
async def disconnect_integration(slug: str, user: dict = Depends(require_owner_or_manager)):
    meta = get_provider(slug)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown provider")
    await manager.disconnect_provider(user.get("businessId"), slug)
    return {"status": "disconnected"}


@router.post("/integrations/{slug}/sync")
async def sync_integration(slug: str, sync_type: str = "sales", user: dict = Depends(require_owner_or_manager)):
    """Trigger a real inbound sync. sync_type is one of catalog | sales | customers
    (whichever the provider's connector supports — see its `capabilities`)."""
    meta = get_provider(slug)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown provider")
    try:
        result = await manager.run_sync(user.get("businessId"), slug, sync_type)
    except manager.NotImplementedProvider:
        raise HTTPException(status_code=501, detail=f"{meta.name} does not have a working connector yet")
    except ConnectorError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return result


@router.get("/integrations/{slug}/credentials")
async def get_integration_credentials(slug: str, user: dict = Depends(require_owner_or_manager)):
    """Masked (last-4-only) view of stored credential field values — never
    the raw secret, which is only ever decrypted in-process for a call."""
    from services.connect.credentials import get_credentials_masked
    masked = await get_credentials_masked(user.get("businessId"), slug)
    if masked is None:
        raise HTTPException(status_code=404, detail="No credentials on file")
    return masked


# ---- Reporting / audit surface — the raw sync-run data end to end ----

@router.get("/integrations/sync-runs/history")
async def get_sync_history(provider: Optional[str] = None, limit: int = 50, user: dict = Depends(get_user)):
    return await manager.sync_history(user.get("businessId"), provider, limit)


@router.get("/integrations/sync-runs/{run_id}")
async def get_sync_run_detail(run_id: str, user: dict = Depends(get_user)):
    from services.connect.sync_log import get_sync_run
    run = await get_sync_run(user.get("businessId"), run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Sync run not found")
    return run


# ---- Inbound webhook — real-time push instead of waiting for the next poll ----

@router.post("/webhooks/square")
async def square_webhook(request: Request):
    """Square pushes order/customer/catalog change events here in real time.
    Square doesn't include NUA's businessId in the payload, so the owning
    business is identified the same way the signature itself is verified:
    by finding whose stored webhook signing key actually validates this
    request. That also means an unrecognized/forged request never touches
    any business's data — it's rejected before a business is even resolved.
    """
    from services.connect.connectors.square import SquareConnector
    from services.connect.credentials import get_credentials
    from services.connect.sync_log import SyncRun

    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    connector = SquareConnector()

    candidates = await db.integration_credentials.find(
        {"provider": "square"}, {"_id": 0, "businessId": 1}
    ).to_list(1000)

    for cand in candidates:
        business_id = cand["businessId"]
        creds = await get_credentials(business_id, "square")
        if creds and connector.verify_webhook(body, headers, creds):
            import json
            event = json.loads(body)
            async with SyncRun(business_id, "square", "webhook", direction="inbound") as run:
                await connector.handle_webhook_event(event, business_id, run)
            return {"received": True}

    raise HTTPException(status_code=401, detail="Signature verification failed")
