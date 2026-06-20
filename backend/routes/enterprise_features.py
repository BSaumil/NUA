from fastapi import APIRouter, HTTPException, Request, Depends
from deps import get_user, require_owner, require_owner_or_manager
from database import db
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter()

# ============ AUTO SURCHARGING (Public Holiday + Weekend) ============
@router.get("/surcharge/settings")
async def get_surcharge_settings():
    s = await db.settings.find_one({"key": "surcharge_config"}, {"_id": 0})
    return s.get("value", {}) if s else {
        "weekendSurcharge": 0, "publicHolidaySurcharge": 0, "enabled": False,
        "publicHolidays": [], "weekendDays": ["Saturday", "Sunday"],
    }

@router.post("/surcharge/settings")
async def save_surcharge_settings(data: dict, _: dict = Depends(require_owner)):
    await db.settings.update_one({"key": "surcharge_config"}, {"$set": {"key": "surcharge_config", "value": data}}, upsert=True)
    return {"message": "Surcharge settings saved"}

@router.get("/surcharge/check")
async def check_surcharge():
    """Check if surcharge applies right now"""
    s = await db.settings.find_one({"key": "surcharge_config"}, {"_id": 0})
    config = s.get("value", {}) if s else {}
    if not config.get("enabled"):
        return {"surchargePercent": 0, "reason": None}
    now = datetime.now(timezone.utc)
    day_name = now.strftime("%A")
    date_str = now.strftime("%Y-%m-%d")
    if date_str in config.get("publicHolidays", []):
        return {"surchargePercent": config.get("publicHolidaySurcharge", 0), "reason": "Public Holiday Surcharge"}
    if day_name in config.get("weekendDays", []):
        return {"surchargePercent": config.get("weekendSurcharge", 0), "reason": "Weekend Surcharge"}
    return {"surchargePercent": 0, "reason": None}

# ============ LIVE SALES REPORTING ============
@router.get("/live-sales")
async def get_live_sales(_: dict = Depends(require_owner_or_manager)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    all_txns = await db.transactions.find({}, {"_id": 0}).to_list(50000)
    # Filter today's transactions
    today_txns = []
    for t in all_txns:
        ts = t.get("timestamp")
        if ts and hasattr(ts, 'replace'):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= today_start:
                today_txns.append(t)
        else:
            today_txns.append(t)
    if not today_txns and all_txns:
        today_txns = all_txns[-20:]  # Fallback: show last 20

    total = sum(t.get("total", 0) for t in today_txns)
    count = len(today_txns)
    avg = total / max(count, 1)
    # By hour
    by_hour = {}
    for t in today_txns:
        ts = t.get("timestamp")
        h = ts.hour if ts and hasattr(ts, 'hour') else 0
        by_hour[h] = by_hour.get(h, {"count": 0, "total": 0})
        by_hour[h]["count"] += 1
        by_hour[h]["total"] += t.get("total", 0)
    # Last 5 transactions
    last5 = sorted(today_txns, key=lambda x: x.get("timestamp", ""), reverse=True)[:5]
    for t in last5:
        t.pop("_id", None)

    return {
        "totalSales": round(total, 2), "transactionCount": count, "avgTicket": round(avg, 2),
        "byHour": [{"hour": h, "count": v["count"], "total": round(v["total"], 2)} for h, v in sorted(by_hour.items())],
        "recentTransactions": last5,
        "timestamp": now.isoformat(),
    }

# ============ CUSTOM PERMISSIONS (Granular) ============
ALL_PERMISSIONS = [
    "dashboard", "pre-shift", "command-center", "pos", "reservations", "floor-plan",
    "waitlist", "kitchen", "menu-engineering", "what-if", "products", "customers",
    "loyalty", "inventory", "ai-pantry", "forecasting", "automation", "accounting",
    "bas-gst", "staff", "staff-roster", "email-marketing", "tip-management",
    "end-of-day", "integrations", "settings",
]

@router.get("/permissions/all")
async def get_all_permissions():
    return ALL_PERMISSIONS

@router.get("/permissions/staff/{staff_id}")
async def get_staff_permissions(staff_id: str, _: dict = Depends(require_owner_or_manager)):
    staff = await db.auth_users.find_one({"id": staff_id}, {"_id": 0, "password_hash": 0})
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"staffId": staff_id, "name": staff.get("name"), "role": staff.get("role"), "customPermissions": staff.get("customPermissions", [])}

