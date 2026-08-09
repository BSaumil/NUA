from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from database import db
from deps import get_user, require_owner_or_manager
from models.promotion import Promotion, PromotionCreate
from models.transaction import Transaction, TransactionCreate
from models.refund import Refund, RefundCreate
from middleware.actor_context import tenant_scope_filter, tenant_owns
from utils.errors import log_and_continue
from utils.dates import date_range_filter
import logging
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

# ============ PROMOTIONS API ============
@router.get("/promotions")
async def get_promotions(user: dict = Depends(get_user)):
    from utils.mongo_safe import safe_parse_list
    promotions = await db.promotions.find(tenant_scope_filter(user.get("businessId")), {"_id": 0}).to_list(1000)
    return safe_parse_list(promotions, Promotion, where="promotions")

@router.get("/promotions/active")
async def get_active_promotions(user: dict = Depends(get_user)):
    from utils.mongo_safe import safe_parse_list
    query = {"active": True, **tenant_scope_filter(user.get("businessId"))}
    promotions = await db.promotions.find(query, {"_id": 0}).to_list(1000)
    return safe_parse_list(promotions, Promotion, where="promotions")

@router.post("/promotions", response_model=Promotion)
async def create_promotion(promotion: PromotionCreate, user: dict = Depends(require_owner_or_manager)):
    promo_obj = Promotion(**promotion.dict(), businessId=user.get("businessId"))
    await db.promotions.insert_one(promo_obj.dict())
    return promo_obj

@router.put("/promotions/{promo_id}")
async def update_promotion(promo_id: str, data: dict, user: dict = Depends(require_owner_or_manager)):
    existing = await db.promotions.find_one({"id": promo_id}, {"_id": 0, "businessId": 1})
    if not existing or not tenant_owns(existing.get("businessId"), user.get("businessId")):
        raise HTTPException(status_code=404, detail="Promotion not found")
    allowed = {"name", "type", "discount", "active", "schedule",
               "products", "category", "categories",
               "pricingMode", "bundlePrice",
               "originalPrice", "discountedPrice",
               "minQuantity", "maxQuantity", "stackable",
               "startDate", "endDate", "activeDays", "startTime", "endTime", "channels"}
    update_data = {k: v for k, v in data.items() if k in allowed}
    result = await db.promotions.find_one_and_update({"id": promo_id}, {"$set": update_data}, return_document=True)
    if not result:
        raise HTTPException(status_code=404, detail="Promotion not found")
    result.pop("_id", None)
    return result

@router.delete("/promotions/{promo_id}")
async def delete_promotion(promo_id: str, user: dict = Depends(require_owner_or_manager)):
    existing = await db.promotions.find_one({"id": promo_id}, {"_id": 0, "businessId": 1})
    if not existing or not tenant_owns(existing.get("businessId"), user.get("businessId")):
        raise HTTPException(status_code=404, detail="Promotion not found")
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
    query = tenant_scope_filter(_user.get("businessId"))
    if payment_method:
        query["paymentMethod"] = payment_method
    if location:
        query["location"] = location
    if start_date and end_date:
        query.update(date_range_filter("timestamp", start_date, end_date))
    transactions = await db.transactions.find(query, {"_id": 0}).sort("timestamp", -1).to_list(1000)
    from utils.mongo_safe import safe_parse_list
    return safe_parse_list(transactions, Transaction, where="transactions")

