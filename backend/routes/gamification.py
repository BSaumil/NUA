from fastapi import APIRouter, HTTPException, Request, Depends
from deps import get_user, require_owner, require_owner_or_manager
from database import db
from datetime import datetime, timezone, timedelta
import uuid, os

router = APIRouter()

# ============ STAFF LEADERBOARD ============
@router.get("/staff/leaderboard")
async def get_staff_leaderboard(_: dict = Depends(get_user)):

    staff = await db.auth_users.find({"status": "active", "role": {"$ne": "owner"}}, {"_id": 0, "password_hash": 0}).to_list(100)
    txns = await db.transactions.find({}, {"_id": 0}).to_list(50000)
    timecards = await db.timecards.find({"clockOut": {"$ne": None}}, {"_id": 0}).to_list(50000)
    tips = await db.tips.find({}, {"_id": 0}).to_list(10000)

    leaderboard = []
    for s in staff:
        staff_txns = [t for t in txns if t.get("cashier") == s["name"] or t.get("cashierId") == s["id"]]
        staff_tips = [t for t in tips if t.get("staffId") == s["id"] or t.get("staffName") == s["name"]]
        staff_cards = [tc for tc in timecards if tc.get("staffId") == s["id"]]
        total_sales = sum(t.get("total", 0) for t in staff_txns)
        total_txns = len(staff_txns)
        total_tips = sum(t.get("amount", 0) for t in staff_tips)
        total_hours = sum(tc.get("hoursWorked", 0) for tc in staff_cards)
        avg_txn = total_sales / max(total_txns, 1)
        sales_per_hour = total_sales / max(total_hours, 1)
        # Performance score: weighted composite
        score = round((total_sales * 0.4) + (total_txns * 2) + (total_tips * 3) + (sales_per_hour * 0.5), 2)

        leaderboard.append({
            "id": s["id"], "name": s["name"], "role": s["role"],
            "totalSales": round(total_sales, 2), "totalTransactions": total_txns,
            "totalTips": round(total_tips, 2), "totalHours": round(total_hours, 2),
            "avgTransaction": round(avg_txn, 2), "salesPerHour": round(sales_per_hour, 2),
            "performanceScore": score,
        })

    leaderboard.sort(key=lambda x: x["performanceScore"], reverse=True)
    for i, s in enumerate(leaderboard):
        s["rank"] = i + 1

    return {"leaderboard": leaderboard, "generatedAt": datetime.now(timezone.utc).isoformat()}

