"""NUA v26 — Commerce extensions.

Bundles together the next batch of owner-requested features so they share one
voucher/coupon code engine, one barcode helper, and one perks model.

ENDPOINTS
  /v26/vouchers              GET/POST/PATCH/DELETE   editable promo + coupon codes
  /v26/vouchers/{code}/apply POST                    validates + returns the discount
  /v26/cart/apply-promos     POST                    auto-apply scheduled promotions to a cart
  /v26/subscriptions/plans   PATCH/DELETE            editable plans with rich perks/T&Cs/barcode
  /v26/gift-cards/sell       POST                    counter or online sale (name/email/payment/customer)
  /v26/gift-cards/assign     POST                    attach card to a customer post-issue
  /v26/events                GET/POST/PATCH/DELETE   events + experiences
  /v26/events/{id}/book      POST                    customer books an event slot
  /v26/events/ai-preview     POST                    AI suggests promo copy for a date/event

All issued codes carry a `barcode` (Code-128 friendly string) AND a manualCode
field so cashiers can scan OR key in by hand.
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Request
from database import db
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import os
import json
import re
import secrets
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v26")


def _now(): return datetime.now(timezone.utc)
def _iso(dt): return dt.isoformat()
def _uid(prefix: str) -> str: return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _new_code(prefix: str = "NUA") -> dict:
    """Mint a uniform manual code + scannable barcode. Code-128 accepts the same
    alphanumeric string so the barcode value == manualCode."""
    raw = secrets.token_hex(4).upper()         # 8 hex chars · easy to read aloud
    manual = f"{prefix}-{raw[:4]}-{raw[4:]}"
    return {"manualCode": manual, "barcode": manual}


async def _llm_json(session_id: str, system: str, user_text: str):
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=session_id, system_message=system,
        ).with_model("openai", "gpt-5.2")
        resp = await chat.send_message(UserMessage(text=user_text))
        text = (resp or "").strip().strip("`")
        try: return json.loads(text)
        except Exception:
            m = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
            return json.loads(m.group(0)) if m else {}
    except Exception as e:
        logger.warning("LLM [%s]: %s", session_id, str(e)[:200])
        return {}


# ============================================================================
# VOUCHERS / COUPONS — unified, editable, scannable
# ============================================================================
@router.get("/vouchers")
async def list_vouchers(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager", "cashier"):
        raise HTTPException(status_code=403, detail="Staff only")
    rows = await db.commerce_vouchers.find({}, {"_id": 0}).sort("createdAt", -1).to_list(500)
    return rows


@router.post("/vouchers")
async def create_voucher(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    kind = data.get("kind", "discount")
    codes = _new_code("GC" if kind == "gift" else data.get("codePrefix", "NUA"))
    v = {
        "id": _uid("VCH"),
        "name": data.get("name", "Voucher"),
        "kind": kind,  # discount | freebie | bundle | gift | marketing
        "discountType": data.get("discountType", "percent"),  # percent | fixed | free_item
        "value": float(data.get("value", 0)),
        "appliesTo": data.get("appliesTo", "cart"),   # cart | category | product
        "category": data.get("category"),
        "productIds": data.get("productIds", []),
        "minSpend": float(data.get("minSpend", 0)),
        "maxUses": int(data.get("maxUses", 0)),    # 0 = unlimited
        "usedCount": 0,
        "validFrom": data.get("validFrom"),
        "validTo": data.get("validTo"),
        "termsAndConditions": data.get("termsAndConditions", ""),
        "active": bool(data.get("active", True)),
        **codes,
        "createdAt": _iso(_now()),
        "createdBy": user["id"],
    }
    await db.commerce_vouchers.insert_one(v); v.pop("_id", None)

    # Stored-value Gift Card: when kind="gift" mint a paired gift_card that is
    # PENDING_ACTIVATION until paid for at the POS. value = initial_balance.
    if kind == "gift":
        initial = float(data.get("value", 0))
        card = {
            "id": _uid("GC"),
            "code": codes["manualCode"], "barcode": codes["barcode"],
            "voucherId": v["id"],
            "initialBalance": initial,
            "currentBalance": 0.0,           # 0 until paid + activated
            "originalAmount": initial,
            "bonus": float(data.get("bonus", 0)),
            "recipientName": data.get("recipientName", ""),
            "recipientEmail": data.get("recipientEmail", ""),
            "purchaserName": data.get("purchaserName", ""),
            "purchaserEmail": data.get("purchaserEmail", ""),
            "customerId": data.get("customerId"),
            "channel": data.get("channel", "voucher"),
            "occasion": data.get("occasion", "general"),
            "message": data.get("message", ""),
            "status": "pending_activation",
            "createdAt": _iso(_now()), "createdBy": user["id"],
        }
        await db.gift_cards.insert_one(card); card.pop("_id", None)
        v["giftCard"] = card
    return v


@router.patch("/vouchers/{vid}")
async def update_voucher(vid: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    # Never let the caller rewrite the code or usage counter
    forbidden = {"id", "manualCode", "barcode", "usedCount", "createdAt", "createdBy"}
    update = {k: v for k, v in data.items() if k not in forbidden}
    update["updatedAt"] = _iso(_now())
    r = await db.commerce_vouchers.update_one({"id": vid}, {"$set": update})
    if r.matched_count == 0: raise HTTPException(status_code=404, detail="Voucher not found")
    return {"updated": True}


@router.delete("/vouchers/{vid}")
async def delete_voucher(vid: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner only")
    r = await db.commerce_vouchers.delete_one({"id": vid})
    if r.deleted_count == 0: raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}


def _voucher_within_window(v: dict) -> bool:
    now_iso = _iso(_now())
    if v.get("validFrom") and now_iso < v["validFrom"]: return False
    if v.get("validTo") and now_iso > v["validTo"]: return False
    if v.get("maxUses", 0) and v.get("usedCount", 0) >= v["maxUses"]: return False
    return True


def _voucher_compute(v: dict, cart_items: list) -> dict:
    """Pure helper — returns {discount, appliedTo, message}."""
    subtotal = sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in cart_items)
    if subtotal < v.get("minSpend", 0):
        return {"discount": 0, "appliedTo": [], "message": f"Minimum spend ${v['minSpend']} not met"}
    # Scope
    applies_to = v.get("appliesTo", "cart")
    relevant = []
    if applies_to == "cart":
        relevant = cart_items
    elif applies_to == "category":
        relevant = [i for i in cart_items if i.get("category") == v.get("category")]
    elif applies_to == "product":
        relevant = [i for i in cart_items if (i.get("productId") or i.get("id")) in (v.get("productIds") or [])]
    rel_subtotal = sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in relevant)
    if rel_subtotal <= 0:
        return {"discount": 0, "appliedTo": [], "message": "No qualifying items in cart"}
    if v["discountType"] == "percent":
        disc = round(rel_subtotal * (float(v["value"]) / 100), 2)
    elif v["discountType"] == "fixed":
        disc = min(float(v["value"]), rel_subtotal)
    else:  # free_item — discount one item fully
        cheapest = min(relevant, key=lambda x: float(x.get("price", 0)))
        disc = float(cheapest.get("price", 0))
    return {"discount": disc, "appliedTo": [i.get("productId") or i.get("id") for i in relevant],
            "message": f"-${disc:.2f} on {len(relevant)} item(s)"}


@router.post("/vouchers/{code}/apply")
async def apply_voucher(code: str, data: dict, request: Request):
    """Cashier scans/types a code → server validates + returns discount to apply."""
    from routes.auth import get_current_user
    await get_current_user(request)
    v = await db.commerce_vouchers.find_one(
        {"$or": [{"manualCode": code.upper()}, {"barcode": code.upper()}, {"id": code}]},
        {"_id": 0},
    )
    if not v: raise HTTPException(status_code=404, detail="Code not found")
    if not v.get("active"): raise HTTPException(status_code=400, detail="Code is disabled")
    if not _voucher_within_window(v): raise HTTPException(status_code=400, detail="Code is expired or fully redeemed")
    cart = data.get("cart") or []
    res = _voucher_compute(v, cart)
    if res["discount"] <= 0:
        raise HTTPException(status_code=400, detail=res["message"])
    return {"voucher": v, **res}


@router.post("/vouchers/{vid}/redeem")
async def record_redemption(vid: str, data: dict, request: Request):
    """Called by the POS once a transaction completes with the voucher attached."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    await db.commerce_vouchers.update_one({"id": vid}, {"$inc": {"usedCount": 1}})
    await db.voucher_redemptions.insert_one({
        "id": _uid("RED"), "voucherId": vid,
        "txId": data.get("txId"), "customerId": data.get("customerId"),
        "amount": float(data.get("amount", 0)),
        "createdAt": _iso(_now()), "createdBy": user["id"],
    })
    return {"recorded": True}


