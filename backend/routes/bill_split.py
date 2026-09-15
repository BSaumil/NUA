"""Guest-facing bill splitting.

Mounted so it rides the existing "/api/table/" public prefix
(server.py's PUBLIC_API_PREFIXES) — no new prefix needed. Viewing a split
and picking a mode need no guest identity, matching table QR ordering's
existing trust model: whoever has the table's link can act for that
table. Claiming a specific line/slot and paying both require a verified
guest session (routes/guest_session.py, phone OTP) so a claim — and the
loyalty points a payment earns — are tied to a real phone number, not
"whoever tapped first."
"""
from __future__ import annotations
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Request, Depends, WebSocket, WebSocketDisconnect
from database import db
from deps import get_user
from services import bill_split, split_group, split_payment, split_loyalty, split_realtime
from routes.guest_session import get_guest_session
import logging

log = logging.getLogger("bill_split")
router = APIRouter()
realtime_mgr = split_realtime.get_manager()


def _public_view(split: dict) -> dict:
    """Hand-picked fields only — never the raw doc. claimedByPhone stays
    server-side; a guest's screen only needs to know a line is claimed,
    not by whose number."""
    return {
        "id": split["id"], "tableNumber": split["tableNumber"], "status": split["status"],
        "mode": split.get("mode"),
        "lines": [
            {"id": l["id"], "productName": l["productName"], "category": l.get("category"),
             "unitPrice": l["unitPrice"], "status": l["status"]}
            for l in split["lines"]
        ],
        "equalParts": [
            {"index": p["index"], "amount": p["amount"], "status": p["status"]}
            for p in split.get("equalParts") or []
        ],
    }


async def _require_business_id(business: Optional[str]) -> str:
    """The QR code a table's split link is printed from must carry
    `?business=<slug-or-id>` — unlike table_ordering.py's menu/order QR
    codes, this one gates money changing hands, so an absent or
    unresolvable business is refused outright (400) rather than silently
    falling back to an unscoped, cross-tenant-poolable lookup."""
    from routes.online_orders import _resolve_business_id
    business_id = await _resolve_business_id(business)
    if not business_id:
        raise HTTPException(status_code=400, detail="A valid business must be specified for bill splitting")
    return business_id