# ============ SMART TIP DISTRIBUTION (Hours + Performance) ============
@router.post("/tips/smart-distribute")
async def smart_distribute_tips(_: dict = Depends(require_owner)):
    """Distribute pooled tips based on hours worked and performance score"""

    tips = await db.tips.find({"pooled": True, "distributed": {"$ne": True}}, {"_id": 0}).to_list(10000)
    pool_total = sum(t.get("amount", 0) for t in tips)
    if pool_total <= 0:
        return {"message": "No pooled tips to distribute", "distributed": 0}

    # Get staff performance data
    staff = await db.auth_users.find({"status": "active", "role": {"$ne": "owner"}}, {"_id": 0, "password_hash": 0}).to_list(100)
    timecards = await db.timecards.find({"clockOut": {"$ne": None}}, {"_id": 0}).to_list(50000)
    txns = await db.transactions.find({}, {"_id": 0}).to_list(50000)

    staff_weights = []
    total_weight = 0
    for s in staff:
        hours = sum(tc.get("hoursWorked", 0) for tc in timecards if tc.get("staffId") == s["id"])
        sales = sum(t.get("total", 0) for t in txns if t.get("cashier") == s["name"])
        # Weight = hours * (1 + performance_bonus)
        perf_bonus = min(sales / max(sum(t.get("total", 0) for t in txns), 1), 0.5)
        weight = hours * (1 + perf_bonus)
        staff_weights.append({"staff": s, "hours": hours, "sales": sales, "weight": weight})
        total_weight += weight

    if total_weight == 0:
        return {"message": "No staff hours recorded", "distributed": 0}

    distributions = []
    for sw in staff_weights:
        if sw["weight"] <= 0:
            continue
        share = round((sw["weight"] / total_weight) * pool_total, 2)
        distributions.append({
            "staffId": sw["staff"]["id"], "staffName": sw["staff"]["name"],
            "hours": round(sw["hours"], 2), "performanceWeight": round(sw["weight"], 2),
            "share": share,
        })

    # Mark tips as distributed
    tip_ids = [t.get("id") for t in tips]
    if tip_ids:
        await db.tips.update_many({"id": {"$in": tip_ids}}, {"$set": {"distributed": True}})

    # Log distribution
    dist_record = {
        "id": f"DIST-{str(uuid.uuid4())[:8].upper()}",
        "type": "smart", "poolTotal": round(pool_total, 2),
        "distributions": distributions,
        "distributedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.tip_distributions.insert_one(dist_record)
    dist_record.pop("_id", None)

    return dist_record

# ============ QUARTERLY REVIEW (Top/Worst Items + AI Alternatives) ============
@router.get("/reports/quarterly-review")
async def quarterly_review(_: dict = Depends(require_owner_or_manager)):

    txns = await db.transactions.find({}, {"_id": 0}).to_list(50000)
    products = await db.products.find({}, {"_id": 0}).to_list(10000)

    # Calculate item performance
    item_stats = {}
    for t in txns:
        for item in t.get("items", []):
            pid = item.get("productId", "")
            if pid not in item_stats:
                p = next((pr for pr in products if pr.get("id") == pid), {})
                item_stats[pid] = {
                    "id": pid, "name": item.get("productName", ""), "category": p.get("category", ""),
                    "price": p.get("price", 0), "cost": p.get("cost", 0),
                    "qtySold": 0, "revenue": 0,
                }
            item_stats[pid]["qtySold"] += item.get("quantity", 0)
            item_stats[pid]["revenue"] += item.get("price", 0) * item.get("quantity", 0)

    for item in item_stats.values():
        item["profit"] = round(item["revenue"] - (item["cost"] * item["qtySold"]), 2)
        item["margin"] = round((item["profit"] / max(item["revenue"], 0.01)) * 100, 1)

    sorted_items = sorted(item_stats.values(), key=lambda x: x["revenue"], reverse=True)
    top_sellers = sorted_items[:10]
    worst_sellers = sorted_items[-10:] if len(sorted_items) > 10 else []
    # Items with negative or very low margin
    underperformers = [i for i in sorted_items if i["margin"] < 20 and i["qtySold"] > 0]

    return {
        "period": "quarterly",
        "topSellers": top_sellers,
        "worstSellers": worst_sellers,
        "underperformers": underperformers[:10],
        "totalItems": len(sorted_items),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }

@router.post("/reports/quarterly-review/ai-alternatives")
async def quarterly_ai_alternatives(data: dict, _: dict = Depends(require_owner)):
    """AI suggests alternatives for worst-performing items"""

    items = data.get("items", [])
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        chat = LlmChat(api_key=api_key, session_id=f"quarterly-{uuid.uuid4()}", system_message="You are a restaurant menu consultant. Suggest replacement items for underperforming menu items. Be specific with names, pricing, and why they'd perform better. Keep each suggestion to 2-3 sentences.")
        chat.with_model("openai", "gpt-5.2")

        items_text = "\n".join([f"- {i.get('name')} (${i.get('price')}, margin {i.get('margin')}%, sold {i.get('qtySold')}x)" for i in items[:10]])
        prompt = f"""These menu items are underperforming. Suggest a replacement for each that would:
1. Appeal to the same customer segment
2. Have better margins (target 60%+)
3. Use similar or simpler ingredients

Underperforming items:
{items_text}

For each item, suggest ONE replacement with: name, suggested price, estimated food cost %, and brief reasoning."""

        msg = UserMessage(text=prompt)
        response = await chat.send_message(msg)
        return {"suggestions": response, "generatedAt": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        return {"suggestions": f"AI unavailable: {str(e)}", "generatedAt": datetime.now(timezone.utc).isoformat()}

# ============ CATEGORY-WISE PRINT ROUTING ============
@router.get("/print-routing/config")
async def get_print_routing():
    """Returns the current print-routing config. Auto-heals legacy shapes
    (e.g. an old dict-shaped `routes` field from a pre-v27 save) so the SPA
    can always call `config.routes.map(...)` without crashing."""
    defaults = {
        "enabled": True,
        "routes": [
            {"category": "Beverages", "printer": "Bar Printer", "priority": 1},
            {"category": "Alcohol", "printer": "Bar Printer", "priority": 1},
            {"category": "Food", "printer": "Kitchen Printer", "priority": 2},
            {"category": "Mains", "printer": "Kitchen Printer", "priority": 2},
            {"category": "Appetizers", "printer": "Kitchen Printer", "priority": 1},
            {"category": "Bakery", "printer": "Kitchen Printer", "priority": 3},
            {"category": "Desserts", "printer": "Kitchen Printer", "priority": 3},
            {"category": "Pizza", "printer": "Pizza Station", "priority": 1},
        ],
        "defaultPrinter": "Kitchen Printer",
        "defaultPriority": 2,
    }
    s = await db.settings.find_one({"key": "print_routing"}, {"_id": 0})
    if not s or not s.get("value"):
        return defaults

    cfg = s["value"] if isinstance(s.get("value"), dict) else {}
    # Coerce legacy `routes` shapes into a list.
    routes = cfg.get("routes")
    if isinstance(routes, dict):
        # Old shape: {"kitchen": "Kitchen Printer", ...}. Convert to the new
        # array-of-route-objects, preserving category → printer intent.
        cfg["routes"] = [
            {"category": cat.title(), "printer": prn, "priority": 2}
            for cat, prn in routes.items() if isinstance(prn, str)
        ]
    elif routes is None or not isinstance(routes, list):
        cfg["routes"] = defaults["routes"]
    cfg.setdefault("enabled", True)
    cfg.setdefault("defaultPrinter", defaults["defaultPrinter"])
    cfg.setdefault("defaultPriority", defaults["defaultPriority"])
    return cfg


@router.post("/print-routing/config")
async def save_print_routing(data: dict, _: dict = Depends(require_owner_or_manager)):
    """Persist print-routing config. Validates `routes` is an array of
    `{category, printer, priority}` objects — rejects legacy dict shapes so
    the SPA never crashes on a subsequent read."""
    from fastapi import HTTPException
    routes = data.get("routes", [])
    if not isinstance(routes, list):
        raise HTTPException(400, "`routes` must be an array of {category, printer, priority}")
    clean = []
    for r in routes:
        if not isinstance(r, dict) or not r.get("category") or not r.get("printer"):
            continue
        try:
            pr = int(r.get("priority", 2))
        except Exception:
            pr = 2
        clean.append({"category": r["category"], "printer": r["printer"], "priority": pr})
    payload = {
        "enabled": bool(data.get("enabled", True)),
        "routes": clean,
        "defaultPrinter": data.get("defaultPrinter") or "Kitchen Printer",
        "defaultPriority": int(data.get("defaultPriority") or 2),
    }
    await db.settings.update_one({"key": "print_routing"},
                                  {"$set": {"key": "print_routing", "value": payload}}, upsert=True)
    return {"message": "Print routing saved", "config": payload}

@router.post("/print-routing/send")
async def send_to_printers(data: dict, _: dict = Depends(get_user)):
    """Route order items to appropriate printers based on category"""

    order_items = data.get("items", [])
    order_id = data.get("orderId", f"ORD-{str(uuid.uuid4())[:8].upper()}")
    table_number = data.get("tableNumber", None)

    # Get routing config
    s = await db.settings.find_one({"key": "print_routing"}, {"_id": 0})
    if s and s.get("value"):
        config = s["value"]
    else:
        # Use defaults
        config = {
            "enabled": True,
            "routes": [
                {"category": "Beverages", "printer": "Bar Printer", "priority": 1},
                {"category": "Alcohol", "printer": "Bar Printer", "priority": 1},
                {"category": "Food", "printer": "Kitchen Printer", "priority": 2},
                {"category": "Mains", "printer": "Kitchen Printer", "priority": 2},
                {"category": "Appetizers", "printer": "Kitchen Printer", "priority": 1},
                {"category": "Bakery", "printer": "Kitchen Printer", "priority": 3},
                {"category": "Desserts", "printer": "Kitchen Printer", "priority": 3},
                {"category": "Pizza", "printer": "Pizza Station", "priority": 1},
            ],
            "defaultPrinter": "Kitchen Printer",
            "defaultPriority": 2,
        }
    routes = config.get("routes", [])
    default_printer = config.get("defaultPrinter", "Kitchen Printer")
    default_priority = config.get("defaultPriority", 2)

    # Group items by printer
    printer_jobs = {}
    for item in order_items:
        cat = item.get("category", "")
        route = next((r for r in routes if r["category"].lower() == cat.lower()), None)
        printer_name = route["printer"] if route else default_printer
        priority = route["priority"] if route else default_priority

        if printer_name not in printer_jobs:
            printer_jobs[printer_name] = {"printer": printer_name, "items": [], "priority": priority}
        printer_jobs[printer_name]["items"].append(item)
        printer_jobs[printer_name]["priority"] = min(printer_jobs[printer_name]["priority"], priority)

    # Create print jobs sorted by priority
    jobs = sorted(printer_jobs.values(), key=lambda x: x["priority"])
    print_records = []
    for job in jobs:
        record = {
            "id": f"PRINT-{str(uuid.uuid4())[:8].upper()}",
            "orderId": order_id, "tableNumber": table_number,
            "printer": job["printer"], "priority": job["priority"],
            "items": job["items"], "status": "queued",
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        await db.print_jobs.insert_one(record)
        record.pop("_id", None)
        print_records.append(record)

    return {"jobs": print_records, "totalPrinters": len(print_records)}

@router.get("/print-routing/queue")
async def get_print_queue(request: Request, printer: str = None):
    query = {"status": {"$in": ["queued", "printing"]}}
    if printer:
        query["printer"] = printer
    jobs = await db.print_jobs.find(query, {"_id": 0}).sort("priority", 1).to_list(100)
    return jobs

@router.post("/print-routing/complete/{job_id}")
async def complete_print_job(job_id: str):
    await db.print_jobs.update_one({"id": job_id}, {"$set": {"status": "printed", "printedAt": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Print job completed"}
