"""v17 — Loyalty Engine (category multipliers + points-and-pay) + Autonomous AI Agent (Ash).

Loyalty rules (user spec):
- 1 USD spent = 1 point (base)
- Categories can have a multiplier configured by owner (e.g. Coffee 2x)
- Minimum redemption = 10 points (= $0.10)
- 1 point = 1¢ = $0.01 face value at redemption
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from deps import get_user, require_owner, require_owner_or_manager
from database import db
from datetime import datetime, timezone, timedelta
import uuid
import os
import json

router = APIRouter()


# =============================================================================
# LOYALTY CONFIG (category multipliers)
# =============================================================================
DEFAULT_CONFIG = {
    "earnRate": 1.0,         # 1 point per $1 base
    "redeemRate": 0.01,      # 1 point = $0.01 (so 10 points = 10c)
    "minRedeem": 10,         # minimum 10 points (= $0.10) to redeem
    "categoryMultipliers": {},  # { "Coffee": 2.0, "Pastry": 1.5 }
    "active": True,
    "pointsExpiryDays": 0,      # 0 = never expire. Otherwise: zero a customer's
                                 # balance once this many days pass with no earn
                                 # or redeem activity at all (inactivity-based,
                                 # not FIFO-per-earn — simpler and matches how
                                 # most POS loyalty programs actually expire).
    "expiryWarnDays": 7,        # send a one-time "your points expire soon" notice
                                 # this many days before pointsExpiryDays actually
                                 # zeroes the balance. Only matters when
                                 # pointsExpiryDays > 0.
    "downgradeEnabled": False,  # tiers only ever went up before; this lets them
                                 # come back down when a customer's balance
                                 # genuinely drops below their tier's threshold.
    "downgradeGraceDays": 30,   # days a customer can sit below-threshold before
                                 # actually being downgraded — a slow month
                                 # shouldn't cost someone their tier overnight.
}


async def get_config():
    cfg = await db.loyalty_config.find_one({"id": "default"}, {"_id": 0})
    return cfg or {"id": "default", **DEFAULT_CONFIG}


@router.get("/loyalty/config")
async def get_loyalty_config(_: dict = Depends(get_user)):
    return await get_config()


@router.put("/loyalty/config")
async def update_loyalty_config(data: dict, _: dict = Depends(require_owner)):
    update = {k: v for k, v in data.items() if k in (
        "earnRate", "redeemRate", "minRedeem", "categoryMultipliers", "active",
        "pointsExpiryDays", "expiryWarnDays", "downgradeEnabled", "downgradeGraceDays",
    )}
    update["updatedAt"] = datetime.now(timezone.utc).isoformat()
    await db.loyalty_config.update_one({"id": "default"}, {"$set": {"id": "default", **update}}, upsert=True)
    return await get_config()


# =============================================================================
# EARN POINTS (called after a successful transaction)
# =============================================================================
@router.post("/loyalty/earn")
async def earn_points(data: dict, _: dict = Depends(get_user)):
    customer_id = data.get("customerId")
    items = data.get("items", [])  # [{ category, price, quantity }]
    transaction_id = data.get("transactionId")
    if not customer_id or not items:
        raise HTTPException(status_code=400, detail="customerId + items required")
    # Idempotency: skip if we already credited this transaction
    if transaction_id:
        existing = await db.loyalty_ledger.find_one({"transactionId": transaction_id, "type": "earn"})
        if existing:
            return {"earned": existing["points"], "skipped": True, "reason": "already credited"}
    cfg = await get_config()
    if not cfg.get("active", True):
        return {"earned": 0, "skipped": True, "reason": "loyalty disabled"}
    mults = cfg.get("categoryMultipliers", {})
    earned = 0.0
    breakdown = []
    for it in items:
        cat = it.get("category", "Other")
        qty = float(it.get("quantity", 1))
        price = float(it.get("price", 0))
        spend = qty * price
        mult = float(mults.get(cat, 1.0))
        pts = spend * float(cfg.get("earnRate", 1.0)) * mult
        earned += pts
        breakdown.append({"category": cat, "spend": round(spend, 2), "multiplier": mult, "points": round(pts, 2)})
    earned_int = int(round(earned))
    # Credit ledger
    entry = {
        "id": f"LP-{str(uuid.uuid4())[:8].upper()}",
        "customerId": customer_id,
        "transactionId": transaction_id,
        "type": "earn",
        "points": earned_int,
        "breakdown": breakdown,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.loyalty_ledger.insert_one(entry)
    # Bump customer balance — "points" is the canonical balance field (also
    # what the Customer model declares and what POS checkout earns/redeems
    # against); this used to write "loyaltyPoints" instead, a field checkout
    # never read, so points earned through this endpoint were invisible at
    # the register.
    await db.customers.update_one({"id": customer_id}, {"$inc": {"points": earned_int}})
    return {"earned": earned_int, "breakdown": breakdown}


# =============================================================================
# REDEEM (points-and-pay at checkout)
# =============================================================================
@router.post("/loyalty/redeem")
async def redeem_points(data: dict, _: dict = Depends(get_user)):
    customer_id = data.get("customerId")
    points = int(data.get("points", 0))
    transaction_id = data.get("transactionId")
    if not customer_id or points <= 0:
        raise HTTPException(status_code=400, detail="customerId + points (>0) required")
    locked_check = await db.customers.find_one({"id": customer_id}, {"_id": 0, "loyaltyLocked": 1})
    if locked_check and locked_check.get("loyaltyLocked"):
        raise HTTPException(status_code=403, detail="Loyalty account locked pending fraud review")
    cfg = await get_config()
    min_redeem = int(cfg.get("minRedeem", 10))
    if points < min_redeem:
        raise HTTPException(status_code=400, detail=f"Minimum {min_redeem} points required")
    # Atomic balance-checked decrement — same pattern as the checkout redeem
    # path, so a double-tap or concurrent call can't take a customer negative.
    updated = await db.customers.find_one_and_update(
        {"id": customer_id, "points": {"$gte": points}},
        {"$inc": {"points": -points}},
    )
    if not updated:
        current = await db.customers.find_one({"id": customer_id}, {"_id": 0, "points": 1})
        if not current:
            raise HTTPException(status_code=404, detail="Customer not found")
        raise HTTPException(status_code=400, detail=f"Insufficient points: {int(current.get('points', 0))} available")
    balance = int(updated.get("points", 0))
    value = round(points * float(cfg.get("redeemRate", 0.01)), 2)
    entry = {
        "id": f"LP-{str(uuid.uuid4())[:8].upper()}",
        "customerId": customer_id,
        "transactionId": transaction_id,
        "type": "redeem",
        "points": -points,
        "value": value,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.loyalty_ledger.insert_one(entry)
    return {"redeemed": points, "discountValue": value, "newBalance": balance - points}


@router.get("/loyalty/balance/{customer_id}")
async def get_balance(customer_id: str, _: dict = Depends(get_user)):
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    pts = int(customer.get("points", 0))
    cfg = await get_config()
    return {
        "customerId": customer_id,
        "points": pts,
        "value": round(pts * float(cfg.get("redeemRate", 0.01)), 2),
        "minRedeem": int(cfg.get("minRedeem", 10)),
        "canRedeem": pts >= int(cfg.get("minRedeem", 10)),
    }


@router.get("/loyalty/ledger/{customer_id}")
async def get_ledger(customer_id: str, _: dict = Depends(get_user)):
    entries = await db.loyalty_ledger.find({"customerId": customer_id}, {"_id": 0}).sort("createdAt", -1).to_list(100)
    return entries


# =============================================================================
# REPORTS — outstanding liability + fraud signals
# =============================================================================
@router.get("/loyalty/reports/liability")
async def get_liability_report(_: dict = Depends(require_owner_or_manager)):
    """Points sitting on customer balances are a real liability — the
    business owes that $ value in future discounts the moment it's earned,
    same accounting posture as gratuity being tracked as a liability rather
    than revenue. Nothing already computed this anywhere; it only ever
    existed implicitly as a sum nobody had run."""
    cfg = await get_config()
    redeem_rate = float(cfg.get("redeemRate", 0.01))
    customers = await db.customers.find({"points": {"$gt": 0}}, {"_id": 0, "id": 1, "name": 1, "points": 1}).to_list(20000)
    total_points = sum(int(c.get("points", 0)) for c in customers)
    top_holders = sorted(customers, key=lambda c: c.get("points", 0), reverse=True)[:20]
    return {
        "totalPointsOutstanding": total_points,
        "totalLiabilityValue": round(total_points * redeem_rate, 2),
        "customersWithBalance": len(customers),
        "redeemRate": redeem_rate,
        "topHolders": [{"customerId": c["id"], "name": c.get("name"), "points": c.get("points", 0),
                         "value": round(c.get("points", 0) * redeem_rate, 2)} for c in top_holders],
    }


async def _compute_fraud_signals() -> list:
    """Two concrete, computable signals from data that already exists —
    not a general fraud model, just the two patterns explicitly called out
    in the loyalty engine spec's fraud-prevention section that had nothing
    behind them yet:

    - point_farming: a customer with an unusually high rate of separate
      earn events in a short window (repeated minimum-value transactions
      purely to rack up points).
    - voucher_sharing: the same voucher code redeemed from more than one
      terminal within a short window (the code changed hands rather than
      staying with whoever it was issued to).
    """
    window_start = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    signals = []
    pipeline = [
        {"$match": {"type": "earn", "createdAt": {"$gte": window_start}}},
        {"$group": {"_id": "$customerId", "count": {"$sum": 1}, "totalPoints": {"$sum": "$points"}}},
        {"$match": {"count": {"$gte": 5}}},
    ]
    async for row in db.loyalty_ledger.aggregate(pipeline):
        if not row["_id"]:
            continue
        customer = await db.customers.find_one({"id": row["_id"]}, {"_id": 0, "name": 1})
        signals.append({
            "type": "point_farming",
            "customerId": row["_id"],
            "customerName": (customer or {}).get("name"),
            "earnEventsLast24h": row["count"],
            "totalPointsEarned": row["totalPoints"],
            "reason": f"{row['count']} separate earn events in the last 24h",
        })

    recent_vouchers = await db.vouchers.find(
        {"redemptions.1": {"$exists": True}}, {"_id": 0, "id": 1, "code": 1, "redemptions": 1}
    ).to_list(2000)
    for v in recent_vouchers:
        redemptions = sorted(v.get("redemptions") or [], key=lambda r: r.get("at", ""))
        for i in range(len(redemptions) - 1):
            a, b = redemptions[i], redemptions[i + 1]
            if not a.get("terminalId") or not b.get("terminalId") or a["terminalId"] == b["terminalId"]:
                continue
            try:
                t_a = datetime.fromisoformat(a["at"].replace("Z", "+00:00"))
                t_b = datetime.fromisoformat(b["at"].replace("Z", "+00:00"))
            except Exception:
                continue
            if abs((t_b - t_a).total_seconds()) <= 600:  # 10 minutes
                signals.append({
                    "type": "voucher_sharing",
                    "voucherId": v["id"], "code": v.get("code"),
                    "terminals": [a["terminalId"], b["terminalId"]],
                    "reason": "Same code redeemed from two different terminals within 10 minutes",
                })
                break  # one flag per voucher is enough signal

    return signals


def _flag_dedup_key(signal: dict) -> dict:
    """One open flag per underlying issue — re-computing signals on every
    report view (or agent tick) shouldn't spam a fresh flag each time."""
    if signal["type"] == "point_farming":
        return {"type": "point_farming", "customerId": signal["customerId"]}
    return {"type": "voucher_sharing", "voucherId": signal["voucherId"]}


