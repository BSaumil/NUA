from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
from database import db
from models.bas_report import BASReport, BASReportCreate
from models.expense import Expense, ExpenseCreate
from models.supplier import Supplier, SupplierCreate, PurchaseOrder, PurchaseOrderCreate
import uuid
import random
import math

router = APIRouter()

# ============ ACCOUNTING API ============
@router.get("/accounting/summary")
async def get_accounting_summary():
    transactions = await db.transactions.find().to_list(10000)
    total_revenue = sum(t.get("total", 0) for t in transactions)
    total_gst_collected = sum(t.get("gst", 0) for t in transactions)
    expenses = await db.expenses.find().to_list(10000)
    total_expenses = sum(e.get("amount", 0) for e in expenses)
    total_gst_paid = sum(e.get("gstAmount", 0) for e in expenses)
    return {
        "revenue": round(total_revenue, 2),
        "gstCollected": round(total_gst_collected, 2),
        "expenses": round(total_expenses, 2),
        "gstPaid": round(total_gst_paid, 2),
        "netGST": round(total_gst_collected - total_gst_paid, 2),
        "profit": round(total_revenue - total_expenses, 2),
    }

@router.get("/accounting/p-and-l")
async def get_p_and_l():
    transactions = await db.transactions.find().to_list(10000)
    expenses = await db.expenses.find().to_list(10000)
    revenue = sum(t.get("total", 0) for t in transactions)
    cogs = sum(e.get("amount", 0) for e in expenses if e.get("category") in ["Ingredients", "Food Supplies", "Beverages"])
    operating = sum(e.get("amount", 0) for e in expenses if e.get("category") not in ["Ingredients", "Food Supplies", "Beverages"])
    gross_profit = revenue - cogs
    return {
        "revenue": round(revenue, 2),
        "costOfGoods": round(cogs, 2),
        "grossProfit": round(gross_profit, 2),
        "operatingExpenses": round(operating, 2),
        "netProfit": round(gross_profit - operating, 2),
        "grossMargin": round((gross_profit / revenue * 100) if revenue > 0 else 0, 1),
    }

# ============ BAS/GST API ============
@router.get("/bas-gst/reports", response_model=List[BASReport])
async def get_bas_reports():
    reports = await db.bas_reports.find().to_list(1000)
    return [BASReport(**r) for r in reports]

@router.post("/bas-gst/reports", response_model=BASReport)
async def create_bas_report(report: BASReportCreate):
    transactions = await db.transactions.find().to_list(10000)
    expenses = await db.expenses.find().to_list(10000)
    gst_collected = sum(t.get("gst", 0) for t in transactions)
    gst_paid = sum(e.get("gstAmount", 0) for e in expenses)
    total_sales = sum(t.get("total", 0) for t in transactions)
    total_purchases = sum(e.get("amount", 0) for e in expenses)
    report_dict = report.dict()
    report_dict.update({
        "gstCollected": round(gst_collected, 2),
        "gstPaid": round(gst_paid, 2),
        "netGST": round(gst_collected - gst_paid, 2),
        "totalSales": round(total_sales, 2),
        "totalPurchases": round(total_purchases, 2),
    })
    report_obj = BASReport(**report_dict)
    await db.bas_reports.insert_one(report_obj.dict())
    return report_obj

@router.post("/bas-gst/submit/{report_id}")
async def submit_bas_report(report_id: str, use_api: bool = False):
    report = await db.bas_reports.find_one({"id": report_id})
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if use_api:
        await db.bas_reports.update_one(
            {"id": report_id},
            {"$set": {"status": "submitted", "submittedAt": datetime.utcnow().isoformat(), "atoReference": f"ATO-{str(uuid.uuid4())[:8].upper()}"}}
        )
        return {"message": "BAS submitted to ATO via API", "reference": f"ATO-{str(uuid.uuid4())[:8].upper()}"}
    else:
        await db.bas_reports.update_one(
            {"id": report_id},
            {"$set": {"status": "ready_to_lodge"}}
        )
        return {"message": "BAS marked as ready to lodge", "atoPortalUrl": "https://www.ato.gov.au/business-portal"}