@router.post("/transactions", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate, user: dict = Depends(get_user)):
    items_list = []
    earn_lines = []  # [(category, lineTotal)] — for category-multiplier points earning below
    subtotal = 0
    for item in transaction.items:
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Invalid quantity for {item.productName}")
        item_dict = item.dict()
        # Server-authoritative pricing: unit price comes from the catalog, not
        # the request body. Modifier surcharges are added on top (clamped to
        # non-negative). Unknown productIds (open/custom lines) keep the client
        # price, floored at zero.
        product = await db.products.find_one({"id": item.productId}, {"_id": 0, "price": 1, "category": 1})
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
        earn_lines.append(((product or {}).get("category") or "Other", item_total))

    # Apply customer membership-tier discount — reads the owner-editable
    # loyalty_tiers ladder (Settings > Loyalty > Tiers) instead of a fixed
    # Silver/Gold/Platinum percentage baked into this function, so a tier's
    # discount%/points-multiplier can actually be changed without a deploy.
    tier_discount = 0
    loyalty_multiplier = 1.0
    if transaction.customerId:
        customer = await db.customers.find_one({"id": transaction.customerId})
        if customer:
            tier_name = customer.get("membershipTier", "Bronze")
            tier_doc = await db.loyalty_tiers.find_one({"name": tier_name}, {"_id": 0})
            if tier_doc:
                tier_discount = subtotal * (float(tier_doc.get("discountPercent", 0)) / 100)
                loyalty_multiplier = float(tier_doc.get("multiplier", 1.0))

    # Voucher/promotion discounts applied at the POS + loyalty-point redemption.
    # Amounts are clamped non-negative and the combined discount can never
    # exceed the subtotal.
    applied_discounts = [d.dict() for d in transaction.appliedDiscounts]
    for d in applied_discounts:
        d["amount"] = max(float(d.get("amount") or 0), 0)
    # Voucher-linked discounts also get capped to what the voucher is
    # actually worth — the client-supplied amount is a display hint only.
    # Without this, any logged-in POS user could attach a real voucherId to
    # an inflated amount and the bill would honour it at face value; the
    # voucher only ever got checked for value once it was (separately)
    # marked consumed after the sale had already been priced and saved.
    for d in applied_discounts:
        if not d.get("voucherId"):
            continue
        v = await db.vouchers.find_one({"id": d["voucherId"]}, {"_id": 0})
        if not v or v.get("status") not in ("active", "partial"):
            d["amount"] = 0.0
        elif v.get("valueType") != "percentage":
            cap = float(v.get("residualValue")) if v.get("partialRedeemable") else float(v.get("value", 0) or 0)
            d["amount"] = min(d["amount"], max(cap, 0.0))
    voucher_discount = sum(d["amount"] for d in applied_discounts)

    # Loyalty config — used for both the redeem check below and the earn
    # calculation further down, so it's fetched once regardless of which (or
    # both) apply to this sale.
    loyalty_cfg = await db.loyalty_config.find_one({"id": "default"}, {"_id": 0}) or {}

    # Points redemption: the client-supplied pointsDiscount is a display hint
    # only — the value actually deducted from the bill (and the points balance)
    # is always computed server-side from pointsRedeemed × the configured
    # redeemRate, exactly the same way the old separate /loyalty/redeem call
    # used to. The balance is checked and decremented atomically right here,
    # in this same request, instead of a follow-up call the frontend used to
    # make best-effort after the fact — that gap could double-spend or lose
    # points if the second call ever failed.
    min_redeem = int(loyalty_cfg.get("minRedeem", 10))
    redeem_rate = float(loyalty_cfg.get("redeemRate", 0.01))

    async def _redeem(customer_id: str, points: int) -> float:
        """Atomically check-and-decrement one customer's points balance.
        Raises 400 on insufficient balance/below minimum. Returns the $
        value to apply as a discount."""
        if points < min_redeem:
            raise HTTPException(status_code=400, detail=f"Minimum {min_redeem} points required to redeem")
        redeemed_doc = await db.customers.find_one_and_update(
            {"id": customer_id, "points": {"$gte": points}, "loyaltyLocked": {"$ne": True}},
            {"$inc": {"points": -points}},
        )
        if not redeemed_doc:
            locked = await db.customers.find_one({"id": customer_id, "loyaltyLocked": True}, {"_id": 0, "id": 1})
            if locked:
                raise HTTPException(status_code=403, detail="Loyalty account locked pending fraud review")
        if not redeemed_doc:
            balance = int((await db.customers.find_one({"id": customer_id}, {"_id": 0, "points": 1}) or {}).get("points", 0))
            raise HTTPException(status_code=400, detail=f"Insufficient points: {balance} available, {points} requested")
        return round(points * redeem_rate, 2)

    points_redeemed = max(int(transaction.pointsRedeemed or 0), 0)
    points_discount = 0.0
    if points_redeemed > 0:
        if not transaction.customerId:
            raise HTTPException(status_code=400, detail="pointsRedeemed requires a customerId")
        points_discount = await _redeem(transaction.customerId, points_redeemed)

    # Split payments: each guest can redeem against their OWN loyalty balance
    # instead of only the one customerId attached to the whole sale — a split
    # used to have no concept of "guest 2's" points at all. Their discount
    # rolls into the same bill-level discount_total below; per-guest points
    # earning happens later, once the transaction total (and each guest's
    # correct share of it) is known.
    for part in transaction.splitDetails:
        if part.customerId and part.pointsRedeemed > 0:
            points_discount += await _redeem(part.customerId, part.pointsRedeemed)

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

    # Auto-gratuity (configured in Settings > Gratuity) — a genuine service
    # charge, calculated on either the pre-discount subtotal or the
    # discounted net depending on the owner's setting, never on the
    # unrelated weekend/holiday surcharge.
    gratuity_percent = 0.0
    gratuity_label = None
    try:
        from routes.enterprise_features import check_gratuity
        gratuity_info = await check_gratuity(covers=transaction.covers)
        gratuity_percent = float(gratuity_info.get("gratuityPercent") or 0)
        gratuity_label = gratuity_info.get("label")
        gratuity_base = subtotal if gratuity_info.get("calculateOn") == "pre_discount" else net_before_surcharge
    except Exception:
        gratuity_base = net_before_surcharge
    gratuity_amount = round(gratuity_base * gratuity_percent / 100, 2)

    total = net_before_surcharge + surcharge_amount + gratuity_amount
    # GST component contained within the final (GST-inclusive) total, at the
    # standard AU 10%-inclusive rate: gst = total / 11.
    gst = total / 11
    # Points earned = post-discount total × membership-tier multiplier ×
    # earnRate × a blended category multiplier (each line's category weighted
    # by its share of the subtotal). This used to be split across two places:
    # this endpoint applied only the tier multiplier directly, while a
    # separate best-effort frontend call applied earnRate/category
    # multipliers on top and credited a *different* balance field
    # (customers.loyaltyPoints vs. customers.points) — so a sale could earn
    # into a balance no redemption or receipt ever read from. Folding it all
    # into one calculation, on one field, here.
    earn_rate = float(loyalty_cfg.get("earnRate", 1.0))
    category_mults = loyalty_cfg.get("categoryMultipliers", {}) if loyalty_cfg.get("active", True) else {}
    if loyalty_cfg.get("active", True) and subtotal > 0 and category_mults:
        category_mult = sum(line_total * float(category_mults.get(cat, 1.0)) for cat, line_total in earn_lines) / subtotal
    else:
        category_mult = 1.0
    points_earned = int(total * loyalty_multiplier * earn_rate * category_mult) if loyalty_cfg.get("active", True) else 0

    txn_dict = {
        # 8 hex chars ≈ 4 billion combos/day; 3 chars collided within ~75 sales
        "id": f"TXN-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
        "items": items_list,
        "subtotal": round(subtotal, 2),
        "discount": round(tier_discount, 2),
        "discountAmount": discount_total,
        "appliedDiscounts": applied_discounts,
        "pointsRedeemed": points_redeemed,
        "pointsDiscount": points_discount,
        "splitDetails": [d.dict() for d in transaction.splitDetails],
        "surchargeAmount": surcharge_amount,
        "surchargePercent": surcharge_percent,
        "surchargeReason": surcharge_reason,
        "gratuityAmount": gratuity_amount,
        "gratuityPercent": gratuity_percent,
        "gratuityLabel": gratuity_label,
        "covers": transaction.covers,
        "gst": round(gst, 2),
        "total": round(total, 2),
        "paymentMethod": transaction.paymentMethod,
        "customerId": transaction.customerId,
        "location": transaction.location or "Main",
        "cashier": transaction.cashier or user.get("name", "Staff"),
        "timestamp": datetime.utcnow(),
        "status": "completed",
        "receiptNumber": f"R-{str(uuid.uuid4())[:8].upper()}",
        "businessId": user.get("businessId"),
    }

    await db.transactions.insert_one(txn_dict)
    txn_dict.pop("_id", None)

    # Record the redemption on the loyalty ledger for history/reporting — the
    # balance itself was already decremented atomically above, before the
    # transaction was inserted, so this is audit trail only.
    if points_redeemed > 0:
        try:
            await db.loyalty_ledger.insert_one({
                "id": f"LP-{str(uuid.uuid4())[:8].upper()}",
                "customerId": transaction.customerId,
                "transactionId": txn_dict["id"],
                "type": "redeem",
                "points": -points_redeemed,
                "value": points_discount,
                "createdAt": datetime.utcnow().isoformat(),
            })
        except Exception:
            pass

    # Consume wallet vouchers used as discounts (no-op for v26 commerce
    # vouchers, which track their own redemption counts).
    try:
        from services.wallet_service import redeem_wallet_voucher
        for d in applied_discounts:
            if d.get("voucherId"):
                await redeem_wallet_voucher(d["voucherId"], txn_dict["id"], d["amount"])
    except Exception:
        pass
    # Audit trail — POS transactions are ledger-grade, always logged. If
    # this write itself silently failed, "always logged" wasn't true and
    # nothing said so.
    try:
        from services.audit_service import log_event
        await log_event(entity_type="transaction", entity_id=txn_dict["id"],
                        action="created", after=txn_dict,
                        memo=f"POS sale {txn_dict['paymentMethod']} ${txn_dict['total']}")
    except Exception as e:
        log_and_continue(logger, f"POS sale audit log write failed for txn {txn_dict['id']}", e)

    # Auto-post to double-entry ledger
    try:
        from services.accounting_service import auto_post_pos_sale
        # coerce timestamp to iso
        auto_txn = {**txn_dict, "timestamp": txn_dict["timestamp"].isoformat() if hasattr(txn_dict["timestamp"], "isoformat") else txn_dict["timestamp"]}
        await auto_post_pos_sale(auto_txn)
    except Exception as e:
        log_and_continue(logger, "POS ledger auto-post skipped", e)

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

    # Base stock decrement is independent per item, so it's one bulk
    # round trip instead of N sequential ones — recipe/measured-stock
    # deduction and event emission below stay per-item since they carry
    # real per-item side effects (container tracking, rules-engine emits)
    # that don't reduce to a single batched write.
    if transaction.items:
        from pymongo import UpdateOne
        await db.products.bulk_write([
            UpdateOne({"id": item.productId}, {"$inc": {"stock": -item.quantity}})
            for item in transaction.items
        ])

    for item in transaction.items:
        try:
            await deduct_recipe_stock(item.productId, item.quantity)
        except Exception as e:
            log_and_continue(logger, f"Recipe stock deduction failed for {item.productId}", e)
        # Measured-stock deduction — silent no-op for whole-unit products.
        try:
            await _mi.deduct_on_sale(item.productId, item.quantity, _actor)
        except Exception as e:
            log_and_continue(logger, f"Measured-stock deduction failed for {item.productId}", e)
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
                # Two fields for the same fact, kept in lockstep on purpose:
                # lastVisit (bare ISO string) is what nua_intelligence.py,
                # nua_tools.py and v25_suite.py already read; lastVisitDate is
                # the Customer model's declared field (models/customer.py) and
                # what loyalty_engine's segmentation and the marketing segment
                # builder's "inactive for N days" rule read. Only writing one
                # of the two silently starved the other's readers of any real
                # data — every customer looked permanently brand-new to them.
                "$set": {"lastVisit": datetime.utcnow().isoformat(),
                         "lastVisitDate": datetime.utcnow().date().isoformat()}
            }
        )
        if points_earned > 0:
            try:
                await db.loyalty_ledger.insert_one({
                    "id": f"LP-{str(uuid.uuid4())[:8].upper()}",
                    "customerId": transaction.customerId,
                    "transactionId": txn_dict["id"],
                    "type": "earn",
                    "points": points_earned,
                    "createdAt": datetime.utcnow().isoformat(),
                })
            except Exception:
                pass
        # Free base identity layer — a repeat contact match at POS checkout is
        # an identity touchpoint (skipped automatically for base-only venues).
        try:
            from services.customer_identity import record_touchpoint
            crm = await db.customers.find_one({"id": transaction.customerId}, {"_id": 0, "phone": 1, "email": 1, "name": 1})
            if crm:
                await record_touchpoint(
                    phone=crm.get("phone"), email=crm.get("email"),
                    name=crm.get("name"), source="pos_checkout",
                )
        except Exception:
            pass

    # Split payments: each guest with their own customerId earns points on
    # their own share of the bill (part.amount), at their own tier's
    # multiplier — previously only transaction.customerId (the one "selected
    # customer" for the whole sale) ever earned anything, so guests 2/3/4 on
    # a split got no loyalty credit for their own payment at all. Skips
    # transaction.customerId if it's also listed as a split guest, so that
    # person doesn't get credited twice for the same money.
    if loyalty_cfg.get("active", True):
        earn_rate = float(loyalty_cfg.get("earnRate", 1.0))
        for part in transaction.splitDetails:
            if not part.customerId or part.customerId == transaction.customerId:
                continue
            guest = await db.customers.find_one({"id": part.customerId}, {"_id": 0, "membershipTier": 1})
            if not guest:
                continue
            tier_doc = await db.loyalty_tiers.find_one({"name": guest.get("membershipTier", "Bronze")}, {"_id": 0})
            mult = float(tier_doc.get("multiplier", 1.0)) if tier_doc else 1.0
            part_points = int(round(float(part.amount) * earn_rate * mult))
            await db.customers.update_one(
                {"id": part.customerId},
                {"$inc": {"totalSpent": part.amount, "visits": 1, "points": part_points},
                 "$set": {"lastVisit": datetime.utcnow().isoformat(),
                          "lastVisitDate": datetime.utcnow().date().isoformat()}},
            )
            if part_points > 0:
                try:
                    await db.loyalty_ledger.insert_one({
                        "id": f"LP-{str(uuid.uuid4())[:8].upper()}",
                        "customerId": part.customerId, "transactionId": txn_dict["id"],
                        "type": "earn", "points": part_points,
                        "createdAt": datetime.utcnow().isoformat(),
                    })
                except Exception:
                    pass

    return Transaction(**txn_dict)