async def _persist_fraud_flags(signals: list) -> int:
    created = 0
    for signal in signals:
        key = _flag_dedup_key(signal)
        existing = await db.loyalty_fraud_flags.find_one({**key, "status": "open"}, {"_id": 0, "id": 1})
        if existing:
            continue
        await db.loyalty_fraud_flags.insert_one({
            "id": f"FLAG-{str(uuid.uuid4())[:8].upper()}",
            **signal,
            "status": "open",
            "reviewedBy": None, "reviewedAt": None, "reviewReason": None,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })
        created += 1
    return created


@router.get("/loyalty/reports/fraud-flags")
async def get_fraud_flags(status: str = "open", _: dict = Depends(require_owner_or_manager)):
    signals = await _compute_fraud_signals()
    await _persist_fraud_flags(signals)
    query = {} if status == "all" else {"status": status}
    flags = await db.loyalty_fraud_flags.find(query, {"_id": 0}).sort("createdAt", -1).to_list(500)
    return {"flags": flags, "checkedAt": datetime.now(timezone.utc).isoformat()}


@router.put("/loyalty/reports/fraud-flags/{flag_id}")
async def resolve_fraud_flag(flag_id: str, data: dict, user: dict = Depends(require_owner_or_manager)):
    """Close the loop on a flag: mark it reviewed, or confirm abuse and take
    the matching action — lock the customer's loyalty account (point
    farming) or revoke the voucher (sharing). Previously a flag was just
    information with nothing to do about it."""
    new_status = data.get("status")
    if new_status not in ("reviewed_ok", "confirmed_abuse"):
        raise HTTPException(status_code=400, detail="status must be reviewed_ok or confirmed_abuse")
    flag = await db.loyalty_fraud_flags.find_one({"id": flag_id}, {"_id": 0})
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    if flag["status"] != "open":
        raise HTTPException(status_code=400, detail=f"Flag already {flag['status']}")

    action_taken = None
    if new_status == "confirmed_abuse":
        if flag["type"] == "point_farming" and flag.get("customerId"):
            await db.customers.update_one({"id": flag["customerId"]}, {"$set": {"loyaltyLocked": True}})
            action_taken = "Loyalty account locked — redemption blocked until unlocked"
        elif flag["type"] == "voucher_sharing" and flag.get("voucherId"):
            await db.vouchers.update_one({"id": flag["voucherId"]}, {"$set": {
                "status": "revoked",
                "revokedAt": datetime.now(timezone.utc).isoformat(),
                "revokedBy": user.get("email"),
                "revokeReason": "Confirmed voucher sharing (fraud flag)",
            }})
            action_taken = "Voucher revoked"

    await db.loyalty_fraud_flags.update_one({"id": flag_id}, {"$set": {
        "status": new_status,
        "reviewedBy": user.get("email"), "reviewedAt": datetime.now(timezone.utc).isoformat(),
        "reviewReason": data.get("reason"),
        "actionTaken": action_taken,
    }})
    try:
        from services.audit_service import log_event
        await log_event(entity_type="loyalty_fraud_flag", entity_id=flag_id, action=new_status,
                         memo=f"{flag['type']} flag resolved: {new_status}" + (f" — {action_taken}" if action_taken else ""))
    except Exception:
        pass
    return {"ok": True, "status": new_status, "actionTaken": action_taken}