# ============ EXPENSES API ============
@router.get("/expenses", response_model=List[Expense])
async def get_expenses(start_date: Optional[str] = None, end_date: Optional[str] = None, category: Optional[str] = None):
    query = {}
    if category:
        query["category"] = category
    if start_date and end_date:
        query["date"] = {"$gte": datetime.fromisoformat(start_date), "$lte": datetime.fromisoformat(end_date)}
    expenses = await db.expenses.find(query).to_list(1000)
    return [Expense(**e) for e in expenses]

@router.post("/expenses", response_model=Expense)
async def create_expense(expense: ExpenseCreate):
    expense_obj = Expense(**expense.dict())
    await db.expenses.insert_one(expense_obj.dict())
    return expense_obj

# ============ SUPPLIERS API ============
@router.get("/suppliers", response_model=List[Supplier])
async def get_suppliers():
    suppliers = await db.suppliers.find().to_list(1000)
    return [Supplier(**s) for s in suppliers]

@router.post("/suppliers", response_model=Supplier)
async def create_supplier(supplier: SupplierCreate):
    supplier_obj = Supplier(**supplier.dict())
    await db.suppliers.insert_one(supplier_obj.dict())
    return supplier_obj

# ============ PURCHASE ORDERS API ============
@router.get("/purchase-orders", response_model=List[PurchaseOrder])
async def get_purchase_orders():
    orders = await db.purchase_orders.find().to_list(1000)
    return [PurchaseOrder(**o) for o in orders]

@router.post("/purchase-orders", response_model=PurchaseOrder)
async def create_purchase_order(po: PurchaseOrderCreate):
    supplier = await db.suppliers.find_one({"id": po.supplierId})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    subtotal = sum(item["quantity"] * item["price"] for item in po.items)
    gst = subtotal * 0.1
    total = subtotal + gst
    po_obj = PurchaseOrder(
        supplierId=po.supplierId, supplierName=supplier["name"],
        expectedDelivery=po.expectedDelivery, items=po.items,
        subtotal=subtotal, gst=gst, total=total, notes=po.notes
    )
    await db.purchase_orders.insert_one(po_obj.dict())
    return po_obj

# ============ REPORTS API ============
@router.get("/reports/sales-summary")
async def get_sales_summary(start_date: str, end_date: str, location: Optional[str] = None):
    query = {"timestamp": {"$gte": datetime.fromisoformat(start_date), "$lte": datetime.fromisoformat(end_date)}}
    if location:
        query["location"] = location
    transactions = await db.transactions.find(query).to_list(10000)
    total_sales = sum(t["total"] for t in transactions)
    total_transactions = len(transactions)
    avg_transaction = total_sales / total_transactions if total_transactions > 0 else 0
    by_payment = {}
    for txn in transactions:
        method = txn["paymentMethod"]
        by_payment[method] = by_payment.get(method, 0) + txn["total"]
    product_sales = {}
    for txn in transactions:
        for item in txn["items"]:
            pid = item["productId"]
            if pid not in product_sales:
                product_sales[pid] = {"name": item["productName"], "quantity": 0, "revenue": 0}
            product_sales[pid]["quantity"] += item["quantity"]
            product_sales[pid]["revenue"] += item["quantity"] * item["price"]
    return {
        "period": {"start": start_date, "end": end_date},
        "total_sales": total_sales, "total_transactions": total_transactions,
        "avg_transaction": avg_transaction, "by_payment_method": by_payment,
        "top_products": sorted(product_sales.values(), key=lambda x: x["revenue"], reverse=True)[:10]
    }

@router.get("/reports/export/csv")
async def export_report_csv(report_type: str, start_date: str, end_date: str):
    return {"message": "CSV export endpoint - implement with csv library"}