# NOTE: static route must be registered before /transactions/{txn_id},
# otherwise "hourly" is captured as a txn_id and always 404s.
@router.get("/transactions/hourly")
async def get_hourly_transactions(_user: dict = Depends(get_user)):
    transactions = await db.transactions.find(tenant_scope_filter(_user.get("businessId"))).to_list(10000)
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
    if not txn or not tenant_owns(txn.get("businessId"), _user.get("businessId")):
        raise HTTPException(status_code=404, detail="Transaction not found")
    # Attach any refunds for this transaction
    refunds = await db.refunds.find({"originalTransactionId": txn_id}, {"_id": 0}).to_list(100)
    txn["refunds"] = refunds
    return txn

# Gift cards live entirely under /v26/gift-cards (routes/v26_commerce.py) —
# that's the schema the POS register and the owner's gift-card management
# page actually read/write. This file used to shadow it with a second,
# unreachable, incompatible schema (field `balance` instead of
# `currentBalance`) — removed rather than fixed, since nothing called it.

async def _reverse_loyalty_for_refund(original_txn: dict, refund_amount: float) -> list:
    """Refunding a sale used to leave loyalty completely untouched: a
    customer who redeemed 500 points for a discount kept the refunded money
    AND lost the points permanently (never restored), while a customer who
    earned points on that sale kept them even though the money came back.

    Reverses both, proportional to how much of the sale was actually
    refunded (a partial refund only reverses that fraction) — using the
    loyalty_ledger entries already written for this transactionId at
    checkout, not the top-level pointsRedeemed field, so this correctly
    covers per-guest split-payment redemptions too, not just the one
    customerId attached to the whole sale.
    """
    total = float(original_txn.get("total") or 0)
    fraction = min(1.0, refund_amount / total) if total > 0 else 1.0
    entries = await db.loyalty_ledger.find(
        {"transactionId": original_txn["id"], "type": {"$in": ["earn", "redeem"]}},
        {"_id": 0, "customerId": 1, "type": 1, "points": 1},
    ).to_list(200)
    by_customer: dict = {}
    for e in entries:
        cid = e.get("customerId")
        if not cid:
            continue
        by_customer.setdefault(cid, {"earned": 0, "redeemed": 0})
        if e["type"] == "earn":
            by_customer[cid]["earned"] += int(e.get("points", 0))
        else:  # redeem entries are stored as negative points
            by_customer[cid]["redeemed"] += abs(int(e.get("points", 0)))

    reversed_for = []
    for customer_id, totals in by_customer.items():
        earn_clawback = round(totals["earned"] * fraction)
        redeem_restore = round(totals["redeemed"] * fraction)
        if earn_clawback <= 0 and redeem_restore <= 0:
            continue
        # Clawback capped at whatever the customer still has — never drive
        # a balance negative because they already spent points earned here
        # on something else entirely.
        current = await db.customers.find_one({"id": customer_id}, {"_id": 0, "points": 1})
        available = int((current or {}).get("points", 0))
        actual_clawback = min(earn_clawback, available)
        net = redeem_restore - actual_clawback
        if net == 0:
            continue
        await db.customers.update_one({"id": customer_id}, {"$inc": {"points": net}})
        await db.loyalty_ledger.insert_one({
            "id": f"LP-{str(uuid.uuid4())[:8].upper()}",
            "customerId": customer_id, "transactionId": original_txn["id"],
            "type": "refund_reversal", "points": net,
            "earnClawedBack": actual_clawback, "redeemRestored": redeem_restore,
            "createdAt": datetime.utcnow().isoformat(),
        })
        reversed_for.append({"customerId": customer_id, "earnClawedBack": actual_clawback, "redeemRestored": redeem_restore})
    return reversed_for


