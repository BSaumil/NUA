from fastapi import APIRouter, HTTPException, Request, Depends
from deps import get_user, require_owner, require_owner_or_manager
from database import db
from datetime import datetime, timezone
import uuid

import os


router = APIRouter()

# ============ BUSINESS SETTINGS ============
@router.get("/business/settings")
async def get_business_settings():
    biz = await db.business_settings.find_one({"key": "main"}, {"_id": 0})
    return biz or {"name": "NUA", "abn": "", "address": "", "phone": "", "email": "", "taxId": ""}

@router.post("/business/settings")
async def save_business_settings(data: dict):
    data["key"] = "main"
    await db.business_settings.update_one({"key": "main"}, {"$set": data}, upsert=True)
    return {"message": "Business settings saved"}


# Brand theme (colors) — shared across every terminal/device for the business,
# not just the browser that changed it. The Settings color pickers still give
# an instant local preview as you drag/type; "Save" is what makes it apply
# everywhere else too.
@router.get("/business/theme")
async def get_business_theme():
    doc = await db.settings.find_one({"key": "business_theme"}, {"_id": 0})
    return doc.get("value") if doc else None


@router.post("/business/theme")
async def save_business_theme(data: dict, _: dict = Depends(require_owner_or_manager)):
    allowed = {"primary", "secondary", "accent", "background", "text", "sidebar"}
    theme = {k: v for k, v in data.items() if k in allowed and isinstance(v, str)}
    await db.settings.update_one(
        {"key": "business_theme"}, {"$set": {"key": "business_theme", "value": theme}}, upsert=True
    )
    return theme


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
async def get_tips(_: dict = Depends(require_owner_or_manager)):
    tips = await db.tips.find({}, {"_id": 0}).sort("createdAt", -1).to_list(5000)
    return tips

