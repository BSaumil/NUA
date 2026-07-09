from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
from database import db
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
async def create_promotion(promotion: PromotionCreate):
    promo_obj = Promotion(**promotion.dict())
    await db.promotions.insert_one(promo_obj.dict())
    return promo_obj

@router.put("/promotions/{promo_id}")
async def update_promotion(promo_id: str, data: dict):
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
async def delete_promotion(promo_id: str):
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
    location: Optional[str] = None
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
async def create_transaction(transaction: TransactionCreate):
    items_list = []
    subtotal = 0
    for item in transaction.items:
        item_dict = item.dict()
        item_total = item.price * item.quantity
        item_dict["total"] = item_total
        subtotal += item_total
        items_list.append(item_dict)

    # Apply customer discount
    discount = 0
    loyalty_multiplier = 1.0
    if transaction.customerId:
        customer = await db.customers.find_one({"id": transaction.customerId})
        if customer:
            tier = customer.get("membershipTier", "Bronze")
            if tier == "Silver":
                discount = subtotal * 0.03
                loyalty_multiplier = 1.25
            elif tier == "Gold":
                discount = subtotal * 0.05
                loyalty_multiplier = 1.5
            elif tier == "Platinum":
                discount = subtotal * 0.10
                loyalty_multiplier = 2.0

    gst = (subtotal - discount) * 0.1
    total = subtotal - discount + gst
    points_earned = int(total * loyalty_multiplier)

    txn_dict = {
        "id": f"TXN-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:3].upper()}",
        "items": items_list,
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "gst": round(gst, 2),
        "total": round(total, 2),
        "paymentMethod": transaction.paymentMethod,
        "customerId": transaction.customerId,
        "location": transaction.location or "Main",
        "cashier": transaction.cashier or "Staff",
        "timestamp": datetime.utcnow(),
        "status": "completed",
        "receiptNumber": f"R-{str(uuid.uuid4())[:8].upper()}",
    }

    await db.transactions.insert_one(txn_dict)
    txn_dict.pop("_id", None)

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

    # Update stock + deduct recipe ingredients via the central helper.
    from routes.inventory_accounting import deduct_recipe_stock
    for item in transaction.items:
        await db.products.update_one(
            {"id": item.productId},
            {"$inc": {"stock": -item.quantity}}
        )
        try: await deduct_recipe_stock(item.productId, item.quantity)
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


@router.get("/transactions/{txn_id}")
async def get_transaction_detail(txn_id: str):
    txn = await db.transactions.find_one({"id": txn_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Attach any refunds for this transaction
    refunds = await db.refunds.find({"originalTransactionId": txn_id}, {"_id": 0}).to_list(100)
    txn["refunds"] = refunds
    return txn


@router.get("/transactions/hourly")
async def get_hourly_transactions():
    transactions = await db.transactions.find().to_list(10000)
    hourly = {}
    for txn in transactions:
        ts = txn.get("timestamp")
        if ts:
            hour = ts.hour if hasattr(ts, 'hour') else 0
            hourly[hour] = hourly.get(hour, 0) + txn.get("total", 0)
    return [{"hour": h, "total": round(t, 2)} for h, t in sorted(hourly.items())]

# ============ GIFT CARDS API ============
@router.get("/gift-cards")
async def get_gift_cards():
    from utils.mongo_safe import safe_parse_list
    cards = await db.gift_cards.find({}, {"_id": 0}).to_list(1000)
    return safe_parse_list(cards, GiftCard, where="gift_cards")

@router.post("/gift-cards", response_model=GiftCard)
async def create_gift_card(card: GiftCardCreate):
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
async def redeem_gift_card(code: str, amount: float):
    card = await db.gift_cards.find_one({"code": code})
    if not card:
        raise HTTPException(status_code=404, detail="Gift card not found")
    if card["balance"] < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    new_balance = card["balance"] - amount
    await db.gift_cards.update_one(
        {"code": code},
        {"$set": {"balance": new_balance}}
    )
    return {"message": "Gift card redeemed", "remaining_balance": new_balance}

# ============ REFUNDS API ============
@router.get("/refunds", response_model=List[Refund])
async def get_refunds():
    refunds = await db.refunds.find().to_list(1000)
    return [Refund(**r) for r in refunds]

@router.post("/refunds", response_model=Refund)
async def create_refund(refund: RefundCreate):
    original_txn = await db.transactions.find_one({"id": refund.originalTransactionId})
    if not original_txn:
        raise HTTPException(status_code=404, detail="Original transaction not found")
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