@router.get("/table/{table_number}/split")
async def get_split(table_number: str, business: Optional[str] = None):
    business_id = await _require_business_id(business)
    try:
        split = await bill_split.get_or_create_split(table_number, business_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _public_view(split)


@router.post("/table/{table_number}/split/mode")
async def choose_mode(table_number: str, data: dict, business: Optional[str] = None):
    business_id = await _require_business_id(business)
    split = await bill_split.get_or_create_split(table_number, business_id)
    try:
        updated = await bill_split.set_mode(
            split["id"], data.get("mode"), data.get("equalCount"),
            custom_amounts=data.get("customAmounts"), custom_percents=data.get("customPercents"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _public_view(updated)


@router.get("/table/split/{split_id}/status")
async def split_status(split_id: str):
    split = await db.bill_splits.find_one({"id": split_id}, {"_id": 0})
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")
    return _public_view(split)


@router.post("/table/split/{split_id}/claim")
async def claim(split_id: str, data: dict, session: dict = Depends(get_guest_session)):
    result = await bill_split.claim_lines(split_id, session["phone"], data.get("lineIds") or [])
    if not result["split"]:
        raise HTTPException(status_code=404, detail="Split not found")
    return {"claimed": result["claimed"], "failed": result["failed"], "split": _public_view(result["split"])}


@router.post("/table/split/{split_id}/claim-equal")
async def claim_equal(split_id: str, data: dict, session: dict = Depends(get_guest_session)):
    idx = data.get("index")
    if idx is None:
        raise HTTPException(status_code=400, detail="index required")
    result = await bill_split.claim_equal_slot(split_id, session["phone"], int(idx))
    if not result["split"]:
        raise HTTPException(status_code=404, detail="Split not found")
    if not result["claimed"]:
        raise HTTPException(status_code=409, detail="That share was just claimed by someone else")
    return _public_view(result["split"])


@router.post("/table/split/{split_id}/release")
async def release(split_id: str, data: dict, session: dict = Depends(get_guest_session)):
    split = await bill_split.release_claim(
        split_id, session["phone"], line_ids=data.get("lineIds"), slot_index=data.get("slotIndex"))
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")
    return _public_view(split)


@router.post("/table/split/{split_id}/checkout")
async def checkout(split_id: str, data: dict, http_request: Request, session: dict = Depends(get_guest_session)):
    provider = data.get("provider", "stripe")
    if provider not in ("stripe", "crypto"):
        raise HTTPException(status_code=400, detail="provider must be 'stripe' or 'crypto'")

    split = await db.bill_splits.find_one({"id": split_id}, {"_id": 0})
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")

    try:
        payload = await bill_split.build_guest_sale_payload(
            split_id, session["phone"], line_ids=data.get("lineIds"), slot_index=data.get("slotIndex"))
    except (ValueError, LookupError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Optional tip on top of this guest's own share — added as its own
    # synthetic line (same pattern as the equal split's SPLIT-SHARE) so it
    # rides through create_transaction's normal item-priced subtotal
    # instead of needing a separate code path, and is what the guest is
    # actually charged via Stripe/Coinbase below.
    tip_amount = round(float(data.get("tipAmount") or 0), 2)
    if tip_amount < 0:
        raise HTTPException(status_code=400, detail="tipAmount can't be negative")
    items = list(payload["items"])
    charge_amount = round(payload["amount"] + tip_amount, 2)
    if tip_amount > 0:
        items.append({"productId": "SPLIT-TIP", "productName": "Tip", "quantity": 1,
                       "price": tip_amount, "modifiers": []})

    # A verified phone is exactly what grows the customer database here —
    # find_or_create_customer_by_phone resolves-or-creates a real
    # db.customers record from it (not just an identity touchpoint), so
    # the loyalty points this payment earns via create_transaction land on
    # an actual account instead of evaporating with an anonymous sale.
    from services.customer_match import find_or_create_customer_by_phone
    customer = await find_or_create_customer_by_phone(session["phone"], tag="split_bill")

    sale = {
        "items": items, "paymentMethod": "Card" if provider == "stripe" else "Crypto",
        "location": f"Table {split['tableNumber']} split", "cashier": "Guest self-checkout",
        "orderType": "dine_in", "tableNumber": split["tableNumber"],
        "customerId": customer["id"], "tipAmount": tip_amount,
    }
    guest_cashier = {"id": f"guest:{session['phone']}", "name": "Guest self-checkout", "role": "guest",
                      "businessId": split.get("businessId")}
    checkout_data = {
        "amount": charge_amount, "orderId": split_id,
        "originUrl": data.get("originUrl") or str(http_request.base_url).rstrip("/"),
        "sale": sale,
        "splitSessionId": split_id, "splitLineIds": payload["splitLineIds"],
        "splitSlotIndex": payload["splitSlotIndex"],
    }
    guest_email = (data.get("email") or "").strip()
    if guest_email:
        checkout_data["guestEmail"] = guest_email

    if provider == "stripe":
        from routes.integrations import _create_stripe_session
        response = await _create_stripe_session(checkout_data, http_request, cashier=guest_cashier)
    else:
        from routes.crypto_payments import _create_crypto_session
        response = await _create_crypto_session(checkout_data, http_request, cashier=guest_cashier)

    # Award loyalty points for this payment
    amount = payload.get("amount", 0)
    points = await split_loyalty.calculate_loyalty_points(amount)
    await split_loyalty.award_loyalty_points(customer["id"], points, split_id, "guest_split_payment")
    await realtime_mgr.broadcast_payment(split_id, session["phone"], amount)

    return response


# ============================================================================
# GROUP COORDINATION ENDPOINTS
# ============================================================================

@router.post("/table/split/{split_id}/group/create")
async def create_group(split_id: str, session: dict = Depends(get_guest_session)):
    """Create a group split (current guest is organizer)."""
    group = await split_group.create_split_group(split_id, session["phone"])
    await split_group.sync_group_to_split(split_id)
    await realtime_mgr.broadcast_update(split_id, "group_created", group)
    return group


@router.post("/table/split/{split_id}/group/invite")
async def send_invite(split_id: str, data: dict, session: dict = Depends(get_guest_session)):
    """Organizer invites another guest to group split."""
    invite_phone = data.get("phone")
    if not invite_phone:
        raise HTTPException(status_code=400, detail="phone required")

    result = await split_group.invite_guest(split_id, session["phone"], invite_phone)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    await realtime_mgr.broadcast_group_invite(split_id, invite_phone)
    return result


@router.post("/table/split/{split_id}/group/accept-invite")
async def accept_group_invite(split_id: str, data: dict, session: dict = Depends(get_guest_session)):
    """Guest accepts group invite."""
    invite_token = data.get("inviteToken")
    if not invite_token:
        raise HTTPException(status_code=400, detail="inviteToken required")

    result = await split_group.accept_invite(split_id, session["phone"], invite_token)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    await split_group.sync_group_to_split(split_id)
    await realtime_mgr.broadcast_update(split_id, "guest_joined_group", {
        "guestPhone": session["phone"]
    })
    return result


@router.get("/table/split/{split_id}/group/status")
async def get_group_status(split_id: str):
    """Get group coordination status."""
    status = await split_group.get_group_status(split_id)
    if not status:
        raise HTTPException(status_code=404, detail="No group for this split")
    return status


# ============================================================================
# PARTIAL PAYMENT / TAB ENDPOINTS
# ============================================================================

@router.post("/table/split/{split_id}/partial-checkout")
async def partial_checkout(split_id: str, data: dict, session: dict = Depends(get_guest_session)):
    """Guest pays partial amount, remainder goes on tab."""
    amount = data.get("amount", 0)
    if not amount or amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")

    # Create guest tab
    line_ids = data.get("lineIds", [])
    slot_index = data.get("slotIndex")
    total_amount = data.get("totalAmount", amount)

    tab = await split_payment.create_guest_tab(split_id, session["phone"], total_amount, line_ids, slot_index)

    # Record partial payment
    payment_result = await split_payment.record_partial_payment(tab["id"], amount, "card", split_id)

    await realtime_mgr.broadcast_payment(split_id, session["phone"], amount)

    return {
        "success": payment_result.get("success"),
        "tabId": tab["id"],
        "paidAmount": payment_result.get("paidAmount"),
        "remainingBalance": payment_result.get("remainingBalance"),
        "status": payment_result.get("status"),
    }


@router.get("/table/split/{split_id}/guest-tabs")
async def get_guest_tabs(split_id: str, session: dict = Depends(get_guest_session)):
    """Get all open tabs for current guest."""
    tabs = await split_payment.get_guest_tabs(session["phone"])
    return {"tabs": tabs, "guestPhone": session["phone"]}


@router.post("/table/split/{split_id}/staff-process-tab")
async def staff_process_tab(split_id: str, data: dict, user: dict = Depends(get_user)):
    """Staff collects remaining tab balance (staff-side only).

    This whole router is mounted under /api/table/, which server.py's
    RequireAuthMiddleware treats as a public prefix wholesale (it exists
    for the genuinely guest-facing QR-ordering/split endpoints elsewhere in
    this file). That prefix match doesn't distinguish "guest-facing" from
    "staff-only" — without an explicit Depends here, this endpoint
    (recording a real payment against a tab) was reachable by anyone on the
    internet with no credential at all, not merely unscoped to a tenant.

    Also verifies the tab's own split belongs to the caller's business —
    tab_id is an opaque id with no tenant field of its own, so without this
    check a staff member from any business who learned/guessed another
    business's tab_id could record a payment against it.
    """
    tab_id = data.get("tabId")
    amount = data.get("amount", 0)
    method = data.get("method", "cash")

    if not tab_id:
        raise HTTPException(status_code=400, detail="tabId required")

    tab = await db.split_tabs.find_one({"id": tab_id}, {"_id": 0})
    if not tab:
        raise HTTPException(status_code=404, detail="Tab not found")
    owning_split = await db.bill_splits.find_one({"id": tab.get("splitId")}, {"_id": 0, "businessId": 1})
    if not owning_split or owning_split.get("businessId") != user.get("businessId"):
        raise HTTPException(status_code=404, detail="Tab not found")

    result = await split_payment.staff_process_tab_payment(tab_id, amount, method)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    await realtime_mgr.broadcast_update(split_id, "tab_payment_received", {
        "tabId": tab_id,
        "amount": amount,
    })
    return result


# ============================================================================
# STAFF REAL-TIME MONITORING
# ============================================================================

def _claims_summary(split: dict) -> list:
    """One row per guest phone that's claimed something on this split —
    what SplitBillStaff.jsx's detail panel shows per guest, aggregated from
    the raw per-line/per-slot claimedByPhone the guest-facing _public_view
    deliberately hides."""
    by_phone: Dict[str, Dict[str, Any]] = {}
    for l in split.get("lines") or []:
        phone = l.get("claimedByPhone")
        if not phone:
            continue
        row = by_phone.setdefault(phone, {"phone": phone, "items": [], "total": 0.0, "paid": True})
        row["items"].append(l["productName"])
        row["total"] = round(row["total"] + l["unitPrice"], 2)
        row["paid"] = row["paid"] and l["status"] == "paid"
    for p in split.get("equalParts") or []:
        phone = p.get("claimedByPhone")
        if not phone:
            continue
        row = by_phone.setdefault(phone, {"phone": phone, "items": [], "total": 0.0, "paid": True})
        row["items"].append(f"Share #{p['index'] + 1}")
        row["total"] = round(row["total"] + p["amount"], 2)
        row["paid"] = row["paid"] and p["status"] == "paid"
    return list(by_phone.values())


@router.get("/table/active-splits")
async def get_active_splits(user: dict = Depends(get_user)):
    """Staff-wide monitoring feed — one row per table with an open split,
    for SplitBillStaff.jsx's dashboard grid (as opposed to /staff-status
    below, which is scoped to a single table).

    Same /api/table/ public-prefix issue as staff-process-tab below: with
    no Depends here, this returned every open split across every business
    on the deployment — guest phone numbers, item details, running
    totals — to anyone on the internet with no credential. Auth added, and
    now also businessId-scoped: db.bill_splits docs are stamped with the
    resolving business at creation (services/bill_split.get_or_create_split),
    so a logged-in staff member of one business can no longer see another
    business's open splits."""
    business_id = user.get("businessId")
    splits = await db.bill_splits.find({"status": "open", "businessId": business_id}, {"_id": 0}).to_list(200)
    out = []
    for split in splits:
        tabs = await db.split_tabs.find(
            {"splitId": split["id"], "status": {"$in": ["open", "partial"]}}, {"_id": 0}
        ).to_list(50)
        out.append({
            **split,
            "totalAmount": round(sum(l["unitPrice"] for l in split.get("lines") or []), 2),
            "claims": _claims_summary(split),
            "openTabs": tabs,
            "participants": split.get("groupParticipants") or [],
        })
    return {"splits": out}


@router.get("/table/{table_number}/split/staff-status")
async def get_staff_status(table_number: str, user: dict = Depends(get_user)):
    """Staff view of split status (all claims, payments, balances). Same
    /api/table/ public-prefix issue as the two endpoints above — was
    reachable with no credential; auth added and scoped to the caller's
    own business so a table-number collision with another business's open
    split can't surface it here either."""
    business_id = user.get("businessId")
    split = await db.bill_splits.find_one(
        {"tableNumber": str(table_number), "businessId": business_id, "status": "open"}, {"_id": 0})
    if not split:
        raise HTTPException(status_code=404, detail="No active split for this table")

    # Gather all tabs for this split
    tabs = await db.split_tabs.find({"splitId": split["id"]}, {"_id": 0}).to_list(100)

    # Get group info if exists
    group = None
    if split.get("groupMode"):
        group = await split_group.get_group_status(split["id"])

    return {
        "split": split,
        "tabs": tabs,
        "group": group,
        "connectedClients": await realtime_mgr.get_connection_count(split["id"]),
    }


# ============================================================================
# WEBSOCKET REAL-TIME SYNC
# ============================================================================

@router.websocket("/ws/split/{split_id}")
async def websocket_split_updates(split_id: str, websocket: WebSocket):
    """WebSocket endpoint for real-time split updates."""
    await websocket.accept()
    await realtime_mgr.register_connection(split_id, websocket)

    try:
        # Send initial split state
        split = await db.bill_splits.find_one({"id": split_id}, {"_id": 0})
        if split:
            await websocket.send_json({
                "type": "connected",
                "splitId": split_id,
                "split": split,
            })

        # Listen for client messages and broadcast
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "sync_request":
                split = await db.bill_splits.find_one({"id": split_id}, {"_id": 0})
                await websocket.send_json({"type": "sync_response", "split": split})

    except WebSocketDisconnect:
        await realtime_mgr.unregister_connection(split_id, websocket)
        log.info(f"Client disconnected from split {split_id}")
    except Exception as e:
        log.error(f"WebSocket error: {e}")
        await realtime_mgr.unregister_connection(split_id, websocket)
