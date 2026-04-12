from fastapi import APIRouter, HTTPException, Request
from database import db
from datetime import datetime, timezone
import uuid

router = APIRouter()

# ============ TIP MANAGEMENT (Toast-style) ============
@router.post("/tips/add")
async def add_tip(data: dict):
    tip = {
        "id": f"TIP-{str(uuid.uuid4())[:8].upper()}",
        "transactionId": data.get("transactionId", ""),
        "staffId": data.get("staffId", ""),
        "staffName": data.get("staffName", ""),
        "amount": data.get("amount", 0),
        "method": data.get("method", "card"),  # card, cash, digital
        "pooled": data.get("pooled", False),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.tips.insert_one(tip)
    tip.pop("_id", None)
    return tip

@router.get("/tips")
async def get_tips(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    tips = await db.tips.find({}, {"_id": 0}).sort("createdAt", -1).to_list(5000)
    return tips

@router.get("/tips/summary")
async def get_tips_summary(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    tips = await db.tips.find({}, {"_id": 0}).to_list(10000)
    total = sum(t.get("amount", 0) for t in tips)
    by_staff = {}
    for t in tips:
        sid = t.get("staffId", "unknown")
        if sid not in by_staff:
            by_staff[sid] = {"name": t.get("staffName", "Unknown"), "total": 0, "count": 0}
        by_staff[sid]["total"] += t.get("amount", 0)
        by_staff[sid]["count"] += 1
    pooled = sum(t.get("amount", 0) for t in tips if t.get("pooled"))
    return {
        "totalTips": round(total, 2),
        "pooledAmount": round(pooled, 2),
        "byStaff": sorted(by_staff.values(), key=lambda x: x["total"], reverse=True),
        "tipCount": len(tips),
    }

@router.post("/tips/pool-distribute")
async def distribute_tip_pool(request: Request):
    """Distribute pooled tips equally among eligible staff"""
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    pooled = await db.tips.find({"pooled": True, "distributed": {"$ne": True}}, {"_id": 0}).to_list(10000)
    pool_total = sum(t.get("amount", 0) for t in pooled)
    staff = await db.auth_users.find({"role": {"$in": ["cashier", "manager"]}, "status": "active"}, {"_id": 0}).to_list(100)
    if not staff or pool_total == 0:
        return {"distributed": 0, "perPerson": 0}
    per_person = round(pool_total / len(staff), 2)
    for tip in pooled:
        await db.tips.update_one({"id": tip["id"]}, {"$set": {"distributed": True}})
    return {"distributed": round(pool_total, 2), "perPerson": per_person, "staffCount": len(staff)}

# ============ TRAINING MODE (Clover-style) ============
@router.get("/settings/training-mode")
async def get_training_mode():
    setting = await db.settings.find_one({"key": "training_mode"}, {"_id": 0})
    return {"enabled": setting.get("value", False) if setting else False}

@router.post("/settings/training-mode")
async def toggle_training_mode(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    enabled = data.get("enabled", False)
    await db.settings.update_one(
        {"key": "training_mode"},
        {"$set": {"key": "training_mode", "value": enabled, "updatedAt": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    return {"enabled": enabled, "message": f"Training mode {'enabled' if enabled else 'disabled'}"}

# ============ END-OF-DAY REPORTS (Square-style) ============
@router.get("/reports/end-of-day")
async def get_end_of_day_report(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")

    txns = await db.transactions.find({}, {"_id": 0}).to_list(10000)
    total_sales = sum(t.get("total", 0) for t in txns)
    total_txns = len(txns)
    avg_ticket = total_sales / max(total_txns, 1)

    by_payment = {}
    for t in txns:
        m = t.get("paymentMethod", "Unknown")
        by_payment[m] = by_payment.get(m, 0) + t.get("total", 0)

    by_hour = {}
    for t in txns:
        ts = t.get("timestamp")
        if ts and hasattr(ts, 'hour'):
            h = ts.hour
            by_hour[h] = by_hour.get(h, 0) + t.get("total", 0)

    refunds = await db.refunds.find({}, {"_id": 0}).to_list(1000)
    total_refunds = sum(r.get("amount", 0) for r in refunds)
    tips = await db.tips.find({}, {"_id": 0}).to_list(10000)
    total_tips = sum(t.get("amount", 0) for t in tips)
    total_gst = sum(t.get("gst", 0) for t in txns)

    product_sales = {}
    for t in txns:
        for item in t.get("items", []):
            pid = item.get("productId", "")
            if pid not in product_sales:
                product_sales[pid] = {"name": item.get("productName", ""), "qty": 0, "revenue": 0}
            product_sales[pid]["qty"] += item.get("quantity", 0)
            product_sales[pid]["revenue"] += item.get("price", 0) * item.get("quantity", 0)

    top_items = sorted(product_sales.values(), key=lambda x: x["revenue"], reverse=True)[:10]

    return {
        "date": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        "summary": {
            "totalSales": round(total_sales, 2), "totalTransactions": total_txns,
            "avgTicket": round(avg_ticket, 2), "totalRefunds": round(total_refunds, 2),
            "totalTips": round(total_tips, 2), "totalGST": round(total_gst, 2),
            "netSales": round(total_sales - total_refunds, 2),
        },
        "byPaymentMethod": [{"method": m, "total": round(v, 2)} for m, v in sorted(by_payment.items(), key=lambda x: x[1], reverse=True)],
        "byHour": [{"hour": h, "total": round(v, 2)} for h, v in sorted(by_hour.items())],
        "topItems": top_items,
    }

# ============ EMAIL MARKETING CAMPAIGNS ============
@router.post("/marketing/campaigns")
async def create_campaign(data: dict, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")

    campaign = {
        "id": f"CMP-{str(uuid.uuid4())[:8].upper()}",
        "name": data.get("name", ""),
        "subject": data.get("subject", ""),
        "body": data.get("body", ""),
        "targetTier": data.get("targetTier"),  # None = all members
        "status": "draft",
        "createdBy": user["id"],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "sentAt": None,
        "recipientCount": 0,
        "openCount": 0,
    }
    # Count target recipients
    query = {} if not campaign["targetTier"] else {"tier": campaign["targetTier"]}
    campaign["recipientCount"] = await db.members.count_documents(query)
    await db.campaigns.insert_one(campaign)
    campaign.pop("_id", None)
    return campaign

@router.get("/marketing/campaigns")
async def get_campaigns(request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    campaigns = await db.campaigns.find({}, {"_id": 0}).sort("createdAt", -1).to_list(100)
    return campaigns

@router.post("/marketing/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")

    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = {} if not campaign.get("targetTier") else {"tier": campaign["targetTier"]}
    members = await db.members.find(query, {"_id": 0, "password_hash": 0}).to_list(10000)

    # Store campaign send record (email delivery would be via SendGrid/SES in production)
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": "sent", "sentAt": datetime.now(timezone.utc).isoformat(), "recipientCount": len(members)}}
    )

    # Log each recipient
    for m in members:
        await db.campaign_sends.insert_one({
            "campaignId": campaign_id, "memberId": m["id"],
            "email": m["email"], "status": "queued",
            "sentAt": datetime.now(timezone.utc).isoformat(),
        })

    return {"message": f"Campaign sent to {len(members)} members", "recipientCount": len(members)}

@router.delete("/marketing/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, request: Request):
    from routes.auth import get_current_user
    user = await get_current_user(request)
    if user["role"] not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager access only")
    await db.campaigns.delete_one({"id": campaign_id})
    return {"message": "Campaign deleted"}
