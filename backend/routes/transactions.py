from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from database import db
from deps import get_user, require_owner_or_manager
from models.promotion import Promotion, PromotionCreate
from models.transaction import Transaction, TransactionCreate
from models.gift_card import GiftCard, GiftCardCreate
from models.refund import Refund, RefundCreate
import uuid

router = APIRouter()

# ============ PROMOTIONS API ============
@router.get("/promotions")
async def get_promotions():
    from utils.mongo_safe import safe_parse_list
    promotions = await db.promotions.find({}, {"_id": 0}).to_list(1000)
    return safe_parse_list(promotions, Promotion, where="promotions")

@router.get("/promotions/active")
async def get_active_promotions():
    from utils.mongo_safe import safe_parse_list
    promotions = await db.promotions.find({"active": True}, {"_id": 0}).to_list(1000)
    return safe_parse_list(promotions, Promotion, where="promotions")

@router.post("/promotions", response_model=Promotion)
async def create_promotion(promotion: PromotionCreate, _user: dict = Depends(require_owner_or_manager)):
    promo_obj = Promotion(**promotion.dict())
    await db.promotions.insert_one(promo_obj.dict())
    return promo_obj

@router.put("/promotions/{promo_id}")
async def update_promotion(promo_id: str, data: dict, _user: dict = Depends(require_owner_or_manager)):
    allowed = {"name", "type", "discount", "active", "schedule",
               "products", "category", "categories",
               "pricingMode", "bundlePrice",
               "originalPrice", "discountedPrice",
               "minQuantity", "maxQuantity", "stackable",
               "startDate", "endDate", "activeDays", "startTime", "endTime"}
    update_data = {k: v for k, v in data.items() if k in allowed}
    result = await db.promotions.find_one_and_update({"id": promo_id}, {"$set": update_data}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Promotion not found")
    result.pop("_id", None)
    return result

@router.delete("/promotions/{promo_id}")
async def delete_promotion(promo_id: str, _user: dict = Depends(require_owner_or_manager)):
    result = await db.promotions.delete_one({"id": promo_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return {"message": "Promotion deleted"}

# ============ TRANSACTIONS API ============
@router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    payment_method: Optional[str] = None,
    location: Optional[str] = None,
    _user: dict = Depends(get_user),
):
    query = {}
    if payment_method:
        query["paymentMethod"] = payment_method
    if location:
        query["location"] = location
    if start_date and end_date:
        query["timestamp"] = {
            "$gte": datetime.fromisoformat(start_date),
            "$lte": datetime.fromisoformat(end_date)
        }
    transactions = await db.transactions.find(query, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    from utils.mongo_safe import safe_parse_list
    return safe_parse_list(transactions, Transaction, where="transactions")

@router.post("/transactions", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate, user: dict = Depends(get_user)):
    items_list = []
    subtotal = 0
    for item in transaction.items:
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Invalid quantity for {item.productName}")
        item_dict = item.dict()
        # Server-authoritative pricing: unit price comes from the catalog, not
        # the request body. Modifier surcharges are added on top (clamped to
        # non-negative). Unknown productIds (open/custom lines) keep the client
        # price, floored at zero.
        product = await db.products.find_one({"id": item.productId}, {"_id": 0, "price": 1})
        modifier_surcharge = sum(max(m.price, 0) for m in item.modifiers)
        if product is not None and isinstance(product.get("price"), (int, float)):
            unit_price = float(product["price"]) + modifier_surcharge
        else:
            unit_price = max(item.price, 0)
        item_dict["price"] = round(unit_price, 2)
        item_total = unit_price * item.quantity
        item_dict["total"] = round(item_total, 2)
        subtotal += item_total
        items_list.append(item_dict)

    # Apply customer membership-tier discount
    tier_discount = 0
    loyalty_multiplier = 1.0
    if transaction.customerId:
        customer = await db.customers.find_one({"id": transaction.customerId})
        if customer:
            tier = customer.get("membershipTier", "Bronze")
            if tier == "Silver":
                tier_discount = subtotal * 0.03
                loyalty_multiplier = 1.25
            elif tier == "Gold":
                tier_discount = subtotal * 0.05
                loyalty_multiplier = 1.5
            elif tier == "Platinum":
                tier_discount = subtotal * 0.10
                loyalty_multiplier = 2.0

    # Voucher/promotion discounts applied at the POS + loyalty-point redemption.
    # Amounts are clamped non-negative and the combined discount can never
    # exceed the subtotal.
    applied_discounts = [d.dict() for d in transaction.appliedDiscounts]
    for d in applied_discounts:
        d["amount"] = max(float(d.get("amount") or 0), 0)
    voucher_discount = sum(d["amount"] for d in applied_discounts)
    points_discount = max(float(transaction.pointsDiscount or 0), 0)
    discount_total = min(round(tier_discount + voucher_discount + points_discount, 2), round(subtotal, 2))

    # Menu/product prices are GST-inclusive — the configured price IS what the
    # customer pays, GST is a component disclosed on the receipt, not an
    # amount added on top of the subtotal.
    net_before_surcharge = max(subtotal - discount_total, 0)

    # Auto-surcharge (weekend/public holiday, configured in Settings >
    # Surcharges) applies on top of the GST-inclusive net — a genuine
    # additional fee, unlike GST which is already baked into subtotal.
    surcharge_percent = 0.0
    surcharge_reason = None
    try:
        from routes.enterprise_features import check_surcharge
        surcharge_info = await check_surcharge()
        surcharge_percent = float(surcharge_info.get("surchargePercent") or 0)
        surcharge_reason = surcharge_info.get("reason")
    except Exception:
        pass
    surcharge_amount = round(net_before_surcharge * surcharge_percent / 100, 2)

    total = net_before_surcharge + surcharge_amount
    # GST component contained within the final (GST-inclusive) total, at the
    # standard AU 10%-inclusive rate: gst = total / 11.
    gst = total / 11
    points_earned = int(total * loyalty_multiplier)

    txn_dict = {
        # 8 hex chars ≈ 4 billion combos/day; 3 chars collided within ~75 sales
        "id": f"TXN-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
        "items": items_list,
        "subtotal": round(subtotal, 2),
        "discount": round(tier_discount, 2),
        "discountAmount": discount_total,
        "appliedDiscounts": applied_discounts,
        "pointsRedeemed": max(int(transaction.pointsRedeemed or 0), 0),
        "pointsDiscount": round(points_discount, 2),
        "surchargeAmount": surcharge_amount,
        "surchargePercent": surcharge_percent,
        "surchargeReason": surcharge_reason,
        "gst": round(gst, 2),
        "total": round(total, 2),
        "paymentMethod": transaction.paymentMethod,
        "customerId": transaction.customerId,
        "location": transaction.location or "Main",
        "cashier": transaction.cashier or user.get("name", "Staff"),
        "timestamp": datetime.utcnow(),
        "status": "completed",
        "receiptNumber": f"R-{str(uuid.uuid4())[:8].upper()}",
    }

    await db.transactions.insert_one(txn_dict)
    txn_dict.pop("_id", None)

    # Consume wallet vouchers used as discounts (no-op for v26 commerce
    # vouchers, which track their own redemption counts).
    try:
        from services.wallet_service import redeem_wallet_voucher
        for d in applied_discounts:
            if d.get("voucherId"):
                await redeem_wallet_voucher(d["voucherId"], txn_dict["id"])
    except Exception:
        pass
    # Audit trail — POS transactions are ledger-grade, always logged
    try:
        from services.audit_service import log_event
        await log_event(entity_type="transaction", entity_id=txn_dict["id"],
                        action="created", after=txn_dict,
                        memo=f"POS sale {txn_dict['paymentMethod']} ${txn_dict['total']}")
    except Exception:
        pass

    # Auto-post to double-entry ledger
    try:
        from services.accounting_service import auto_post_pos_sale
        # coerce timestamp to iso
        auto_txn = {**txn_dict, "timestamp": txn_dict["timestamp"].isoformat() if hasattr(txn_dict["timestamp"], "isoformat") else txn_dict["timestamp"]}
        await auto_post_pos_sale(auto_txn)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"POS ledger auto-post skipped: {e}")

    # Fire rules-engine event: pos.sale.completed
    try:
        from services.rules_engine import safe_emit
        safe_emit("pos.sale.completed", {
            "id": txn_dict["id"], "total": txn_dict["total"],
            "customerId": txn_dict.get("customerId"),
            "items": [i.get("productId") for i in items_list],
            "paymentMethod": txn_dict["paymentMethod"],
        }, entity_id=txn_dict["id"])
    except Exception:
        pass

    # Live-sync: push the sale to any connected Dashboard app instantly.
    # Best-effort only — the Dashboard's own polling is the real source of
    # truth, this just makes the common case feel instant.
    try:
        from services import realtime
        await realtime.broadcast({
            "type": "sale.completed", "id": txn_dict["id"], "total": txn_dict["total"],
            "paymentMethod": txn_dict["paymentMethod"], "location": txn_dict.get("location"),
        })
    except Exception:
        pass

    # Update stock + deduct recipe ingredients via the central helper.
    from routes.inventory_accounting import deduct_recipe_stock
    from services import measured_inventory_service as _mi
    _actor = getattr(transaction, "cashier", None) or "pos"
    for item in transaction.items:
        await db.products.update_one(
            {"id": item.productId},
            {"$inc": {"stock": -item.quantity}}
        )
        try: await deduct_recipe_stock(item.productId, item.quantity)
        except Exception: pass
        # Measured-stock deduction — silent no-op for whole-unit products.
        try: await _mi.deduct_on_sale(item.productId, item.quantity, _actor)
        except Exception: pass
        # Emit inventory events for rules engine
        try:
            p = await db.products.find_one({"id": item.productId}, {"_id": 0})
            if p:
                from services.rules_engine import safe_emit
                stock = p.get("stock", 0)
                threshold = p.get("lowStockThreshold", 5)
                if stock <= 0:
                    safe_emit("inventory.stockout", {"productId": p["id"], "productName": p.get("name"), "stock": stock})
                elif stock <= threshold:
                    safe_emit("inventory.low_stock", {"productId": p["id"], "productName": p.get("name"), "stock": stock, "threshold": threshold})
        except Exception:
            pass

    # Update customer stats
    if transaction.customerId:
        await db.customers.update_one(
            {"id": transaction.customerId},
            {
                "$inc": {
                    "totalSpent": total,
                    "visits": 1,
                    "points": points_earned,
                },
                "$set": {"lastVisit": datetime.utcnow().isoformat()}
            }
        )

    return Transaction(**txn_dict)


# NOTE: static route must be registered before /transactions/{txn_id},
# otherwise "hourly" is captured as a txn_id and always 404s.
@router.get("/transactions/hourly")
async def get_hourly_transactions(_user: dict = Depends(get_user)):
    transactions = await db.transactions.find().to_list(10000)
    hourly = {}
    for txn in transactions:
        ts = txn.get("timestamp")
        if ts:
            hour = ts.hour if hasattr(ts, 'hour') else 0
            hourly[hour] = hourly.get(hour, 0) + txn.get("total", 0)
    return [{"hour": h, "total": round(t, 2)} for h, t in sorted(hourly.items())]


@router.get("/transactions/{txn_id}")
async def get_transaction_detail(txn_id: str, _user: dict = Depends(get_user)):
    txn = await db.transactions.find_one({"id": txn_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Attach any refunds for this transaction
    refunds = await db.refunds.find({"originalTransactionId": txn_id}, {"_id": 0}).to_list(100)
    txn["refunds"] = refunds
    return txn

# ============ GIFT CARDS API ============
@router.get("/gift-cards")
async def get_gift_cards(_user: dict = Depends(get_user)):
    from utils.mongo_safe import safe_parse_list
    cards = await db.gift_cards.find({}, {"_id": 0}).to_list(1000)
    return safe_parse_list(cards, GiftCard, where="gift_cards")

@router.post("/gift-cards", response_model=GiftCard)
async def create_gift_card(card: GiftCardCreate, _user: dict = Depends(get_user)):
    card_dict = card.dict()
    card_dict["code"] = f"GC-{str(uuid.uuid4())[:8].upper()}"
    card_dict["balance"] = card.amount
    card_obj = GiftCard(**card_dict)
    await db.gift_cards.insert_one(card_obj.dict())
    # Auto-post gift card sale to ledger (Bank DR / Gift Card Liability CR)
    try:
        from services.accounting_service import auto_post_gift_card_sale
        _d = card_obj.dict()
        await auto_post_gift_card_sale({
            "id": _d.get("id"),
            "amount": _d.get("initialValue") or _d.get("balance") or 0,
            "issuedAt": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Gift card ledger auto-post skipped: {e}")
    return card_obj

@router.post("/gift-cards/{code}/redeem")
async def redeem_gift_card(code: str, amount: float, _user: dict = Depends(get_user)):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Redemption amount must be positive")
    # Atomic balance check + decrement: two terminals redeeming the same card
    # concurrently must not both succeed off a stale read.
    card = await db.gift_cards.find_one_and_update(
        {"code": code, "balance": {"$gte": amount}},
        {"$inc": {"balance": -amount}},
        return_document=True,
    )
    if not card:
        exists = await db.gift_cards.find_one({"code": code})
        if not exists:
            raise HTTPException(status_code=404, detail="Gift card not found")
        raise HTTPException(status_code=400, detail="Insufficient balance")
    return {"message": "Gift card redeemed", "remaining_balance": card["balance"]}

# ============ REFUNDS API ============
@router.get("/refunds", response_model=List[Refund])
async def get_refunds(_user: dict = Depends(get_user)):
    refunds = await db.refunds.find().to_list(1000)
    return [Refund(**r) for r in refunds]

@router.post("/refunds", response_model=Refund)
async def create_refund(refund: RefundCreate, _user: dict = Depends(require_owner_or_manager)):
    original_txn = await db.transactions.find_one({"id": refund.originalTransactionId})
    if not original_txn:
        raise HTTPException(status_code=404, detail="Original transaction not found")
    if refund.amount <= 0:
        raise HTTPException(status_code=400, detail="Refund amount must be positive")
    # Cap cumulative refunds at the original transaction total
    prior = await db.refunds.find({"originalTransactionId": refund.originalTransactionId}).to_list(1000)
    already_refunded = sum(r.get("amount", 0) for r in prior)
    refundable = round(original_txn.get("total", 0) - already_refunded, 2)
    if refund.amount > refundable:
        raise HTTPException(
            status_code=400,
            detail=f"Refund exceeds remaining refundable amount (${refundable:.2f})"
        )
    refund_obj = Refund(**refund.dict())
    await db.refunds.insert_one(refund_obj.dict())
    # Auto-post refund reversal to ledger
    try:
        from services.accounting_service import auto_post_refund
        await auto_post_refund({**refund_obj.dict(), "timestamp": datetime.utcnow().isoformat()})
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Refund ledger auto-post skipped: {e}")
    # Fire rules-engine event: pos.refund.issued
    try:
        from services.rules_engine import safe_emit
        safe_emit("pos.refund.issued", {
            "id": refund_obj.id if hasattr(refund_obj, "id") else refund_obj.dict().get("id"),
            "amount": refund_obj.amount,
            "reason": refund_obj.reason,
            "customerId": refund_obj.customerId,
        })
    except Exception:
        pass
    if refund.refundMethod == "store_credit" and refund.customerId:
        await db.customers.update_one(
            {"id": refund.customerId},
            {"$inc": {"storeCredit": refund.amount}}
        )
    return refund_obj