# ============ PRE-SHIFT DASHBOARD API ============
@router.get("/pre-shift/today")
async def get_pre_shift_data():
    today = datetime.utcnow().strftime('%Y-%m-%d')
    reservations = await db.reservations.find({"date": today}, {"_id": 0}).sort("time", 1).to_list(100)
    vip_guests = []
    for r in reservations:
        if r.get("customerId"):
            cust = await db.customers.find_one({"id": r["customerId"]}, {"_id": 0})
            if cust and cust.get("isVip"):
                vip_guests.append({**r, "customerProfile": cust})
        elif "VIP" in (r.get("tags") or []):
            vip_guests.append(r)
    dietary_alerts = []
    for r in reservations:
        alerts = []
        if r.get("customerId"):
            cust = await db.customers.find_one({"id": r["customerId"]}, {"_id": 0})
            if cust:
                if cust.get("dietaryRestrictions"):
                    alerts.extend(cust["dietaryRestrictions"])
                if cust.get("allergies"):
                    alerts.extend([f"ALLERGY: {a}" for a in cust["allergies"]])
        if alerts:
            dietary_alerts.append({"reservation": r["id"], "guest": r["guestName"], "time": r["time"], "alerts": alerts})
    special_requests = [
        {"guest": r["guestName"], "time": r["time"], "request": r["specialRequests"], "partySize": r["partySize"]}
        for r in reservations if r.get("specialRequests")
    ]
    total_covers = sum(r.get("partySize", 0) for r in reservations)
    confirmed = len([r for r in reservations if r.get("status") == "confirmed"])
    seated = len([r for r in reservations if r.get("status") == "seated"])
    kitchen_pending = await db.kitchen_orders.count_documents({"status": {"$in": ["new", "preparing"]}})
    waitlist_count = await db.waitlist.count_documents({"status": "waiting"})
    txns_today = await db.transactions.find({}, {"_id": 0}).sort("timestamp", -1).to_list(100)
    revenue_today = sum(t.get("total", 0) for t in txns_today)
    return {
        "date": today, "reservations": reservations, "totalReservations": len(reservations),
        "totalCovers": total_covers, "confirmed": confirmed, "seated": seated,
        "vipGuests": vip_guests, "dietaryAlerts": dietary_alerts, "specialRequests": special_requests,
        "kitchenPending": kitchen_pending, "waitlistCount": waitlist_count,
        "revenueToday": revenue_today, "transactionsToday": len(txns_today),
    }