@router.get("/tips/summary")
async def get_tips_summary(_: dict = Depends(require_owner)):
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
async def distribute_tip_pool(_: dict = Depends(require_owner)):
    """Distribute pooled tips equally among eligible staff"""
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
async def toggle_training_mode(data: dict, _: dict = Depends(require_owner_or_manager)):
    enabled = data.get("enabled", False)
    await db.settings.update_one(
        {"key": "training_mode"},
        {"$set": {"key": "training_mode", "value": enabled, "updatedAt": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    return {"enabled": enabled, "message": f"Training mode {'enabled' if enabled else 'disabled'}"}

# ============ END-OF-DAY REPORTS (Square-style, Comprehensive) ============
@router.get("/reports/end-of-day")
async def get_end_of_day_report( period: str = "today", start_date: str = None, end_date: str = None, _: dict = Depends(require_owner_or_manager)):

    # Build date filter
    query = {}
    now = datetime.now(timezone.utc)
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "yesterday":
        start = (now - __import__('datetime').timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59)
    elif period == "week":
        start = (now - __import__('datetime').timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "quarter":
        q_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=q_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
    elif period == "custom" and start_date and end_date:
        start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now

    # Get all transactions (filter by date if they have datetime timestamps)
    all_txns = await db.transactions.find({}, {"_id": 0}).to_list(50000)
    txns = []
    for t in all_txns:
        ts = t.get("timestamp")
        if ts:
            if hasattr(ts, 'replace'):
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if start <= ts <= end:
                    txns.append(t)
            else:
                txns.append(t)
        else:
            txns.append(t)

    # If no date filtering worked (all timestamps are strings etc), use all
    if len(txns) == 0 and len(all_txns) > 0:
        txns = all_txns

    total_sales = sum(t.get("total", 0) for t in txns)
    total_txns = len(txns)
    avg_ticket = total_sales / max(total_txns, 1)

    # By payment method
    by_payment = {}
    for t in txns:
        m = t.get("paymentMethod", "Unknown")
        by_payment[m] = by_payment.get(m, 0) + t.get("total", 0)

    # By hour
    by_hour = {}
    for t in txns:
        ts = t.get("timestamp")
        if ts and hasattr(ts, 'hour'):
            h = ts.hour
            by_hour[h] = by_hour.get(h, 0) + t.get("total", 0)

    # By category — categories marked "reports under" another category roll
    # their sales up into that category's label (e.g. an "Iced Coffee"
    # sub-category reporting as "Coffee"), resolved from the current
    # category setup at report time.
    from routes.items_system import build_reporting_map
    reporting_map = await build_reporting_map()
    by_category = {}
    product_sales = {}
    for t in txns:
        for item in t.get("items", []):
            cat = reporting_map.get(item.get("category", "Uncategorized"), item.get("category", "Uncategorized"))
            pid = item.get("productId", "")
            qty = item.get("quantity", 0)
            rev = item.get("price", 0) * qty
            by_category[cat] = by_category.get(cat, {"qty": 0, "revenue": 0})
            by_category[cat]["qty"] += qty
            by_category[cat]["revenue"] += rev
            if pid not in product_sales:
                product_sales[pid] = {"name": item.get("productName", ""), "category": cat, "qty": 0, "revenue": 0}
            product_sales[pid]["qty"] += qty
            product_sales[pid]["revenue"] += rev

    top_items = sorted(product_sales.values(), key=lambda x: x["revenue"], reverse=True)[:15]

    # Refunds & tips
    refunds = await db.refunds.find({}, {"_id": 0}).to_list(1000)
    total_refunds = sum(r.get("amount", 0) for r in refunds)
    tips = await db.tips.find({}, {"_id": 0}).to_list(10000)
    total_tips = sum(t.get("amount", 0) for t in tips)
    total_gst = sum(t.get("gst", 0) for t in txns)

    # Customer analytics
    customer_ids = [t.get("customerId") for t in txns if t.get("customerId")]
    unique_customers = len(set(customer_ids))
    customers = await db.customers.find({}, {"_id": 0}).to_list(10000)
    cust_map = {c.get("id"): c for c in customers}
    new_customers = 0
    returning_customers = 0
    for cid in set(customer_ids):
        c = cust_map.get(cid, {})
        if c.get("visits", 0) <= 1:
            new_customers += 1
        else:
            returning_customers += 1
    walk_ins = total_txns - len(customer_ids)
    total_covers = total_txns  # each txn = 1 cover approx

    # Spending habits
    spend_by_customer = {}
    for t in txns:
        cid = t.get("customerId", "walk-in")
        spend_by_customer[cid] = spend_by_customer.get(cid, 0) + t.get("total", 0)
    avg_customer_spend = sum(spend_by_customer.values()) / max(len(spend_by_customer), 1)
    top_spenders = sorted(
        [{"id": k, "name": cust_map.get(k, {}).get("name", "Walk-in"), "total": round(v, 2)} for k, v in spend_by_customer.items()],
        key=lambda x: x["total"], reverse=True
    )[:10]

    return {
        "period": period,
        "dateRange": {"start": start.isoformat(), "end": end.isoformat()},
        "summary": {
            "totalSales": round(total_sales, 2), "totalTransactions": total_txns,
            "avgTicket": round(avg_ticket, 2), "totalRefunds": round(total_refunds, 2),
            "totalTips": round(total_tips, 2), "totalGST": round(total_gst, 2),
            "netSales": round(total_sales - total_refunds, 2),
        },
        "byPaymentMethod": [{"method": m, "total": round(v, 2)} for m, v in sorted(by_payment.items(), key=lambda x: x[1], reverse=True)],
        "byHour": [{"hour": h, "total": round(v, 2)} for h, v in sorted(by_hour.items())],
        "byCategory": [{"category": k, "qty": v["qty"], "revenue": round(v["revenue"], 2)} for k, v in sorted(by_category.items(), key=lambda x: x[1]["revenue"], reverse=True)],
        "topItems": top_items,
        "customerAnalytics": {
            "totalCovers": total_covers,
            "uniqueCustomers": unique_customers,
            "walkIns": walk_ins,
            "newCustomers": new_customers,
            "returningCustomers": returning_customers,
            "avgCustomerSpend": round(avg_customer_spend, 2),
            "topSpenders": top_spenders,
        },
    }

# ============ EMAIL MARKETING CAMPAIGNS ============
@router.post("/marketing/campaigns")
async def create_campaign(data: dict, user: dict = Depends(require_owner_or_manager)):

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
async def get_campaigns(_: dict = Depends(require_owner_or_manager)):
    campaigns = await db.campaigns.find({}, {"_id": 0}).sort("createdAt", -1).to_list(100)
    return campaigns

@router.post("/marketing/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: str, _: dict = Depends(require_owner_or_manager)):

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
async def delete_campaign(campaign_id: str, _: dict = Depends(require_owner_or_manager)):
    await db.campaigns.delete_one({"id": campaign_id})
    return {"message": "Campaign deleted"}


# ============ AI EOD INSIGHTS ============
@router.post("/reports/ai-insights")
async def generate_ai_insights(data: dict, _: dict = Depends(require_owner_or_manager)):

    report_data = data.get("reportData", {})
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        chat = LlmChat(api_key=api_key, session_id=f"eod-{uuid.uuid4()}", system_message="You are an expert restaurant business analyst. Provide concise, actionable insights from POS data. Use bullet points. Be specific with numbers. Keep response under 300 words.")
        chat.with_model("openai", "gpt-5.2")

        summary = report_data.get("summary", {})
        prompt = f"""Analyze this restaurant's End-of-Day report and provide actionable insights:

Sales: ${summary.get('totalSales', 0):.2f} | Net: ${summary.get('netSales', 0):.2f} | Transactions: {summary.get('totalTransactions', 0)}
Avg Ticket: ${summary.get('avgTicket', 0):.2f} | GST: ${summary.get('totalGST', 0):.2f}
Refunds: ${summary.get('totalRefunds', 0):.2f} | Tips: ${summary.get('totalTips', 0):.2f}

Payment Methods: {report_data.get('byPaymentMethod', [])}
Top Items: {report_data.get('topItems', [])[:5]}
Categories: {report_data.get('byCategory', [])}
Customer Analytics: {report_data.get('customerAnalytics', {})}
Hourly Sales: {report_data.get('byHour', [])}

Provide:
1. Key Performance Highlights (2-3 bullets)
2. Areas of Concern (if any)
3. Actionable Recommendations (2-3 specific suggestions)
4. Staffing Insight based on hourly data
5. Customer Retention Insight"""

        msg = UserMessage(text=prompt)
        response = await chat.send_message(msg)

        insight = {
            "id": f"AI-{str(uuid.uuid4())[:8].upper()}",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "insights": response,
            "period": data.get("period", "today"),
        }
        await db.ai_insights.insert_one(insight)
        insight.pop("_id", None)
        return insight
    except Exception as e:
        return {"insights": f"AI insights unavailable: {str(e)}", "generatedAt": datetime.now(timezone.utc).isoformat()}