@router.post("/permissions/staff/{staff_id}")
async def set_staff_permissions(staff_id: str, data: dict, _: dict = Depends(require_owner)):
    permissions = data.get("permissions", [])
    valid = [p for p in permissions if p in ALL_PERMISSIONS]
    await db.auth_users.update_one({"id": staff_id}, {"$set": {"customPermissions": valid}})
    return {"message": f"Permissions updated ({len(valid)} permissions set)", "permissions": valid}

# ============ SMART KIOSK UPSELLS ============
@router.get("/pos/upsells")
async def get_upsells(request: Request):
    """Get smart upsell suggestions based on cart items"""
    cart_items = request.query_params.get("items", "").split(",")
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    txns = await db.transactions.find({}, {"_id": 0, "items": 1}).to_list(10000)
    # Find frequently bought together items
    co_purchases = {}
    for t in txns:
        items = [i.get("productId") for i in t.get("items", [])]
        for ci in cart_items:
            if ci in items:
                for other in items:
                    if other != ci and other not in cart_items:
                        co_purchases[other] = co_purchases.get(other, 0) + 1
    # Sort by frequency and return top 3
    top = sorted(co_purchases.items(), key=lambda x: x[1], reverse=True)[:3]
    suggestions = []
    for pid, freq in top:
        p = next((pr for pr in products if pr.get("id") == pid), None)
        if p:
            suggestions.append({"id": p["id"], "name": p["name"], "price": p["price"], "image": p.get("image", ""), "frequency": freq})
    return suggestions

# ============ AUTOMATED REPORTING ============
@router.get("/reports/automated-config")
async def get_report_config(_: dict = Depends(require_owner)):
    s = await db.settings.find_one({"key": "auto_report_config"}, {"_id": 0})
    return s.get("value", {}) if s else {
        "enabled": False, "frequency": "daily", "time": "23:00",
        "reportTypes": ["itemised", "category", "detailed"],
        "recipientEmail": "", "includeAIInsights": True,
    }

@router.post("/reports/automated-config")
async def save_report_config(data: dict, _: dict = Depends(require_owner)):
    await db.settings.update_one({"key": "auto_report_config"}, {"$set": {"key": "auto_report_config", "value": data}}, upsert=True)
    return {"message": "Automated report settings saved"}