# ============================================================================
# AUTO-APPLY PROMOTIONS (the bug fix)
# ============================================================================
def _promotion_active_now(promo: dict) -> bool:
    """Honour startDate/endDate, activeDays, and start/endTime."""
    if not promo.get("active"): return False
    now = _now()
    today = now.date().isoformat()
    if promo.get("startDate") and today < promo["startDate"]: return False
    if promo.get("endDate") and today > promo["endDate"]: return False
    days = promo.get("activeDays") or []
    if days and now.strftime("%A") not in days: return False
    hhmm = now.strftime("%H:%M")
    if promo.get("startTime") and hhmm < promo["startTime"]: return False
    if promo.get("endTime") and hhmm > promo["endTime"]: return False
    return True


@router.post("/cart/apply-promos")
async def apply_promos_to_cart(data: dict, request: Request):
    """Given a cart, return every promotion that auto-fires *right now* plus the
    computed discount. The POS shows them as "auto-applied" chips with × to remove."""
    from routes.auth import get_current_user
    await get_current_user(request)
    cart = data.get("cart") or []
    if not cart:
        return {"applied": [], "totalDiscount": 0}

    promos = await db.promotions.find({"active": True}, {"_id": 0}).to_list(200)
    applied = []
    total = 0.0
    for p in promos:
        if not _promotion_active_now(p): continue
        relevant = cart
        if p.get("type") == "bundle" and p.get("products"):
            ids = {i.get("productId") or i.get("id") for i in cart}
            if not set(p["products"]).issubset(ids): continue
            relevant = [i for i in cart if (i.get("productId") or i.get("id")) in p["products"]]
        elif p.get("type") == "category" and p.get("category"):
            relevant = [i for i in cart if i.get("category") == p["category"]]
            if not relevant: continue
        rel_subtotal = sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in relevant)
        disc = round(rel_subtotal * (float(p.get("discount", 0)) / 100), 2)
        if disc <= 0: continue
        applied.append({
            "promotionId": p["id"], "name": p["name"],
            "discount": disc, "percentage": p["discount"],
            "appliedTo": [i.get("productId") or i.get("id") for i in relevant],
            "label": f"{p['name']} — {p['discount']}% off",
        })
        total += disc
    return {"applied": applied, "totalDiscount": round(total, 2)}


