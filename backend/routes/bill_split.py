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
from fastapi import APIRouter, HTTPException, Request, Depends
from database import db
from services import bill_split
from routes.guest_session import get_guest_session

router = APIRouter()


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


@router.get("/table/{table_number}/split")
async def get_split(table_number: str):
    try:
        split = await bill_split.get_or_create_split(table_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _public_view(split)


@router.post("/table/{table_number}/split/mode")
async def choose_mode(table_number: str, data: dict):
    split = await bill_split.get_or_create_split(table_number)
    try:
        updated = await bill_split.set_mode(split["id"], data.get("mode"), data.get("equalCount"))
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

    # A verified phone is exactly what grows the customer database here —
    # find_or_create_customer_by_phone resolves-or-creates a real
    # db.customers record from it (not just an identity touchpoint), so
    # the loyalty points this payment earns via create_transaction land on
    # an actual account instead of evaporating with an anonymous sale.
    from services.customer_match import find_or_create_customer_by_phone
    customer = await find_or_create_customer_by_phone(session["phone"], tag="split_bill")

    sale = {
        "items": payload["items"], "paymentMethod": "Card" if provider == "stripe" else "Crypto",
        "location": f"Table {split['tableNumber']} split", "cashier": "Guest self-checkout",
        "orderType": "dine_in", "tableNumber": split["tableNumber"],
        "customerId": customer["id"],
    }
    guest_cashier = {"id": f"guest:{session['phone']}", "name": "Guest self-checkout", "role": "guest"}
    checkout_data = {
        "amount": payload["amount"], "orderId": split_id,
        "originUrl": data.get("originUrl") or str(http_request.base_url).rstrip("/"),
        "sale": sale,
        "splitSessionId": split_id, "splitLineIds": payload["splitLineIds"],
        "splitSlotIndex": payload["splitSlotIndex"],
    }

    if provider == "stripe":
        from routes.integrations import _create_stripe_session
        return await _create_stripe_session(checkout_data, http_request, cashier=guest_cashier)
    from routes.crypto_payments import _create_crypto_session
    return await _create_crypto_session(checkout_data, http_request, cashier=guest_cashier)