@router.post("/loyalty/customers/{customer_id}/unlock")
async def unlock_loyalty_account(customer_id: str, user: dict = Depends(require_owner)):
    """Reverse a loyaltyLocked from a confirmed_abuse flag — owner only,
    since re-enabling redemption after a fraud confirmation is a judgment
    call worth restricting more tightly than reviewing the flag itself."""
    result = await db.customers.update_one({"id": customer_id}, {"$set": {"loyaltyLocked": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"ok": True}


# =============================================================================
# AUTONOMOUS AI AGENT (Ash) — observes, decides, acts
# =============================================================================
async def _segment_customers():
    """Auto-segment customers: VIP / regular / at-risk / first-timer."""
    customers = await db.customers.find({}, {"_id": 0}).to_list(5000)
    now = datetime.now(timezone.utc)
    sixty_days_ago = (now - timedelta(days=60)).isoformat()
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    segments = {"vip": [], "regular": [], "at_risk": [], "first_timer": []}
    for c in customers:
        visits = int(c.get("totalVisits", 0) or 0)
        spend = float(c.get("totalSpend", 0) or 0)
        last_visit = c.get("lastVisit", "")
        if spend > 500 and visits > 10:
            segments["vip"].append(c["id"])
        elif visits <= 1:
            segments["first_timer"].append(c["id"])
        elif last_visit and last_visit < sixty_days_ago:
            segments["at_risk"].append(c["id"])
        else:
            segments["regular"].append(c["id"])
    return segments


async def _record_decision(action_type: str, summary: str, payload: dict, status: str = "executed"):
    rec = {
        "id": f"AGT-{str(uuid.uuid4())[:8].upper()}",
        "actionType": action_type,
        "summary": summary,
        "payload": payload,
        "status": status,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.agent_decisions.insert_one(rec)
    rec.pop("_id", None)
    return rec


# =============================================================================
# POINTS EXPIRY (inactivity-based, opt-in via loyalty_config.pointsExpiryDays)
# =============================================================================
async def _expire_inactive_points(cfg: dict) -> list:
    """Zero out a customer's points balance once pointsExpiryDays have passed
    since their last earn/redeem activity. Inactivity-based rather than
    FIFO-per-earn (which would need tracking an expiry date per earn ledger
    entry and partially consuming it on redemption) — simpler, and matches
    how most POS loyalty programs actually communicate expiry to customers
    ("use your points within a year of your last visit")."""
    days = int(cfg.get("pointsExpiryDays") or 0)
    if days <= 0:
        return []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    customers = await db.customers.find({"points": {"$gt": 0}}, {"_id": 0, "id": 1, "points": 1}).to_list(20000)
    expired = []
    for c in customers:
        last = await db.loyalty_ledger.find_one(
            {"customerId": c["id"]}, {"_id": 0, "createdAt": 1}, sort=[("createdAt", -1)]
        )
        last_activity = (last or {}).get("createdAt")
        if not last_activity or last_activity >= cutoff:
            continue
        pts = int(c.get("points", 0))
        if pts <= 0:
            continue
        await db.customers.update_one({"id": c["id"]}, {"$inc": {"points": -pts}})
        await db.loyalty_ledger.insert_one({
            "id": f"LP-{str(uuid.uuid4())[:8].upper()}",
            "customerId": c["id"], "type": "expire", "points": -pts,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        })
        expired.append({"customerId": c["id"], "points": pts})
    return expired


async def _warn_expiring_points(cfg: dict) -> list:
    """One-time "your points expire soon" notice, sent expiryWarnDays before
    pointsExpiryDays actually zeroes a balance. Expiry used to run
    completely silently — a customer only found out their balance was gone
    after the fact, with no chance to use it first."""
    expiry_days = int(cfg.get("pointsExpiryDays") or 0)
    warn_days = int(cfg.get("expiryWarnDays") or 7)
    if expiry_days <= 0 or warn_days <= 0:
        return []
    from utils.notifications import send_email, send_sms
    now = datetime.now(timezone.utc)
    warn_cutoff = (now - timedelta(days=max(expiry_days - warn_days, 0))).isoformat()
    expire_cutoff = (now - timedelta(days=expiry_days)).isoformat()
    customers = await db.customers.find(
        {"points": {"$gt": 0}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "phone": 1, "points": 1, "loyaltyExpiryWarnedAt": 1},
    ).to_list(20000)
    warned = []
    for c in customers:
        last = await db.loyalty_ledger.find_one(
            {"customerId": c["id"]}, {"_id": 0, "createdAt": 1}, sort=[("createdAt", -1)]
        )
        last_activity = (last or {}).get("createdAt")
        # In the warning window: inactive long enough to be within
        # warn_days of expiring, but not already expired (that's
        # _expire_inactive_points's job, run separately in the same tick).
        if not last_activity or not (expire_cutoff < last_activity <= warn_cutoff):
            continue
        already_warned = c.get("loyaltyExpiryWarnedAt")
        if already_warned and already_warned >= last_activity:
            continue  # already warned for this inactivity stretch — new activity would push last_activity forward
        if not c.get("email") and not c.get("phone"):
            continue
        try:
            last_dt = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        days_left = max(0, (last_dt + timedelta(days=expiry_days) - now).days)
        pts = int(c.get("points", 0))
        msg = f"You have {pts} points expiring in {days_left} day{'s' if days_left != 1 else ''} — visit us to keep them active!"
        if c.get("email"):
            await send_email(c["email"], "Your points are expiring soon",
                              f"<p>Hi {c.get('name', '')},</p><p>{msg}</p>")
        if c.get("phone"):
            await send_sms(c["phone"], msg)
        await db.customers.update_one({"id": c["id"]}, {"$set": {"loyaltyExpiryWarnedAt": now.isoformat()}})
        warned.append({"customerId": c["id"], "points": pts, "daysLeft": days_left})
    return warned


# =============================================================================
# TIER RE-EVALUATION (upgrade always; downgrade opt-in, with a grace period)
# =============================================================================
async def _reevaluate_tiers(cfg: dict) -> dict:
    """Recompute each customer's tier from their current points balance
    against routes/loyalty.py's owner-editable loyalty_tiers ladder.
    Upgrades apply immediately (unchanged from before). Downgrades only
    happen when downgradeEnabled is on, and only after the customer has sat
    below their tier's threshold continuously for downgradeGraceDays — a
    single slow week shouldn't cost someone their tier the moment this
    tick runs."""
    tiers = await db.loyalty_tiers.find({}, {"_id": 0}).to_list(20)
    if not tiers:
        return {"downgraded": [], "upgraded": []}
    tiers_desc = sorted(tiers, key=lambda t: t.get("minPoints", 0), reverse=True)
    downgrade_enabled = bool(cfg.get("downgradeEnabled", False))
    grace_days = int(cfg.get("downgradeGraceDays") or 30)
    now = datetime.now(timezone.utc)

    customers = await db.customers.find(
        {"membershipTier": {"$exists": True}},
        {"_id": 0, "id": 1, "points": 1, "membershipTier": 1, "tierGraceStartedAt": 1},
    ).to_list(20000)
    downgraded, upgraded = [], []
    for c in customers:
        pts = int(c.get("points", 0))
        qualifying = next((t["name"] for t in tiers_desc if pts >= t.get("minPoints", 0)), tiers_desc[-1]["name"])
        current = c.get("membershipTier", tiers_desc[-1]["name"])
        rank = {t["name"]: i for i, t in enumerate(tiers_desc)}  # 0 = highest tier
        cur_rank = rank.get(current, len(tiers_desc) - 1)
        qual_rank = rank.get(qualifying, len(tiers_desc) - 1)

        if qual_rank < cur_rank:
            # Balance now qualifies for a HIGHER tier than currently held.
            await db.customers.update_one(
                {"id": c["id"]}, {"$set": {"membershipTier": qualifying}, "$unset": {"tierGraceStartedAt": ""}}
            )
            upgraded.append({"customerId": c["id"], "from": current, "to": qualifying})
        elif qual_rank > cur_rank:
            # Balance has fallen below the current tier's threshold.
            if not downgrade_enabled:
                continue
            started = c.get("tierGraceStartedAt")
            if not started:
                await db.customers.update_one({"id": c["id"]}, {"$set": {"tierGraceStartedAt": now.isoformat()}})
                continue
            started_dt = datetime.fromisoformat(started.replace("Z", "+00:00")) if isinstance(started, str) else started
            if started_dt.tzinfo is None:
                started_dt = started_dt.replace(tzinfo=timezone.utc)
            if (now - started_dt).days >= grace_days:
                await db.customers.update_one(
                    {"id": c["id"]}, {"$set": {"membershipTier": qualifying}, "$unset": {"tierGraceStartedAt": ""}}
                )
                downgraded.append({"customerId": c["id"], "from": current, "to": qualifying})
        elif c.get("tierGraceStartedAt"):
            # Back at/above threshold before the grace period ran out — clear it.
            await db.customers.update_one({"id": c["id"]}, {"$unset": {"tierGraceStartedAt": ""}})
    return {"downgraded": downgraded, "upgraded": upgraded}


@router.get("/agent/segments")
async def get_segments(_: dict = Depends(require_owner_or_manager)):
    s = await _segment_customers()
    return {"segments": {k: len(v) for k, v in s.items()}, "ids": s}


@router.get("/agent/decisions")
async def get_decisions( limit: int = 100, _: dict = Depends(require_owner_or_manager)):
    decisions = await db.agent_decisions.find({}, {"_id": 0}).sort("createdAt", -1).to_list(limit)
    return decisions


@router.post("/agent/tick")
async def agent_tick(request: Request, user: dict = Depends(require_owner_or_manager)):
    """Run all autonomous rules once. Returns the list of decisions taken."""
    decisions = []
    # 1. Auto-segment + flag at-risk
    segs = await _segment_customers()
    if len(segs["at_risk"]) > 0:
        decisions.append(await _record_decision("at_risk_flagged",
            f"Flagged {len(segs['at_risk'])} customers as at-risk (no visit in 60 days)",
            {"customerIds": segs["at_risk"][:20]}))
    # 2. Birthday vouchers — actually issue wallet vouchers for customers whose
    # birthday month is now (idempotent per customer per year).
    from services.wallet_service import ensure_birthday_voucher
    customers = await db.customers.find({"birthday": {"$exists": True}}, {"_id": 0}).to_list(5000)
    issued = []
    for c in customers:
        try:
            v = await ensure_birthday_voucher(c)
            if v:
                issued.append({"customerId": c["id"], "name": c.get("name"), "voucherId": v["id"], "amount": v["amount"]})
        except Exception:
            continue
    if issued:
        decisions.append(await _record_decision("birthday_vouchers",
            f"Issued {len(issued)} birthday-month vouchers straight to customer wallets",
            {"issued": issued[:20]}))
    # 3. Inventory low-stock reorder suggestions
    products = await db.products.find({"stock": {"$lte": 5}, "active": {"$ne": False}}, {"_id": 0, "id": 1, "name": 1, "stock": 1}).to_list(500)
    if products:
        decisions.append(await _record_decision("low_stock_alert",
            f"{len(products)} products at/below 5 units — suggest reorder",
            {"products": [{"id": p["id"], "name": p["name"], "stock": p["stock"]} for p in products[:20]]}))
    # 4. Anomaly check on inventory
    try:
        from routes.v15_features import inventory_anomalies  # reuse
        anom = await inventory_anomalies(request)
        if anom.get("anomalies"):
            decisions.append(await _record_decision("inventory_anomaly",
                f"Detected {len(anom['anomalies'])} unusual sales velocity",
                {"anomalies": anom["anomalies"][:10]}))
    except Exception:
        pass
    # 5. Tonight-only blast suggestion if low booking count
    today_iso = today.date().isoformat()
    bookings_today = await db.reservations.count_documents({"date": today_iso})
    if bookings_today < 5:
        decisions.append(await _record_decision("blast_suggested",
            f"Only {bookings_today} bookings tonight — suggest 20% off SMS blast to VIPs",
            {"bookingsToday": bookings_today, "vipCount": len(segs["vip"])},
            status="suggested"))
    # 6. Points expiry warning + 7. Points expiry + 8. Tier re-evaluation —
    # all opt-in via loyalty_config (pointsExpiryDays / downgradeEnabled),
    # no-ops otherwise. Warning runs before expiry so a customer who's about
    # to lose points this tick was at least told last tick, not the same run.
    cfg = await get_config()
    warned = await _warn_expiring_points(cfg)
    if warned:
        decisions.append(await _record_decision("points_expiry_warned",
            f"Sent expiry warning to {len(warned)} customer(s) with points expiring soon",
            {"warned": warned[:20]}))
    expired = await _expire_inactive_points(cfg)
    if expired:
        decisions.append(await _record_decision("points_expired",
            f"Expired inactive points for {len(expired)} customer(s)",
            {"expired": expired[:20]}))
    tier_changes = await _reevaluate_tiers(cfg)
    if tier_changes["upgraded"]:
        decisions.append(await _record_decision("tier_upgraded",
            f"{len(tier_changes['upgraded'])} customer(s) auto-upgraded to a higher tier",
            {"upgraded": tier_changes["upgraded"][:20]}))
    if tier_changes["downgraded"]:
        decisions.append(await _record_decision("tier_downgraded",
            f"{len(tier_changes['downgraded'])} customer(s) downgraded after {cfg.get('downgradeGraceDays', 30)} days below their tier's threshold",
            {"downgraded": tier_changes["downgraded"][:20]}))
    return {"decisionsCount": len(decisions), "decisions": decisions, "segments": {k: len(v) for k, v in segs.items()}}


# =============================================================================
# VOICE COMMAND ROUTER (natural language → action)
# =============================================================================
@router.post("/agent/voice-command")
async def voice_command(data: dict, request: Request, user: dict = Depends(get_user)):
    """Accepts text or audio (base64), classifies intent, executes."""
    text = (data.get("text") or "").strip()
    audio_b64 = data.get("audioBase64")
    if audio_b64 and not text:
        try:
            from routes.v15_features import voice_order
            r = await voice_order({"audioBase64": audio_b64, "mime": data.get("mime", "audio/webm")}, request)
            text = r.get("transcript", "") if isinstance(r, dict) else ""
        except Exception:
            pass

    if not text:
        raise HTTPException(status_code=400, detail="text or audioBase64 required")

    # Quick intent routing using simple LLM call
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ.get("EMERGENT_LLM_KEY"),
            session_id=f"voice-cmd-{user['id']}-{uuid.uuid4()}",
            system_message=(
                "Classify this restaurant POS command into one of these intents and return STRICT JSON only: "
                "navigate, add_item, book_reservation, run_report, agent_tick, redeem_points, message_blast, unknown. "
                "Format: {\"intent\":\"...\",\"target\":\"...\",\"args\":{...}}. "
                "Examples: 'open dashboard' → navigate dashboard; 'add 2 flat whites' → add_item; "
                "'show today report' → run_report; 'send tonight blast to vips' → message_blast; "
                "'pay using my points' → redeem_points."
            ),
        )
        chat.with_model("openai", "gpt-5.2")
        resp = await chat.send_message(UserMessage(text=text))
        # Parse JSON from response
        try:
            parsed = json.loads(resp.strip().strip("`").strip())
        except Exception:
            # fallback: try to extract braces
            import re
            m = re.search(r"\{.*\}", resp, re.DOTALL)
            parsed = json.loads(m.group(0)) if m else {"intent": "unknown", "raw": resp}
    except Exception as e:
        return {"transcript": text, "intent": "unknown", "error": str(e)[:200]}

    intent = parsed.get("intent", "unknown")
    # Map intent → action route hint for the frontend to execute
    route_map = {
        "navigate": {"navigate": parsed.get("target", "/")},
        "add_item": {"action": "add_to_cart", "items": parsed.get("args", {}).get("items", [])},
        "book_reservation": {"navigate": "/reservations", "preset": parsed.get("args", {})},
        "run_report": {"navigate": "/end-of-day"},
        "redeem_points": {"action": "redeem_points"},
        "message_blast": {"action": "open_blast", "audience": parsed.get("args", {}).get("audience", "vip")},
        "agent_tick": {"action": "agent_tick"},
    }
    return {"transcript": text, "intent": intent, "parsed": parsed, "instruction": route_map.get(intent, {})}


# =============================================================================
# VOICE COMMAND CATALOG (per section)
# =============================================================================
VOICE_CATALOG = {
    "POS": [
        "Add two flat whites and a croissant",
        "Hold this order",
        "Pay using points",
        "Show tabs",
        "Open dashboard",
    ],
    "Items": [
        "Show items",
        "Add new item called Iced Latte for $5.50 in Beverages",
        "Generate image for Avocado Toast",
        "Import items from CSV",
    ],
    "Reservations": [
        "Show today's bookings",
        "Add booking for 4 at 7 PM",
        "Open floor plan",
        "Send confirmation SMS to next booking",
    ],
    "Roster": [
        "Show this week's roster",
        "Run AI auto-roster",
        "Approve all pending swap requests",
    ],
    "Customers": [
        "Show VIP customers",
        "Send tonight blast to at-risk customers",
        "Export GDPR data for John",
    ],
    "Reports": [
        "Show today's revenue",
        "Run end of day",
        "Show inventory anomalies",
        "What's our retention rate?",
    ],
    "Agent": [
        "Run agent tick",
        "Show recent decisions",
        "Approve birthday vouchers",
    ],
}

@router.get("/agent/voice-catalog")
async def voice_catalog():
    return VOICE_CATALOG