@router.post("/reports/generate")
async def generate_report(data: dict, _: dict = Depends(require_owner_or_manager)):
    """Generate a report on demand"""

    report_type = data.get("type", "detailed")  # itemised, category, detailed
    period = data.get("period", "today")

    txns = await db.transactions.find({}, {"_id": 0}).to_list(50000)
    products = await db.products.find({}, {"_id": 0}).to_list(10000)

    if report_type == "itemised":
        item_sales = {}
        for t in txns:
            for item in t.get("items", []):
                pid = item.get("productId", "")
                if pid not in item_sales:
                    item_sales[pid] = {"name": item.get("productName", ""), "qty": 0, "revenue": 0, "cost": 0}
                item_sales[pid]["qty"] += item.get("quantity", 0)
                item_sales[pid]["revenue"] += item.get("price", 0) * item.get("quantity", 0)
                p = next((pr for pr in products if pr.get("id") == pid), {})
                item_sales[pid]["cost"] += p.get("cost", 0) * item.get("quantity", 0)
        items = sorted(item_sales.values(), key=lambda x: x["revenue"], reverse=True)
        for i in items:
            i["profit"] = round(i["revenue"] - i["cost"], 2)
            i["margin"] = round((i["profit"] / max(i["revenue"], 0.01)) * 100, 1)
        return {"type": "itemised", "items": items, "totalRevenue": round(sum(i["revenue"] for i in items), 2), "totalProfit": round(sum(i["profit"] for i in items), 2)}

    elif report_type == "category":
        cat_sales = {}
        for t in txns:
            for item in t.get("items", []):
                cat = item.get("category", "Uncategorized")
                if not cat:
                    p = next((pr for pr in products if pr.get("id") == item.get("productId")), {})
                    cat = p.get("category", "Uncategorized")
                if cat not in cat_sales:
                    cat_sales[cat] = {"qty": 0, "revenue": 0, "cost": 0}
                cat_sales[cat]["qty"] += item.get("quantity", 0)
                cat_sales[cat]["revenue"] += item.get("price", 0) * item.get("quantity", 0)
        cats = [{"category": k, **v, "profit": round(v["revenue"] - v["cost"], 2)} for k, v in sorted(cat_sales.items(), key=lambda x: x[1]["revenue"], reverse=True)]
        return {"type": "category", "categories": cats, "totalRevenue": round(sum(c["revenue"] for c in cats), 2)}

    else:  # detailed
        total_revenue = sum(t.get("total", 0) for t in txns)
        total_gst = sum(t.get("gst", 0) for t in txns)
        expenses = await db.expenses.find({}, {"_id": 0}).to_list(10000)
        total_expenses = sum(e.get("amount", 0) for e in expenses)
        cogs = sum(e.get("amount", 0) for e in expenses if e.get("category") in ("Wages", "Ingredients", "Food Supplies", "Superannuation"))
        refunds = await db.refunds.find({}, {"_id": 0}).to_list(1000)
        total_refunds = sum(r.get("amount", 0) for r in refunds)
        return {
            "type": "detailed",
            "revenue": round(total_revenue, 2), "gst": round(total_gst, 2),
            "expenses": round(total_expenses, 2), "cogs": round(cogs, 2),
            "refunds": round(total_refunds, 2),
            "grossProfit": round(total_revenue - cogs, 2),
            "netProfit": round(total_revenue - total_expenses - total_refunds, 2),
            "transactionCount": len(txns),
        }

# ============ HARDWARE INTEGRATIONS ============
@router.get("/hardware/printers")
async def get_printer_configs():
    printers = await db.hardware_printers.find({}, {"_id": 0}).to_list(100)
    return printers

@router.post("/hardware/printers")
async def add_printer(data: dict, _: dict = Depends(require_owner_or_manager)):
    printer = {
        "id": f"PRT-{str(uuid.uuid4())[:8].upper()}",
        "name": data.get("name", ""), "type": data.get("type", "receipt"),
        "connectionType": data.get("connectionType", "usb"),  # usb, network, bluetooth
        "ipAddress": data.get("ipAddress", ""), "port": data.get("port", 9100),
        "model": data.get("model", ""), "status": "configured",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.hardware_printers.insert_one(printer)
    printer.pop("_id", None)
    return printer

@router.delete("/hardware/printers/{printer_id}")
async def delete_printer(printer_id: str, _: dict = Depends(require_owner_or_manager)):
    await db.hardware_printers.delete_one({"id": printer_id})
    return {"message": "Printer removed"}

@router.get("/hardware/scanners")
async def get_scanner_configs():
    scanners = await db.hardware_scanners.find({}, {"_id": 0}).to_list(100)
    return scanners

@router.post("/hardware/scanners")
async def add_scanner(data: dict, _: dict = Depends(require_owner_or_manager)):
    scanner = {
        "id": f"SCN-{str(uuid.uuid4())[:8].upper()}",
        "name": data.get("name", ""), "type": data.get("type", "barcode"),
        "connectionType": data.get("connectionType", "usb"),
        "model": data.get("model", ""), "status": "configured",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.hardware_scanners.insert_one(scanner)
    scanner.pop("_id", None)
    return scanner