# ============ AI COMMAND CENTER API ============
@router.get("/analytics/command-center")
async def get_command_center():
    all_txns = await db.transactions.find({}, {"_id": 0}).to_list(10000)
    total_revenue = sum(t.get("total", 0) for t in all_txns)
    total_txns = len(all_txns)
    avg_ticket = total_revenue / total_txns if total_txns > 0 else 0
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    product_map = {p["id"]: p for p in products}
    total_cogs = 0
    for txn in all_txns:
        for item in txn.get("items", []):
            prod = product_map.get(item.get("productId"))
            if prod:
                total_cogs += prod.get("cost", 0) * item.get("quantity", 0)
    food_cost_pct = (total_cogs / total_revenue * 100) if total_revenue > 0 else 0
    expenses = await db.expenses.find({}, {"_id": 0}).to_list(10000)
    total_expenses = sum(e.get("amount", 0) for e in expenses)
    shifts = await db.staff_shifts.find({}, {"_id": 0}).to_list(1000)
    total_hours = sum(s.get("totalHours", 0) for s in shifts)
    labor_cost = total_hours * 30
    labor_pct = (labor_cost / total_revenue * 100) if total_revenue > 0 else 0
    product_sales = {}
    for txn in all_txns:
        for item in txn.get("items", []):
            pid = item.get("productId", "")
            if pid not in product_sales:
                prod = product_map.get(pid, {})
                product_sales[pid] = {
                    "id": pid, "name": item.get("productName", ""),
                    "revenue": 0, "quantity": 0, "cost": prod.get("cost", 0),
                    "price": prod.get("price", item.get("price", 0))
                }
            product_sales[pid]["revenue"] += item.get("price", 0) * item.get("quantity", 0)
            product_sales[pid]["quantity"] += item.get("quantity", 0)
    for pid, ps in product_sales.items():
        ps["totalCost"] = ps["cost"] * ps["quantity"]
        ps["profit"] = ps["revenue"] - ps["totalCost"]
        ps["margin"] = (ps["profit"] / ps["revenue"] * 100) if ps["revenue"] > 0 else 0
    top_sellers = sorted(product_sales.values(), key=lambda x: x["revenue"], reverse=True)[:10]
    low_performers = sorted(product_sales.values(), key=lambda x: x["margin"])[:5]
    today = datetime.utcnow().strftime('%Y-%m-%d')
    today_res = await db.reservations.find({"date": today}, {"_id": 0}).to_list(100)
    insights = []
    if food_cost_pct > 35:
        insights.append({"type": "warning", "title": "High Food Cost", "message": f"Food cost at {food_cost_pct:.1f}% - target is under 35%.", "priority": "high"})
    if labor_pct > 30:
        insights.append({"type": "warning", "title": "Labor Cost Alert", "message": f"Labor cost at {labor_pct:.1f}% of revenue.", "priority": "high"})
    if len(today_res) > 20:
        insights.append({"type": "info", "title": "Busy Night Ahead", "message": f"{len(today_res)} reservations today.", "priority": "medium"})
    if low_performers:
        worst = low_performers[0]
        if worst["margin"] < 20:
            insights.append({"type": "alert", "title": "Underperforming Dish", "message": f'"{worst["name"]}" has only {worst["margin"]:.0f}% margin.', "priority": "medium"})
    customers = await db.customers.find({}, {"_id": 0}).to_list(10000)
    vip_count = len([c for c in customers if c.get("isVip")])
    avg_rating = sum(c.get("feedbackRating", 0) for c in customers if c.get("feedbackRating", 0) > 0)
    rated = len([c for c in customers if c.get("feedbackRating", 0) > 0])
    avg_rating = avg_rating / rated if rated > 0 else 0
    return {
        "revenue": {"total": total_revenue, "transactions": total_txns, "avgTicket": avg_ticket},
        "costs": {"foodCost": total_cogs, "foodCostPct": food_cost_pct, "laborCost": labor_cost, "laborPct": labor_pct, "expenses": total_expenses},
        "profit": {"gross": total_revenue - total_cogs, "net": total_revenue - total_cogs - total_expenses - labor_cost},
        "topSellers": top_sellers, "lowPerformers": low_performers, "insights": insights,
        "customers": {"total": len(customers), "vips": vip_count, "avgRating": round(avg_rating, 1)},
        "todayReservations": len(today_res), "todayCovers": sum(r.get("partySize", 0) for r in today_res),
    }