@router.get("/promotions/active-now")
async def list_active_promotions_now(request: Request):
    """POS-facing: returns every promotion that is *currently* live based on
    today's date, weekday, and current time of day. Staff use this so they know
    exactly what's running without scrolling through inactive promos."""
    from routes.auth import get_current_user
    await get_current_user(request)
    promos = await db.promotions.find({"active": True}, {"_id": 0}).to_list(500)
    return [p for p in promos if _promotion_active_now(p)]


# ============================================================================
# SUBSCRIPTIONS — rich plan model + edit/delete
# ============================================================================
@router.patch("/subscriptions/plans/{plan_id}")
async def update_sub_plan(plan_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    forbidden = {"id", "createdAt"}
    update = {k: v for k, v in data.items() if k not in forbidden}
    # If the plan doesn't yet have a barcode, mint one (legacy plans)
    if "manualCode" not in update:
        existing = await db.subscription_plans.find_one({"id": plan_id}, {"_id": 0})
        if existing and not existing.get("manualCode"):
            update.update(_new_code("SUB"))
    update["updatedAt"] = _iso(_now())
    r = await db.subscription_plans.update_one({"id": plan_id}, {"$set": update})
    if r.matched_count == 0: raise HTTPException(status_code=404, detail="Plan not found")
    return {"updated": True}


@router.delete("/subscriptions/plans/{plan_id}")
async def delete_sub_plan(plan_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    r = await db.subscription_plans.delete_one({"id": plan_id})
    if r.deleted_count == 0: raise HTTPException(status_code=404, detail="Plan not found")
    return {"deleted": True}


# ============================================================================
# GIFT CARDS — sell online + at counter + assign to customer
# ============================================================================
@router.get("/gift-cards")
async def list_gift_cards(request: Request, status: Optional[str] = None):
    from routes.auth import get_current_user
    await get_current_user(request)
    q = {}
    if status: q["status"] = status
    rows = await db.gift_cards.find(q, {"_id": 0}).sort("createdAt", -1).to_list(500)
    return rows


@router.post("/gift-cards/sell")
async def sell_gift_card(data: dict, request: Request):
    """Channel-aware sale. Owner/manager/cashier can sell at counter; the same
    endpoint is used by the public store-front for online purchase (would be
    gated by a separate route in production)."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager", "cashier"):
        raise HTTPException(status_code=403, detail="Staff only")
    amount = float(data.get("amount", 0))
    if amount <= 0: raise HTTPException(status_code=400, detail="Amount must be > 0")
    bonus = float(data.get("bonus", 20 if amount >= 100 else 0))
    codes = _new_code("GC")
    starting = round(amount + bonus, 2)
    # Counter sales activate immediately (cash/card taken at till). Online sales
    # land as 'pending_activation' and need to be paid for via Stripe etc.
    channel = data.get("channel", "counter")
    status = "active" if channel == "counter" else "pending_activation"
    card = {
        "id": _uid("GC"),
        "code": codes["manualCode"], "barcode": codes["barcode"],
        "initialBalance": amount,
        "currentBalance": starting if status == "active" else 0.0,
        "amount": starting,                                   # legacy mirror
        "originalAmount": amount, "bonus": bonus,
        "recipientName": data.get("recipientName", ""),
        "recipientEmail": data.get("recipientEmail", ""),
        "purchaserName": data.get("purchaserName", ""),
        "purchaserEmail": data.get("purchaserEmail", ""),
        "customerId": data.get("customerId"),
        "channel": channel,
        "paymentMethod": data.get("paymentMethod", "card"),
        "occasion": data.get("occasion", "general"),
        "message": data.get("message", ""),
        "status": status,
        "createdAt": _iso(_now()), "createdBy": user["id"],
    }
    await db.gift_cards.insert_one(card); card.pop("_id", None)
    if status == "active":
        await _record_gift_txn(card, "activate", starting, 0.0, starting,
                               user["id"], data.get("transactionId"))
    return card


@router.post("/gift-cards/{code_or_id}/assign")
async def assign_gift_card(code_or_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager", "cashier"):
        raise HTTPException(status_code=403, detail="Staff only")
    customer_id = data.get("customerId")
    if not customer_id: raise HTTPException(status_code=400, detail="customerId required")
    r = await db.gift_cards.update_one(
        {"$or": [{"code": code_or_id.upper()}, {"barcode": code_or_id.upper()}, {"id": code_or_id}]},
        {"$set": {"customerId": customer_id, "assignedAt": _iso(_now()), "assignedBy": user["id"]}},
    )
    if r.matched_count == 0: raise HTTPException(status_code=404, detail="Card not found")
    return {"assigned": True}


@router.get("/gift-cards/lookup/{code}")
async def lookup_gift_card(code: str):
    """Lookup by barcode or manual code — used by POS scan flow."""
    card = await db.gift_cards.find_one(
        {"$or": [{"code": code.upper()}, {"barcode": code.upper()}, {"id": code}]},
        {"_id": 0},
    )
    if not card: raise HTTPException(status_code=404, detail="Card not found")
    # Back-fill balance for legacy cards that pre-date the stored-value rewrite.
    if "currentBalance" not in card and "amount" in card:
        card["currentBalance"] = float(card.get("amount", 0))
        card["initialBalance"] = float(card.get("originalAmount", card.get("amount", 0)))
    return card


@router.get("/gift-cards/{code}/transactions")
async def gift_card_transactions(code: str, request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    card = await db.gift_cards.find_one(
        {"$or": [{"code": code.upper()}, {"barcode": code.upper()}, {"id": code}]},
        {"_id": 0, "id": 1},
    )
    if not card: raise HTTPException(status_code=404, detail="Card not found")
    rows = await db.gift_card_transactions.find({"giftCardId": card["id"]}, {"_id": 0}).sort("createdAt", 1).to_list(500)
    return rows


async def _record_gift_txn(card: dict, txn_type: str, amount: float, balance_before: float,
                           balance_after: float, user_id: str, ref: Optional[str] = None) -> dict:
    txn = {
        "id": _uid("GCT"),
        "giftCardId": card["id"],
        "giftCardCode": card.get("code"),
        "type": txn_type,          # issue | activate | redeem | refund | adjust
        "amount": round(float(amount), 2),
        "balanceBefore": round(float(balance_before), 2),
        "balanceAfter": round(float(balance_after), 2),
        "ref": ref,                # tx/order id or note
        "createdAt": _iso(_now()),
        "createdBy": user_id,
    }
    await db.gift_card_transactions.insert_one(txn); txn.pop("_id", None)
    return txn


@router.post("/gift-cards/{code}/activate")
async def activate_gift_card(code: str, data: dict, request: Request):
    """Activate a pending gift card. Called by POS *after* the cart payment that
    pays for the card has settled successfully. Idempotent: re-activating an
    already-active card just no-ops with the current state."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager", "cashier"):
        raise HTTPException(status_code=403, detail="Staff only")
    card = await db.gift_cards.find_one(
        {"$or": [{"code": code.upper()}, {"barcode": code.upper()}, {"id": code}]},
        {"_id": 0},
    )
    if not card: raise HTTPException(status_code=404, detail="Card not found")
    if card.get("status") == "active":
        return {"activated": False, "alreadyActive": True, "card": card}
    if card.get("status") not in ("pending_activation", None):
        raise HTTPException(status_code=400, detail=f"Card status '{card.get('status')}' cannot be activated")
    initial = float(card.get("initialBalance") or card.get("originalAmount") or card.get("amount") or 0)
    bonus = float(card.get("bonus", 0))
    starting = round(initial + bonus, 2)
    await db.gift_cards.update_one(
        {"id": card["id"]},
        {"$set": {"status": "active", "currentBalance": starting,
                  "initialBalance": initial,
                  "activatedAt": _iso(_now()), "activatedBy": user["id"],
                  "activationTxId": data.get("transactionId")}},
    )
    txn = await _record_gift_txn(card, "activate", starting, 0.0, starting,
                                 user["id"], data.get("transactionId"))
    card = await db.gift_cards.find_one({"id": card["id"]}, {"_id": 0})
    return {"activated": True, "card": card, "transaction": txn}


@router.post("/gift-cards/{code}/redeem")
async def redeem_gift_card_partial(code: str, data: dict, request: Request):
    """Atomic partial redemption. Requires card.status == 'active' AND sufficient
    balance. Records a ledger entry and returns the new balance."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager", "cashier"):
        raise HTTPException(status_code=403, detail="Staff only")
    amount = float(data.get("amount", 0))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")
    upper = code.upper()
    # Atomic deduction — guarantees no double-spend even under concurrency.
    card = await db.gift_cards.find_one_and_update(
        {"$or": [{"code": upper}, {"barcode": upper}, {"id": code}],
         "status": "active", "currentBalance": {"$gte": amount}},
        {"$inc": {"currentBalance": -amount}},
        return_document=False,
    )
    if not card:
        exists = await db.gift_cards.find_one(
            {"$or": [{"code": upper}, {"barcode": upper}, {"id": code}]}, {"_id": 0})
        if not exists: raise HTTPException(status_code=404, detail="Card not found")
        if exists.get("status") != "active":
            raise HTTPException(status_code=400, detail=f"Card is {exists.get('status')}")
        raise HTTPException(status_code=400, detail=f"Insufficient balance (${exists.get('currentBalance', 0):.2f})")
    balance_before = float(card.get("currentBalance", 0))
    balance_after = round(balance_before - amount, 2)
    if balance_after <= 0.001:
        await db.gift_cards.update_one({"id": card["id"]}, {"$set": {"status": "depleted", "depletedAt": _iso(_now())}})
    txn = await _record_gift_txn({"id": card["id"], "code": card.get("code")}, "redeem",
                                 amount, balance_before, balance_after,
                                 user["id"], data.get("transactionId"))
    return {"redeemed": amount, "newBalance": balance_after, "transaction": txn}


# ============================================================================
# EVENTS & EXPERIENCES — bookable + AI marketing preview
# ============================================================================
@router.get("/events")
async def list_events(request: Request, upcomingOnly: bool = False):
    from routes.auth import get_current_user
    await get_current_user(request)
    q = {}
    if upcomingOnly:
        q["date"] = {"$gte": _now().date().isoformat()}
    rows = await db.events.find(q, {"_id": 0}).sort("date", 1).to_list(200)
    return rows


@router.post("/events")
async def create_event(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    ev = {
        "id": _uid("EVT"),
        "title": data.get("title", "Untitled Event"),
        "description": data.get("description", ""),
        "date": data.get("date"),           # YYYY-MM-DD
        "startTime": data.get("startTime", "18:00"),
        "endTime": data.get("endTime", "21:00"),
        "capacity": int(data.get("capacity", 30)),
        "pricePerGuest": float(data.get("pricePerGuest", 0)),
        "image": data.get("image"),
        "category": data.get("category", "experience"),   # tasting | live_music | workshop | private | experience
        "bookings": [],
        "termsAndConditions": data.get("termsAndConditions", ""),
        "active": True,
        "createdAt": _iso(_now()), "createdBy": user["id"],
    }
    await db.events.insert_one(ev); ev.pop("_id", None)
    return ev


@router.patch("/events/{eid}")
async def update_event(eid: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    update = {k: v for k, v in data.items() if k not in {"id", "createdAt", "bookings"}}
    update["updatedAt"] = _iso(_now())
    r = await db.events.update_one({"id": eid}, {"$set": update})
    if r.matched_count == 0: raise HTTPException(status_code=404, detail="Event not found")
    return {"updated": True}


@router.delete("/events/{eid}")
async def delete_event(eid: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    r = await db.events.delete_one({"id": eid})
    if r.deleted_count == 0: raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}


@router.post("/events/{eid}/book")
async def book_event(eid: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    ev = await db.events.find_one({"id": eid}, {"_id": 0})
    if not ev: raise HTTPException(status_code=404, detail="Event not found")
    party = int(data.get("partySize", 1))
    booked = sum(int(b.get("partySize", 0)) for b in ev.get("bookings", []))
    if booked + party > ev.get("capacity", 0):
        raise HTTPException(status_code=400, detail=f"Only {ev['capacity'] - booked} seats left")
    booking = {
        "id": _uid("EVB"), "guestName": data.get("guestName", "Guest"),
        "guestEmail": data.get("guestEmail", ""), "guestPhone": data.get("guestPhone", ""),
        "partySize": party,
        "notes": data.get("notes", ""),
        "customerId": data.get("customerId"),
        "createdAt": _iso(_now()), "createdBy": user["id"],
    }
    await db.events.update_one({"id": eid}, {"$push": {"bookings": booking}})
    return booking


@router.post("/events/ai-preview")
async def event_ai_preview(data: dict, request: Request):
    """Owner asks: 'given this date, what should we promote?' LLM looks at events
    on that date + the day-of-week + loyalty tiers and drafts marketing copy."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    date = data.get("date") or _now().date().isoformat()
    events = await db.events.find({"date": date}, {"_id": 0}).to_list(20)
    tiers = await db.loyalty_tiers.find({}, {"_id": 0}).to_list(10)
    sys_msg = (
        "You are a restaurant marketing director. Given the date, scheduled events, "
        "and loyalty tiers, draft promotional copy for an email + SMS that combines "
        "the events with a tier-specific perk. Return STRICT JSON: "
        '{"subject":"...","emailBody":"...","sms":"...","highlights":["..."]}'
    )
    user_text = json.dumps({"date": date, "dayOfWeek": datetime.fromisoformat(date).strftime("%A"),
                            "events": events, "tiers": tiers[:5]})
    out = await _llm_json(f"event-mkt-{uuid.uuid4().hex[:6]}", sys_msg, user_text)
    return {"date": date, "events": events, "preview": out or {}}


# ============================================================================
# AI MARKETING EMAILS — autonomous generator
# ============================================================================
@router.post("/marketing/email/generate")
async def generate_marketing_email(data: dict, request: Request):
    """LLM drafts a full marketing email featuring upcoming events, active
    vouchers, and tier-specific perks. Returns JSON the owner can edit + send.
    Audience: 'all' | 'tier:Gold' | 'segment:lapsed' | etc."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    audience = data.get("audience", "all")
    tone = data.get("tone", "friendly")
    horizon_days = int(data.get("horizonDays", 14))
    today_iso = _now().date().isoformat()
    until_iso = (_now() + timedelta(days=horizon_days)).date().isoformat()
    # Pull data once, in parallel where possible.
    events = await db.events.find(
        {"active": True, "date": {"$gte": today_iso, "$lte": until_iso}},
        {"_id": 0}).sort("date", 1).to_list(20)
    vouchers = await db.commerce_vouchers.find(
        {"active": True, "kind": {"$in": ["discount", "freebie", "bundle", "marketing"]}},
        {"_id": 0}).to_list(20)
    tiers = await db.loyalty_tiers.find({}, {"_id": 0}).to_list(10)
    if not events and not vouchers and not tiers:
        raise HTTPException(status_code=400, detail="Nothing to promote — add events, vouchers or tiers first")

    sys_msg = (
        "You are NUA's autonomous marketing engine. Draft a single marketing email "
        "for a restaurant. Include: catchy subject, preheader, warm opening, a section "
        "highlighting upcoming events with dates, a section featuring 1-3 active "
        "vouchers/codes the reader can use, and a callout for the audience's tier "
        "perks (or generic if 'all'). Keep it under 320 words. Tone: {tone}. "
        "Return STRICT JSON: "
        '{"subject":"...","preheader":"...","emailBody":"...","sms":"...","cta":"...",'
        '"featuredEventIds":["..."],"featuredVoucherIds":["..."],"highlights":["..."]}'
    ).replace("{tone}", tone)
    user_text = json.dumps({
        "audience": audience,
        "windowFrom": today_iso, "windowTo": until_iso,
        "events": events[:10],
        "vouchers": [{"id": v["id"], "name": v["name"], "code": v.get("manualCode"),
                      "kind": v["kind"], "discountType": v["discountType"], "value": v["value"]}
                     for v in vouchers],
        "tiers": [{"name": t.get("name"), "perks": t.get("perks", [])} for t in tiers[:5]],
    })
    draft = await _llm_json(f"mkt-email-{uuid.uuid4().hex[:6]}", sys_msg, user_text) or {}

    # Persist as a draft so it appears in the marketing inbox / can be sent later.
    row = {
        "id": _uid("MKT"),
        "audience": audience, "tone": tone, "horizonDays": horizon_days,
        "subject": draft.get("subject", ""), "preheader": draft.get("preheader", ""),
        "emailBody": draft.get("emailBody", ""), "sms": draft.get("sms", ""),
        "cta": draft.get("cta", ""),
        "featuredEventIds": draft.get("featuredEventIds", []),
        "featuredVoucherIds": draft.get("featuredVoucherIds", []),
        "highlights": draft.get("highlights", []),
        "status": "draft",
        "createdAt": _iso(_now()), "createdBy": user["id"],
    }
    await db.marketing_emails.insert_one(row); row.pop("_id", None)
    return row


@router.get("/marketing/emails")
async def list_marketing_emails(request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    rows = await db.marketing_emails.find({}, {"_id": 0}).sort("createdAt", -1).to_list(100)
    return rows


@router.patch("/marketing/emails/{mid}")
async def update_marketing_email(mid: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    update = {k: v for k, v in data.items() if k not in {"id", "createdAt"}}
    update["updatedAt"] = _iso(_now())
    r = await db.marketing_emails.update_one({"id": mid}, {"$set": update})
    if r.matched_count == 0: raise HTTPException(status_code=404, detail="Email not found")
    return {"updated": True}


@router.delete("/marketing/emails/{mid}")
async def delete_marketing_email(mid: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner": raise HTTPException(status_code=403, detail="Owner only")
    r = await db.marketing_emails.delete_one({"id": mid})
    if r.deleted_count == 0: raise HTTPException(status_code=404, detail="Not found")
    return {"deleted": True}


# ============================================================================
# STAFF AVAILABILITY (normal days + blackout periods)
# ============================================================================
@router.get("/staff/{staff_id}/availability")
async def get_availability(staff_id: str, request: Request):
    from routes.auth import get_current_user
    await get_current_user(request)
    a = await db.staff_availability.find_one({"staffId": staff_id}, {"_id": 0})
    return a or {"staffId": staff_id, "weeklyAvailable": [], "blackoutDates": []}


@router.put("/staff/{staff_id}/availability")
async def set_availability(staff_id: str, data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    doc = {
        "staffId": staff_id,
        "weeklyAvailable": data.get("weeklyAvailable", []),    # ["Mon","Tue",...]
        "blackoutDates": data.get("blackoutDates", []),         # [{"from":"YYYY-MM-DD","to":"YYYY-MM-DD","reason":"holiday"}]
        "preferredHours": data.get("preferredHours", {}),       # {"Mon": "09:00-17:00"}
        "updatedAt": _iso(_now()), "updatedBy": user["id"],
    }
    await db.staff_availability.update_one({"staffId": staff_id}, {"$set": doc}, upsert=True)
    return {"updated": True, "availability": doc}


# ============================================================================
# ROSTER — clear all + integrity on staff delete
# ============================================================================
@router.post("/roster/clear-all")
async def roster_clear_all(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    week = data.get("week")  # optional: "YYYY-WW" or date range
    q = {}
    if week:
        q["week"] = week
    res = await db.roster_shifts.delete_many(q)
    return {"cleared": res.deleted_count}


@router.post("/roster/sync-staff")
async def sync_roster_staff(request: Request):
    """Audit + clean: remove shifts referencing deleted staff, dedupe simultaneous
    overlapping shifts of the same person on the same day. Idempotent."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    staff_ids = {s["id"] for s in await db.auth_users.find({"role": {"$in": ["cashier", "barista", "kitchen", "manager"]}}, {"_id": 0, "id": 1}).to_list(2000)}
    # Drop orphans
    orphans = await db.roster_shifts.delete_many({"staff_id": {"$nin": list(staff_ids)}})
    # Dedupe by (staff_id, date, start, end)
    pipeline = [
        {"$group": {"_id": {"staff_id": "$staff_id", "date": "$date", "start": "$start", "end": "$end"},
                    "ids": {"$push": "$id"}, "n": {"$sum": 1}}},
        {"$match": {"n": {"$gt": 1}}},
    ]
    dupes = await db.roster_shifts.aggregate(pipeline).to_list(2000)
    dropped = 0
    for d in dupes:
        keep, *kill = d["ids"]
        if kill:
            r = await db.roster_shifts.delete_many({"id": {"$in": kill}})
            dropped += r.deleted_count
    return {"orphansRemoved": orphans.deleted_count, "duplicatesRemoved": dropped}


# ============================================================================
# CUSTOMER DISPLAY — enriched current cart
# ============================================================================
@router.post("/cfd/push")
async def cfd_push(data: dict, request: Request):
    """POS terminal pushes the live cart + customer here so the customer-facing
    display can render it. One doc per terminal/session (keyed by terminalId)."""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    terminal_id = data.get("terminalId") or user["id"]
    doc = {
        "terminalId": terminal_id,
        "cart": data.get("cart") or [],
        "selectedCustomer": data.get("selectedCustomer"),
        "tableNumber": data.get("tableNumber"),
        "walkInName": data.get("walkInName"),
        "updatedAt": _iso(_now()),
        "cashier": user.get("name"),
    }
    await db.cfd_live.update_one({"terminalId": terminal_id}, {"$set": doc}, upsert=True)
    return {"pushed": True}


@router.get("/cfd/enriched")
async def cfd_enriched(request: Request, terminalId: Optional[str] = None):
    """Live cart + customer name OR walk-in booking name, table number, and
    points earned/missed this visit. Prefers a live pushed feed; falls back to
    pos_tabs for legacy callers."""
    live = None
    if terminalId:
        live = await db.cfd_live.find_one({"terminalId": terminalId}, {"_id": 0})
    if not live:
        live = await db.cfd_live.find_one({}, {"_id": 0}, sort=[("updatedAt", -1)])
    if not live:
        tab = await db.pos_tabs.find_one({"status": {"$in": ["open", "active", None]}}, {"_id": 0}, sort=[("createdAt", -1)])
        live = {
            "cart": (tab or {}).get("cart") or [],
            "selectedCustomer": (tab or {}).get("selectedCustomer"),
            "tableNumber": (tab or {}).get("tableNumber") or (tab or {}).get("tableId"),
            "walkInName": (tab or {}).get("walkInName"),
        }
    customer = live.get("selectedCustomer")
    cart = live.get("cart") or []
    subtotal = sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in cart)
    cfg = await db.loyalty_config.find_one({}, {"_id": 0}) or {}
    earn_rate = float(cfg.get("earnRate", 1))
    points_earned = int(subtotal * earn_rate) if customer else 0
    points_missed = 0 if customer else int(subtotal * earn_rate)
    name_display = (customer or {}).get("name") if customer else live.get("walkInName")
    return {
        "cart": cart, "subtotal": round(subtotal, 2),
        "customerName": name_display,
        "isMember": bool(customer),
        "membershipTier": (customer or {}).get("membershipTier"),
        "tableNumber": live.get("tableNumber"),
        "pointsEarned": points_earned,
        "pointsMissed": points_missed,
        "updatedAt": _iso(_now()),
    }