# ============ REFUNDS API ============
@router.get("/refunds", response_model=List[Refund])
async def get_refunds(_user: dict = Depends(get_user)):
    refunds = await db.refunds.find(tenant_scope_filter(_user.get("businessId"))).to_list(1000)
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
    refund_obj = Refund(**refund.dict(), businessId=original_txn.get("businessId"))
    await db.refunds.insert_one(refund_obj.dict())
    # Auto-post refund reversal to ledger
    try:
        from services.accounting_service import auto_post_refund
        await auto_post_refund({**refund_obj.dict(), "timestamp": datetime.utcnow().isoformat()})
    except Exception as e:
        log_and_continue(logger, "Refund ledger auto-post skipped", e)
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

    # The money path and the food path were tracked separately: refunding a
    # sale left its kitchen ticket open and its stock consumed, so the kitchen
    # kept cooking a dish nobody was paying for and inventory stayed wrong.
    try:
        from services import refund_effects
        refund_obj_dict = refund_obj.dict()
        refund_obj_dict["kitchenEffects"] = await refund_effects.reverse(
            original_txn, refund_obj_dict, actor=_user.get("name") or _user.get("email"))
        await db.refunds.update_one(
            {"id": refund_obj_dict["id"]},
            {"$set": {"kitchenEffects": refund_obj_dict["kitchenEffects"]}})
    except Exception as e:
        log_and_continue(logger, "Refund kitchen/stock reversal skipped", e)

    try:
        await _reverse_loyalty_for_refund(original_txn, refund.amount)
    except Exception as e:
        log_and_continue(logger, "Refund loyalty reversal skipped", e)

    return refund_obj