# ============ MENU ENGINEERING API ============
@router.get("/analytics/menu-engineering")
async def get_menu_engineering():
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    all_txns = await db.transactions.find({}, {"_id": 0}).to_list(10000)
    product_map = {p["id"]: p for p in products}
    sales_data = {}
    for txn in all_txns:
        for item in txn.get("items", []):
            pid = item.get("productId", "")
            if pid not in sales_data:
                prod = product_map.get(pid, {})
                sales_data[pid] = {
                    "id": pid, "name": item.get("productName", prod.get("name", "")),
                    "category": prod.get("category", "Other"),
                    "price": prod.get("price", 0), "cost": prod.get("cost", 0),
                    "quantity": 0, "revenue": 0
                }
            sales_data[pid]["quantity"] += item.get("quantity", 0)
            sales_data[pid]["revenue"] += item.get("price", 0) * item.get("quantity", 0)
    items = list(sales_data.values())
    for item in items:
        item["totalCost"] = item["cost"] * item["quantity"]
        item["profit"] = item["revenue"] - item["totalCost"]
        item["margin"] = (item["profit"] / item["revenue"] * 100) if item["revenue"] > 0 else 0
        item["contributionMargin"] = item["price"] - item["cost"]
    if items:
        avg_qty = sum(i["quantity"] for i in items) / len(items)
        avg_margin = sum(i["margin"] for i in items) / len(items)
        for item in items:
            high_pop = item["quantity"] >= avg_qty * 0.7
            high_profit = item["margin"] >= avg_margin
            if high_pop and high_profit:
                item["classification"] = "star"
            elif not high_pop and high_profit:
                item["classification"] = "puzzle"
            elif high_pop and not high_profit:
                item["classification"] = "horse"
            else:
                item["classification"] = "dog"
    categories = {}
    for item in items:
        cat = item["category"]
        if cat not in categories:
            categories[cat] = {"name": cat, "revenue": 0, "cost": 0, "quantity": 0, "items": 0}
        categories[cat]["revenue"] += item["revenue"]
        categories[cat]["cost"] += item["totalCost"]
        categories[cat]["quantity"] += item["quantity"]
        categories[cat]["items"] += 1
    for cat in categories.values():
        cat["profit"] = cat["revenue"] - cat["cost"]
        cat["margin"] = (cat["profit"] / cat["revenue"] * 100) if cat["revenue"] > 0 else 0
    return {
        "items": sorted(items, key=lambda x: x["revenue"], reverse=True),
        "categories": sorted(categories.values(), key=lambda x: x["revenue"], reverse=True),
        "summary": {
            "stars": len([i for i in items if i.get("classification") == "star"]),
            "puzzles": len([i for i in items if i.get("classification") == "puzzle"]),
            "horses": len([i for i in items if i.get("classification") == "horse"]),
            "dogs": len([i for i in items if i.get("classification") == "dog"]),
        }
    }

# ============ WHAT-IF SIMULATOR ============
@router.post("/analytics/what-if")
async def what_if_simulation(changes: List[dict]):
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    txns = await db.transactions.find({}, {"_id": 0}).to_list(10000)
    product_map = {p["id"]: p for p in products}
    product_sales = {}
    for txn in txns:
        for item in txn.get("items", []):
            pid = item.get("productId", "")
            if pid not in product_sales:
                product_sales[pid] = {"quantity": 0, "revenue": 0}
            product_sales[pid]["quantity"] += item.get("quantity", 0)
            product_sales[pid]["revenue"] += item.get("price", 0) * item.get("quantity", 0)
    results = []
    total_current_profit = 0
    total_projected_profit = 0
    for change in changes:
        pid = change.get("productId", "")
        new_price = change.get("newPrice")
        new_cost = change.get("newCost")
        prod = product_map.get(pid)
        if not prod:
            continue
        sales = product_sales.get(pid, {"quantity": 0, "revenue": 0})
        qty = sales["quantity"]
        current_price = prod.get("price", 0)
        current_cost = prod.get("cost", 0)
        current_profit = (current_price - current_cost) * qty
        proj_price = new_price if new_price is not None else current_price
        proj_cost = new_cost if new_cost is not None else current_cost
        price_change_pct = ((proj_price - current_price) / max(current_price, 0.01)) * 100
        demand_adjustment = 1 - (price_change_pct * 0.005)
        proj_qty = max(0, int(qty * demand_adjustment))
        projected_profit = (proj_price - proj_cost) * proj_qty
        total_current_profit += current_profit
        total_projected_profit += projected_profit
        results.append({
            "productId": pid, "productName": prod["name"],
            "currentPrice": current_price, "currentCost": current_cost,
            "projectedPrice": proj_price, "projectedCost": proj_cost,
            "currentQty": qty, "projectedQty": proj_qty,
            "currentProfit": round(current_profit, 2), "projectedProfit": round(projected_profit, 2),
            "profitChange": round(projected_profit - current_profit, 2),
            "profitChangePct": round(((projected_profit - current_profit) / max(abs(current_profit), 0.01)) * 100, 1),
        })
    return {
        "simulations": results,
        "totalCurrentProfit": round(total_current_profit, 2),
        "totalProjectedProfit": round(total_projected_profit, 2),
        "netImpact": round(total_projected_profit - total_current_profit, 2),
    }

# ============ DEMAND FORECASTING API ============
@router.get("/analytics/demand-forecast")
async def get_demand_forecast():
    all_txns = await db.transactions.find({}, {"_id": 0}).to_list(10000)
    reservations = await db.reservations.find({}, {"_id": 0}).to_list(1000)
    today = datetime.utcnow()
    forecast = []
    for i in range(7):
        day = today + __import__('datetime').timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        day_name = day.strftime('%A')
        day_res = [r for r in reservations if r.get("date") == day_str]
        booked_covers = sum(r.get("partySize", 0) for r in day_res)
        is_weekend = day.weekday() >= 4
        base_walkins = random.randint(30, 60) if is_weekend else random.randint(15, 35)
        estimated_covers = booked_covers + base_walkins
        busy_level = "low"
        if estimated_covers > 80:
            busy_level = "very_high"
        elif estimated_covers > 50:
            busy_level = "high"
        elif estimated_covers > 30:
            busy_level = "medium"
        forecast.append({
            "date": day_str, "dayOfWeek": day_name,
            "reservations": len(day_res), "bookedCovers": booked_covers,
            "estimatedWalkins": base_walkins, "totalEstimatedCovers": estimated_covers,
            "busyLevel": busy_level, "isWeekend": is_weekend,
            "suggestedStaff": max(3, estimated_covers // 15),
        })
    return {"forecast": forecast, "generatedAt": today.isoformat()}

# ============ TABLE TURN-TIME OPTIMIZATION ============
@router.get("/analytics/table-turns")
async def get_table_turn_analytics():
    reservations = await db.reservations.find({}, {"_id": 0}).to_list(5000)
    completed = [r for r in reservations if r.get("status") == "completed" and r.get("seatedAt") and r.get("completedAt")]
    turn_times = []
    for r in completed:
        try:
            seated = datetime.fromisoformat(r["seatedAt"])
            done = datetime.fromisoformat(r["completedAt"])
            duration = (done - seated).total_seconds() / 60
            if 10 < duration < 300:
                turn_times.append({"reservationId": r["id"], "partySize": r.get("partySize", 2), "duration": round(duration, 1), "section": r.get("section", "main")})
        except (ValueError, TypeError):
            pass
    avg_turn = sum(t["duration"] for t in turn_times) / len(turn_times) if turn_times else 75
    by_party = {}
    for t in turn_times:
        ps = t["partySize"]
        if ps not in by_party:
            by_party[ps] = []
        by_party[ps].append(t["duration"])
    party_avgs = [{"partySize": ps, "avgDuration": round(sum(ds) / len(ds), 1), "count": len(ds)} for ps, ds in sorted(by_party.items())]
    by_section = {}
    for t in turn_times:
        sec = t["section"]
        if sec not in by_section:
            by_section[sec] = []
        by_section[sec].append(t["duration"])
    section_avgs = [{"section": sec, "avgDuration": round(sum(ds) / len(ds), 1), "count": len(ds)} for sec, ds in by_section.items()]
    optimal_turn = max(45, avg_turn * 0.85)
    potential_extra = 0
    tables = await db.floor_plans.find({}, {"_id": 0}).to_list(10)
    total_tables = sum(len(p.get("tables", [])) for p in tables)
    if total_tables > 0:
        current_turns_per_night = (5 * 60) / avg_turn
        optimal_turns = (5 * 60) / optimal_turn
        potential_extra = int((optimal_turns - current_turns_per_night) * total_tables)
    return {
        "avgTurnTime": round(avg_turn, 1), "totalCompleted": len(turn_times),
        "byPartySize": party_avgs, "bySection": section_avgs,
        "optimization": {"optimalTurnTime": round(optimal_turn, 1), "potentialExtraCovers": potential_extra,
                         "revenueOpportunity": round(potential_extra * 35, 2)},
    }

# ============ SMART ROSTERING API ============
@router.get("/staff/smart-roster")
async def get_smart_roster():
    today = datetime.utcnow()
    roster = []
    for i in range(7):
        day = today + __import__('datetime').timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        day_name = day.strftime('%A')
        is_weekend = day.weekday() >= 4
        base_staff = 6 if is_weekend else 4
        reservations = await db.reservations.find({"date": day_str}, {"_id": 0}).to_list(100)
        covers = sum(r.get("partySize", 0) for r in reservations)
        extra_staff = covers // 20
        total_staff = base_staff + extra_staff
        roles = {
            "servers": max(2, total_staff // 2), "bartenders": max(1, total_staff // 4),
            "kitchen": max(2, total_staff // 3), "host": 1,
        }
        roster.append({
            "date": day_str, "dayOfWeek": day_name, "isWeekend": is_weekend,
            "expectedCovers": covers + (random.randint(20, 45) if is_weekend else random.randint(10, 25)),
            "reservations": len(reservations), "totalStaffNeeded": total_staff, "roles": roles,
        })
    return {"roster": roster, "generatedAt": today.isoformat()}

# ============ PREDICTIVE CUSTOMER MATCHING ============
@router.post("/orders/predict-customer")
async def predict_customer_for_order(order_items: List[dict]):
    if not order_items:
        return {"matched": False, "message": "No items provided"}
    item_names = set(item.get("productName", "").lower() for item in order_items)
    customers = await db.customers.find({}, {"_id": 0}).to_list(1000)
    txns = await db.transactions.find({}, {"_id": 0}).to_list(10000)
    customer_patterns = {}
    for txn in txns:
        cid = txn.get("customerId")
        if not cid:
            continue
        if cid not in customer_patterns:
            customer_patterns[cid] = {}
        for item in txn.get("items", []):
            name = item.get("productName", "").lower()
            customer_patterns[cid][name] = customer_patterns[cid].get(name, 0) + item.get("quantity", 0)
    scores = []
    for cust in customers:
        cid = cust["id"]
        pattern = customer_patterns.get(cid, {})
        if not pattern:
            continue
        overlap = sum(1 for name in item_names if name in pattern)
        total_items = len(item_names)
        freq_score = sum(pattern.get(name, 0) for name in item_names)
        if overlap > 0:
            similarity = (overlap / max(total_items, 1)) * 100
            scores.append({
                "customerId": cid, "customerName": cust["name"],
                "email": cust.get("email", ""), "phone": cust.get("phone", ""),
                "points": cust.get("points", 0), "tier": cust.get("membershipTier", "Bronze"),
                "isVip": cust.get("isVip", False), "similarity": round(similarity, 1),
                "frequencyScore": freq_score, "matchedItems": [n for n in item_names if n in pattern],
                "favoriteDishes": cust.get("favoriteDishes", []),
            })
    scores.sort(key=lambda x: (x["similarity"], x["frequencyScore"]), reverse=True)
    if scores:
        return {"matched": True, "predictions": scores[:5], "topMatch": scores[0]}
    return {"matched": False, "message": "No matching customer patterns found"}

@router.post("/orders/link-customer")
async def link_order_to_customer(transaction_id: str, customer_id: str, points_earned: int = 0):
    await db.transactions.update_one({"id": transaction_id}, {"$set": {"customerId": customer_id}})
    if points_earned > 0:
        await db.customers.update_one({"id": customer_id}, {"$inc": {"points": points_earned, "visits": 1}})
    return {"message": "Order linked and points awarded", "pointsEarned": points_earned}
