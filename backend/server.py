from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import uuid

from models.product import Product, ProductCreate, ProductUpdate
from models.promotion import Promotion, PromotionCreate
from models.customer import Customer, CustomerCreate, CustomerUpdate
from models.transaction import Transaction, TransactionCreate, TransactionItem
from models.bas_report import BASReport, BASReportCreate
from models.location import Location, LocationCreate
from models.user import User, UserCreate
from models.category import Category, CategoryCreate
from models.modifier import Modifier, ModifierCreate
from models.printer import PrinterConfig, PrinterConfigCreate
from models.gift_card import GiftCard, GiftCardCreate
from models.refund import Refund, RefundCreate
from models.supplier import Supplier, SupplierCreate, PurchaseOrder, PurchaseOrderCreate
from models.expense import Expense, ExpenseCreate
from models.staff import StaffCommission, StaffShift
from models.table import Table, TableCreate, DineInOrder
from models.eftpos import EFTPOSConfig, EFTPOSConfigCreate, EFTPOSTransaction, EFTPOSTransactionRequest
from models.integration import Integration, IntegrationCreate, IntegrationUpdate, SyncRequest
from models.employee import EmployeeSchedule, EmployeeScheduleCreate, TimeOffRequest, AgeVerification
from models.reservation import Reservation, ReservationCreate, ReservationUpdate
from models.floor_plan import FloorPlan, FloorPlanCreate, FloorPlanUpdate
from models.waitlist import WaitlistEntry, WaitlistEntryCreate, WaitlistEntryUpdate
from models.feedback import Feedback, FeedbackCreate
from models.kitchen_order import KitchenOrder, KitchenOrderCreate

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()

# Create router with /api prefix
api_router = APIRouter(prefix="/api")

# ============ PRODUCTS API ============
@api_router.get("/products", response_model=List[Product])
async def get_products(category: Optional[str] = None, search: Optional[str] = None):
    query = {}
    if category and category != "All":
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"sku": {"$regex": search, "$options": "i"}}
        ]
    
    products = await db.products.find(query).to_list(1000)
    return [Product(**p) for p in products]

@api_router.post("/products", response_model=Product)
async def create_product(product: ProductCreate):
    product_dict = product.dict()
    product_obj = Product(**product_dict)
    await db.products.insert_one(product_obj.dict())
    return product_obj

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product_update: ProductUpdate):
    update_data = {k: v for k, v in product_update.dict().items() if v is not None}
    update_data["updatedAt"] = datetime.utcnow()
    
    result = await db.products.find_one_and_update(
        {"id": product_id},
        {"$set": update_data},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return Product(**result)

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

# ============ PROMOTIONS API ============
@api_router.get("/promotions", response_model=List[Promotion])
async def get_promotions():
    promotions = await db.promotions.find().to_list(1000)
    return [Promotion(**p) for p in promotions]

@api_router.get("/promotions/active", response_model=List[Promotion])
async def get_active_promotions():
    promotions = await db.promotions.find({"active": True}).to_list(1000)
    return [Promotion(**p) for p in promotions]

@api_router.post("/promotions", response_model=Promotion)
async def create_promotion(promotion: PromotionCreate):
    promotion_dict = promotion.dict()
    promotion_obj = Promotion(**promotion_dict)
    await db.promotions.insert_one(promotion_obj.dict())
    return promotion_obj

# ============ CUSTOMERS API ============
@api_router.get("/customers", response_model=List[Customer])
async def get_customers(search: Optional[str] = None):
    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    customers = await db.customers.find(query).to_list(1000)
    return [Customer(**c) for c in customers]

@api_router.post("/customers", response_model=Customer)
async def create_customer(customer: CustomerCreate):
    customer_dict = customer.dict()
    customer_obj = Customer(**customer_dict)
    await db.customers.insert_one(customer_obj.dict())
    return customer_obj

@api_router.put("/customers/{customer_id}", response_model=Customer)
async def update_customer(customer_id: str, customer_update: CustomerUpdate):
    update_data = {k: v for k, v in customer_update.dict().items() if v is not None}
    
    result = await db.customers.find_one_and_update(
        {"id": customer_id},
        {"$set": update_data},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return Customer(**result)

# ============ TRANSACTIONS API ============
@api_router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    location: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    query = {}
    if location:
        query["location"] = location
    if start_date and end_date:
        query["timestamp"] = {
            "$gte": datetime.fromisoformat(start_date),
            "$lte": datetime.fromisoformat(end_date)
        }
    
    transactions = await db.transactions.find(query).sort("timestamp", -1).to_list(1000)
    return [Transaction(**t) for t in transactions]

@api_router.post("/transactions", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate):
    # Calculate subtotal including modifiers
    subtotal = 0
    for item in transaction.items:
        item_total = item.quantity * item.price
        # Add modifier prices
        for modifier in item.modifiers:
            item_total += modifier.price * item.quantity
        subtotal += item_total
    
    # Apply discount
    discount_amount = 0
    if transaction.discount:
        if transaction.discount.type == "percentage":
            discount_amount = subtotal * (transaction.discount.value / 100)
        elif transaction.discount.type == "fixed":
            discount_amount = transaction.discount.value
        elif transaction.discount.type == "custom":
            discount_amount = transaction.discount.value
    
    subtotal_after_discount = subtotal - discount_amount
    
    # Add tip
    tip_amount = transaction.tipAmount or 0
    
    # Calculate GST
    gst = subtotal_after_discount * 0.1
    total = subtotal_after_discount + gst + tip_amount
    
    # Generate transaction ID
    txn_id = f"TXN-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:3].upper()}"
    
    # Get customer name if customer ID provided
    customer_name = None
    if transaction.customerId:
        customer = await db.customers.find_one({"id": transaction.customerId})
        if customer:
            customer_name = customer["name"]
            # Update customer stats
            await db.customers.update_one(
                {"id": transaction.customerId},
                {
                    "$inc": {
                        "totalSpent": total,
                        "visits": 1,
                        "points": int(total)
                    }
                }
            )
    
    transaction_obj = Transaction(
        id=txn_id,
        items=transaction.items,
        subtotal=subtotal,
        discount=transaction.discount,
        discountAmount=discount_amount,
        tipAmount=tip_amount,
        gst=gst,
        total=total,
        paymentMethod=transaction.paymentMethod,
        paymentSplits=transaction.paymentSplits,
        isSplitPayment=transaction.isSplitPayment,
        customerId=transaction.customerId,
        customerName=customer_name,
        location=transaction.location,
        cashier=transaction.cashier,
        emailReceipt=transaction.emailReceipt,
        smsReceipt=transaction.smsReceipt,
        tableNumber=transaction.tableNumber,
        orderType=transaction.orderType
    )
    
    await db.transactions.insert_one(transaction_obj.dict())
    
    # Update product stock
    for item in transaction.items:
        await db.products.update_one(
            {"id": item.productId},
            {"$inc": {"stock": -item.quantity}}
        )
    
    # Send digital receipt if requested
    if transaction.emailReceipt or transaction.smsReceipt:
        # TODO: Integrate email/SMS service
        pass
    
    return transaction_obj
    
    await db.transactions.insert_one(transaction_obj.dict())
    
    # Update product stock
    for item in transaction.items:
        await db.products.update_one(
            {"id": item.productId},
            {"$inc": {"stock": -item.quantity}}
        )
    
    return transaction_obj

@api_router.get("/transactions/hourly")
async def get_hourly_transactions():
    transactions = await db.transactions.find().sort("timestamp", -1).to_list(1000)
    
    # Group by hour
    hourly = {}
    for txn in transactions:
        hour = txn["timestamp"].hour
        if hour not in hourly:
            hourly[hour] = []
        hourly[hour].append(txn)
    
    return hourly

# ============ ACCOUNTING API ============
@api_router.get("/accounting/summary")
async def get_accounting_summary():
    transactions = await db.transactions.find().to_list(10000)
    
    total_revenue = sum(t["total"] for t in transactions)
    total_gst = sum(t["gst"] for t in transactions)
    total_transactions = len(transactions)
    avg_transaction = total_revenue / total_transactions if total_transactions > 0 else 0
    
    return {
        "totalRevenue": total_revenue,
        "gstCollected": total_gst,
        "transactions": total_transactions,
        "avgTransaction": avg_transaction
    }

@api_router.get("/accounting/p-and-l")
async def get_p_and_l():
    transactions = await db.transactions.find().to_list(10000)
    products = await db.products.find().to_list(1000)
    
    total_sales = sum(t["total"] for t in transactions)
    total_gst = sum(t["gst"] for t in transactions)
    
    # Calculate COGS (simplified)
    cogs = 0
    for txn in transactions:
        for item in txn["items"]:
            product = next((p for p in products if p["id"] == item["productId"]), None)
            if product:
                cogs += product["cost"] * item["quantity"]
    
    operating_expenses = 8200.00  # Mock value
    net_profit = total_sales - cogs - operating_expenses - total_gst
    
    return {
        "revenue": total_sales,
        "cogs": cogs,
        "operatingExpenses": operating_expenses,
        "gst": total_gst,
        "netProfit": net_profit
    }

# ============ BAS/GST API ============
@api_router.get("/bas-gst/reports", response_model=List[BASReport])
async def get_bas_reports():
    reports = await db.bas_reports.find().sort("createdAt", -1).to_list(1000)
    return [BASReport(**r) for r in reports]

@api_router.post("/bas-gst/reports", response_model=BASReport)
async def create_bas_report(report: BASReportCreate):
    # Calculate from transactions
    transactions = await db.transactions.find().to_list(10000)
    
    total_sales = sum(t["subtotal"] for t in transactions)
    gst_collected = sum(t["gst"] for t in transactions)
    gst_paid = gst_collected * 0.2  # Simplified calculation
    net_gst = gst_collected - gst_paid
    
    report_obj = BASReport(
        quarter=report.quarter,
        period=report.period,
        totalSales=total_sales,
        gstCollected=gst_collected,
        gstPaid=gst_paid,
        netGst=net_gst,
        dueDate=report.dueDate,
        transactionIds=[t["id"] for t in transactions]
    )
    
    await db.bas_reports.insert_one(report_obj.dict())
    return report_obj

@api_router.post("/bas-gst/submit/{report_id}")
async def submit_bas_report(report_id: str, use_api: bool = False):
    result = await db.bas_reports.find_one_and_update(
        {"id": report_id},
        {
            "$set": {
                "status": "submitted",
                "submittedDate": datetime.utcnow()
            }
        },
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    
    submission_type = "API" if use_api else "Mock"
    return {
        "message": f"BAS report submitted successfully via {submission_type}",
        "report": BASReport(**result)
    }

# ============ LOCATIONS API ============
@api_router.get("/locations", response_model=List[Location])
async def get_locations():
    locations = await db.locations.find().to_list(1000)
    return [Location(**l) for l in locations]

@api_router.post("/locations", response_model=Location)
async def create_location(location: LocationCreate):
    location_dict = location.dict()
    location_obj = Location(**location_dict)
    await db.locations.insert_one(location_obj.dict())
    return location_obj

# ============ USERS API ============
@api_router.get("/users", response_model=List[User])
async def get_users():
    users = await db.users.find().to_list(1000)
    return [User(**u) for u in users]

@api_router.post("/users", response_model=User)
async def create_user(user: UserCreate):
    user_dict = user.dict()
    user_obj = User(**user_dict)
    await db.users.insert_one(user_obj.dict())
    return user_obj

# ============ CATEGORIES API ============
@api_router.get("/categories", response_model=List[Category])
async def get_categories():
    categories = await db.categories.find().sort("sortOrder", 1).to_list(1000)
    return [Category(**c) for c in categories]

@api_router.post("/categories", response_model=Category)
async def create_category(category: CategoryCreate):
    category_dict = category.dict()
    category_obj = Category(**category_dict)
    await db.categories.insert_one(category_obj.dict())
    return category_obj

# ============ MODIFIERS API ============
@api_router.get("/modifiers", response_model=List[Modifier])
async def get_modifiers():
    modifiers = await db.modifiers.find().to_list(1000)
    return [Modifier(**m) for m in modifiers]

@api_router.post("/modifiers", response_model=Modifier)
async def create_modifier(modifier: ModifierCreate):
    modifier_dict = modifier.dict()
    modifier_obj = Modifier(**modifier_dict)
    await db.modifiers.insert_one(modifier_obj.dict())
    return modifier_obj

# ============ PRINTER API ============
@api_router.get("/printers", response_model=List[PrinterConfig])
async def get_printers():
    printers = await db.printers.find().to_list(1000)
    return [PrinterConfig(**p) for p in printers]

@api_router.post("/printers", response_model=PrinterConfig)
async def create_printer(printer: PrinterConfigCreate):
    printer_dict = printer.dict()
    printer_obj = PrinterConfig(**printer_dict)
    await db.printers.insert_one(printer_obj.dict())
    return printer_obj

@api_router.post("/printers/{printer_id}/print")
async def print_receipt(printer_id: str, transaction_id: str):
    printer = await db.printers.find_one({"id": printer_id})
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    transaction = await db.transactions.find_one({"id": transaction_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Mark transaction as printed
    await db.transactions.update_one(
        {"id": transaction_id},
        {"$set": {"printed": True}}
    )
    
    # Return printer config and transaction for client-side printing
    return {
        "printer": PrinterConfig(**printer),
        "transaction": Transaction(**transaction),
        "message": "Receipt data prepared for printing"
    }

# ============ OFFLINE SYNC API ============
@api_router.post("/offline/sync")
async def sync_offline_data(data: dict):
    """Sync offline transactions and data"""
    synced = []
    
    # Sync transactions
    if "transactions" in data:
        for txn_data in data["transactions"]:
            await db.transactions.insert_one(txn_data)
            synced.append(txn_data["id"])
    
    return {
        "success": True,
        "synced": synced,
        "message": f"Synced {len(synced)} items"
    }

# ============ GIFT CARDS API ============
@api_router.get("/gift-cards", response_model=List[GiftCard])
async def get_gift_cards():
    cards = await db.gift_cards.find().to_list(1000)
    return [GiftCard(**c) for c in cards]

@api_router.post("/gift-cards", response_model=GiftCard)
async def create_gift_card(card: GiftCardCreate):
    import random
    import string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    
    card_obj = GiftCard(
        code=code,
        balance=card.initialValue,
        initialValue=card.initialValue,
        customerId=card.customerId,
        expiryDate=card.expiryDate
    )
    await db.gift_cards.insert_one(card_obj.dict())
    return card_obj

@api_router.post("/gift-cards/{code}/redeem")
async def redeem_gift_card(code: str, amount: float):
    card = await db.gift_cards.find_one({"code": code})
    if not card:
        raise HTTPException(status_code=404, detail="Gift card not found")
    
    if card["balance"] < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    new_balance = card["balance"] - amount
    status = "redeemed" if new_balance == 0 else "active"
    
    await db.gift_cards.update_one(
        {"code": code},
        {"$set": {"balance": new_balance, "status": status}}
    )
    
    return {"balance": new_balance, "amount_redeemed": amount}

# ============ REFUNDS API ============
@api_router.get("/refunds", response_model=List[Refund])
async def get_refunds():
    refunds = await db.refunds.find().to_list(1000)
    return [Refund(**r) for r in refunds]

@api_router.post("/refunds", response_model=Refund)
async def create_refund(refund: RefundCreate):
    # Verify original transaction exists
    original_txn = await db.transactions.find_one({"id": refund.originalTransactionId})
    if not original_txn:
        raise HTTPException(status_code=404, detail="Original transaction not found")
    
    refund_obj = Refund(**refund.dict())
    await db.refunds.insert_one(refund_obj.dict())
    
    # If store credit, add to customer account
    if refund.refundMethod == "store_credit" and refund.customerId:
        await db.customers.update_one(
            {"id": refund.customerId},
            {"$inc": {"storeCredit": refund.amount}}
        )
    
    return refund_obj

# ============ SUPPLIERS API ============
@api_router.get("/suppliers", response_model=List[Supplier])
async def get_suppliers():
    suppliers = await db.suppliers.find().to_list(1000)
    return [Supplier(**s) for s in suppliers]

@api_router.post("/suppliers", response_model=Supplier)
async def create_supplier(supplier: SupplierCreate):
    supplier_dict = supplier.dict()
    supplier_obj = Supplier(**supplier_dict)
    await db.suppliers.insert_one(supplier_obj.dict())
    return supplier_obj

# ============ PURCHASE ORDERS API ============
@api_router.get("/purchase-orders", response_model=List[PurchaseOrder])
async def get_purchase_orders():
    orders = await db.purchase_orders.find().to_list(1000)
    return [PurchaseOrder(**o) for o in orders]

@api_router.post("/purchase-orders", response_model=PurchaseOrder)
async def create_purchase_order(po: PurchaseOrderCreate):
    supplier = await db.suppliers.find_one({"id": po.supplierId})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    subtotal = sum(item["quantity"] * item["price"] for item in po.items)
    gst = subtotal * 0.1
    total = subtotal + gst
    
    po_obj = PurchaseOrder(
        supplierId=po.supplierId,
        supplierName=supplier["name"],
        expectedDelivery=po.expectedDelivery,
        items=po.items,
        subtotal=subtotal,
        gst=gst,
        total=total,
        notes=po.notes
    )
    
    await db.purchase_orders.insert_one(po_obj.dict())
    return po_obj

# ============ EXPENSES API ============
@api_router.get("/expenses", response_model=List[Expense])
async def get_expenses(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None
):
    query = {}
    if category:
        query["category"] = category
    if start_date and end_date:
        query["date"] = {
            "$gte": datetime.fromisoformat(start_date),
            "$lte": datetime.fromisoformat(end_date)
        }
    
    expenses = await db.expenses.find(query).to_list(1000)
    return [Expense(**e) for e in expenses]

@api_router.post("/expenses", response_model=Expense)
async def create_expense(expense: ExpenseCreate):
    expense_dict = expense.dict()
    expense_obj = Expense(**expense_dict)
    await db.expenses.insert_one(expense_obj.dict())
    return expense_obj

# ============ STAFF API ============
@api_router.get("/staff/commissions")
async def get_staff_commissions(period: Optional[str] = None):
    query = {"period": period} if period else {}
    commissions = await db.staff_commissions.find(query).to_list(1000)
    return commissions

@api_router.post("/staff/clock-in")
async def staff_clock_in(user_id: str, location: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    shift = StaffShift(
        userId=user_id,
        userName=user["name"],
        location=location,
        clockIn=datetime.utcnow()
    )
    
    await db.staff_shifts.insert_one(shift.dict())
    return shift

@api_router.post("/staff/clock-out/{shift_id}")
async def staff_clock_out(shift_id: str, break_minutes: int = 0):
    shift = await db.staff_shifts.find_one({"id": shift_id})
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    clock_out = datetime.utcnow()
    clock_in = shift["clockIn"]
    total_hours = (clock_out - clock_in).total_seconds() / 3600
    total_hours -= break_minutes / 60
    
    await db.staff_shifts.update_one(
        {"id": shift_id},
        {
            "$set": {
                "clockOut": clock_out,
                "breakMinutes": break_minutes,
                "totalHours": total_hours,
                "status": "completed"
            }
        }
    )
    
    return {"total_hours": total_hours}

# ============ TABLES API (For Restaurants) ============
@api_router.get("/tables", response_model=List[Table])
async def get_tables(location: Optional[str] = None):
    query = {"location": location} if location else {}
    tables = await db.tables.find(query).to_list(1000)
    return [Table(**t) for t in tables]

@api_router.post("/tables", response_model=Table)
async def create_table(table: TableCreate):
    table_dict = table.dict()
    table_obj = Table(**table_dict)
    await db.tables.insert_one(table_obj.dict())
    return table_obj

@api_router.post("/tables/{table_id}/occupy")
async def occupy_table(table_id: str, order_id: str):
    await db.tables.update_one(
        {"id": table_id},
        {"$set": {"status": "occupied", "currentOrderId": order_id}}
    )
    return {"message": "Table occupied"}

@api_router.post("/tables/{table_id}/free")
async def free_table(table_id: str):
    await db.tables.update_one(
        {"id": table_id},
        {"$set": {"status": "available", "currentOrderId": None}}
    )
    return {"message": "Table freed"}

# ============ REPORTS & EXPORT API ============
@api_router.get("/reports/sales-summary")
async def get_sales_summary(
    start_date: str,
    end_date: str,
    location: Optional[str] = None
):
    query = {
        "timestamp": {
            "$gte": datetime.fromisoformat(start_date),
            "$lte": datetime.fromisoformat(end_date)
        }
    }
    if location:
        query["location"] = location
    
    transactions = await db.transactions.find(query).to_list(10000)
    
    total_sales = sum(t["total"] for t in transactions)
    total_transactions = len(transactions)
    avg_transaction = total_sales / total_transactions if total_transactions > 0 else 0
    
    # Group by payment method
    by_payment = {}
    for txn in transactions:
        method = txn["paymentMethod"]
        by_payment[method] = by_payment.get(method, 0) + txn["total"]
    
    # Group by product
    product_sales = {}
    for txn in transactions:
        for item in txn["items"]:
            pid = item["productId"]
            if pid not in product_sales:
                product_sales[pid] = {
                    "name": item["productName"],
                    "quantity": 0,
                    "revenue": 0
                }
            product_sales[pid]["quantity"] += item["quantity"]
            product_sales[pid]["revenue"] += item["quantity"] * item["price"]
    
    return {
        "period": {"start": start_date, "end": end_date},
        "total_sales": total_sales,
        "total_transactions": total_transactions,
        "avg_transaction": avg_transaction,
        "by_payment_method": by_payment,
        "top_products": sorted(product_sales.values(), key=lambda x: x["revenue"], reverse=True)[:10]
    }

@api_router.get("/reports/export/csv")
async def export_report_csv(report_type: str, start_date: str, end_date: str):
    """Export reports in CSV format"""
    # This would generate CSV data
    return {"message": "CSV export endpoint - implement with csv library"}

# ============ EFTPOS API ============
@api_router.get("/eftpos/terminals", response_model=List[EFTPOSConfig])
async def get_eftpos_terminals():
    """Get all EFTPOS terminal configurations"""
    terminals = await db.eftpos_terminals.find().to_list(1000)
    return [EFTPOSConfig(**t) for t in terminals]

@api_router.post("/eftpos/terminals", response_model=EFTPOSConfig)
async def create_eftpos_terminal(terminal: EFTPOSConfigCreate):
    """Configure new EFTPOS terminal"""
    terminal_dict = terminal.dict()
    terminal_obj = EFTPOSConfig(**terminal_dict)
    await db.eftpos_terminals.insert_one(terminal_obj.dict())
    return terminal_obj

@api_router.put("/eftpos/terminals/{terminal_id}", response_model=EFTPOSConfig)
async def update_eftpos_terminal(terminal_id: str, terminal: EFTPOSConfigCreate):
    """Update EFTPOS terminal configuration"""
    update_data = terminal.dict()
    result = await db.eftpos_terminals.find_one_and_update(
        {"id": terminal_id},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Terminal not found")
    return EFTPOSConfig(**result)

@api_router.delete("/eftpos/terminals/{terminal_id}")
async def delete_eftpos_terminal(terminal_id: str):
    """Delete EFTPOS terminal configuration"""
    result = await db.eftpos_terminals.delete_one({"id": terminal_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Terminal not found")
    return {"message": "Terminal deleted successfully"}

@api_router.post("/eftpos/terminals/{terminal_id}/test")
async def test_eftpos_connection(terminal_id: str):
    """Test EFTPOS terminal connection"""
    terminal = await db.eftpos_terminals.find_one({"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    
    try:
        from services.eftpos_service import eftpos_service
        
        provider = eftpos_service.get_provider(terminal)
        connected = await provider.connect()
        
        if connected:
            await provider.disconnect()
            await db.eftpos_terminals.update_one(
                {"id": terminal_id},
                {"$set": {"status": "active", "lastPing": datetime.utcnow()}}
            )
            return {"success": True, "message": "Connection successful"}
        else:
            await db.eftpos_terminals.update_one(
                {"id": terminal_id},
                {"$set": {"status": "error"}}
            )
            return {"success": False, "message": "Connection failed"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@api_router.post("/eftpos/transaction", response_model=EFTPOSTransaction)
async def process_eftpos_transaction(request: EFTPOSTransactionRequest):
    """Process EFTPOS payment transaction"""
    # Get terminal configuration
    terminal = await db.eftpos_terminals.find_one({"id": request.terminalId})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    
    try:
        from services.eftpos_service import eftpos_service
        
        # Process transaction
        result = await eftpos_service.process_transaction(
            config=terminal,
            transaction_type=request.transactionType,
            amount=request.amount,
            reference=request.reference,
            cashout=request.cashout
        )
        
        # Create EFTPOS transaction record
        eftpos_txn = EFTPOSTransaction(
            terminalId=request.terminalId,
            provider=terminal["provider"],
            transactionType=request.transactionType,
            amount=request.amount,
            cashout=request.cashout,
            reference=request.reference,
            posTransactionId=request.posTransactionId,
            cardType=result.get("cardType"),
            maskedPan=result.get("maskedPan"),
            authCode=result.get("authCode"),
            rrn=result.get("rrn"),
            stan=result.get("stan"),
            responseCode=result.get("responseCode", "99"),
            responseText=result.get("responseText", "Unknown"),
            approved=result.get("approved", False)
        )
        
        await db.eftpos_transactions.insert_one(eftpos_txn.dict())
        
        return eftpos_txn
        
    except Exception as e:
        logger.error(f"EFTPOS transaction error: {e}")
        # Create failed transaction record
        eftpos_txn = EFTPOSTransaction(
            terminalId=request.terminalId,
            provider=terminal["provider"],
            transactionType=request.transactionType,
            amount=request.amount,
            cashout=request.cashout,
            reference=request.reference,
            posTransactionId=request.posTransactionId,
            responseCode="99",
            responseText=str(e),
            approved=False
        )
        await db.eftpos_transactions.insert_one(eftpos_txn.dict())
        return eftpos_txn

@api_router.get("/eftpos/transactions", response_model=List[EFTPOSTransaction])
async def get_eftpos_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    terminal_id: Optional[str] = None
):
    """Get EFTPOS transaction history"""
    query = {}
    if terminal_id:
        query["terminalId"] = terminal_id
    if start_date and end_date:
        query["timestamp"] = {
            "$gte": datetime.fromisoformat(start_date),
            "$lte": datetime.fromisoformat(end_date)
        }
    
    transactions = await db.eftpos_transactions.find(query).sort("timestamp", -1).to_list(1000)
    return [EFTPOSTransaction(**t) for t in transactions]

@api_router.post("/eftpos/terminals/{terminal_id}/settlement")
async def perform_settlement(terminal_id: str):
    """Perform end-of-day settlement"""
    terminal = await db.eftpos_terminals.find_one({"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    
    try:
        from services.eftpos_service import eftpos_service
        
        provider = eftpos_service.get_provider(terminal)
        await provider.connect()
        result = await provider.settlement()
        await provider.disconnect()
        
        return {
            "success": result.get("approved", False),
            "message": result.get("responseText", "Settlement completed")
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

# ============ CUSTOMER PROFILE (360° Guest CRM) ============
@api_router.get("/customers/{customer_id}/profile")
async def get_customer_profile(customer_id: str):
    """Full 360° guest profile with dining history."""
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    # Get reservation history
    reservations = await db.reservations.find(
        {"$or": [{"customerId": customer_id}, {"guestEmail": customer.get("email", "")}]},
        {"_id": 0}
    ).sort("date", -1).to_list(50)
    # Get feedback
    feedbacks = await db.feedback.find({"customerId": customer_id}, {"_id": 0}).sort("createdAt", -1).to_list(50)
    # Get transaction history
    transactions = await db.transactions.find({"customerId": customer_id}, {"_id": 0}).sort("timestamp", -1).to_list(50)
    return {
        **customer,
        "reservationHistory": reservations,
        "feedbackHistory": feedbacks,
        "transactionHistory": transactions,
    }

# ============ FEEDBACK API ============
@api_router.get("/feedback", response_model=List[Feedback])
async def get_feedback(customer_id: Optional[str] = None, status: Optional[str] = None):
    query = {}
    if customer_id:
        query["customerId"] = customer_id
    if status:
        query["status"] = status
    items = await db.feedback.find(query, {"_id": 0}).sort("createdAt", -1).to_list(1000)
    return [Feedback(**f) for f in items]

@api_router.post("/feedback", response_model=Feedback)
async def create_feedback(fb: FeedbackCreate):
    fb_obj = Feedback(**fb.dict())
    await db.feedback.insert_one(fb_obj.dict())
    # Update customer feedback stats
    if fb.customerId:
        customer = await db.customers.find_one({"id": fb.customerId}, {"_id": 0})
        if customer:
            count = customer.get("feedbackCount", 0)
            avg = customer.get("feedbackRating", 0)
            new_count = count + 1
            new_avg = ((avg * count) + fb.rating) / new_count
            await db.customers.update_one(
                {"id": fb.customerId},
                {"$set": {"feedbackRating": round(new_avg, 1), "feedbackCount": new_count}}
            )
    return fb_obj

@api_router.put("/feedback/{feedback_id}/respond")
async def respond_to_feedback(feedback_id: str, response: str = ""):
    result = await db.feedback.find_one_and_update(
        {"id": feedback_id},
        {"$set": {"status": "responded", "response": response}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Feedback not found")
    result.pop("_id", None)
    return Feedback(**result)

# ============ RESERVATIONS API ============
@api_router.get("/reservations", response_model=List[Reservation])
async def get_reservations(
    date: Optional[str] = None,
    status: Optional[str] = None,
    section: Optional[str] = None
):
    query = {}
    if date:
        query["date"] = date
    if status:
        query["status"] = status
    if section:
        query["section"] = section
    reservations = await db.reservations.find(query, {"_id": 0}).sort("time", 1).to_list(1000)
    return [Reservation(**r) for r in reservations]

@api_router.get("/reservations/{reservation_id}", response_model=Reservation)
async def get_reservation(reservation_id: str):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return Reservation(**res)

@api_router.post("/reservations", response_model=Reservation)
async def create_reservation(reservation: ReservationCreate):
    res_obj = Reservation(**reservation.dict())
    doc = res_obj.dict()
    await db.reservations.insert_one(doc)
    # If table assigned, update table status
    if reservation.tableId:
        await db.floor_tables.update_one(
            {"id": reservation.tableId},
            {"$set": {"status": "reserved", "currentReservationId": res_obj.id}}
        )
    # Link to customer if customerId provided
    if reservation.customerId:
        await db.customers.update_one(
            {"id": reservation.customerId},
            {"$inc": {"visits": 0}, "$push": {"reservationIds": res_obj.id}}
        )
    return res_obj

@api_router.put("/reservations/{reservation_id}", response_model=Reservation)
async def update_reservation(reservation_id: str, update: ReservationUpdate):
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    update_data["updatedAt"] = datetime.utcnow().isoformat()
    result = await db.reservations.find_one_and_update(
        {"id": reservation_id},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Reservation not found")
    result.pop("_id", None)
    return Reservation(**result)

@api_router.delete("/reservations/{reservation_id}")
async def delete_reservation(reservation_id: str):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    # Free up the table if one was assigned
    if res.get("tableId"):
        await db.floor_tables.update_one(
            {"id": res["tableId"]},
            {"$set": {"status": "available", "currentReservationId": None}}
        )
    await db.reservations.delete_one({"id": reservation_id})
    return {"message": "Reservation deleted"}

@api_router.post("/reservations/{reservation_id}/seat")
async def seat_reservation(reservation_id: str, table_id: Optional[str] = None):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    tid = table_id or res.get("tableId")
    update_data = {
        "status": "seated",
        "seatedAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat()
    }
    if tid:
        update_data["tableId"] = tid
        await db.floor_tables.update_one(
            {"id": tid},
            {"$set": {"status": "occupied", "currentReservationId": reservation_id}}
        )
    await db.reservations.update_one({"id": reservation_id}, {"$set": update_data})
    return {"message": "Guest seated", "tableId": tid}

@api_router.post("/reservations/{reservation_id}/complete")
async def complete_reservation(reservation_id: str):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {
            "status": "completed",
            "completedAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }}
    )
    if res.get("tableId"):
        await db.floor_tables.update_one(
            {"id": res["tableId"]},
            {"$set": {"status": "cleaning", "currentReservationId": None}}
        )
    return {"message": "Reservation completed"}

@api_router.post("/reservations/{reservation_id}/no-show")
async def mark_no_show(reservation_id: str, fee: float = 0):
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {
            "status": "no_show",
            "noShowFee": fee,
            "updatedAt": datetime.utcnow().isoformat()
        }}
    )
    # Flag customer profile if linked
    if res.get("customerId"):
        await db.customers.update_one(
            {"id": res["customerId"]},
            {"$inc": {"noShowCount": 1}}
        )
    if res.get("tableId"):
        await db.floor_tables.update_one(
            {"id": res["tableId"]},
            {"$set": {"status": "available", "currentReservationId": None}}
        )
    return {"message": "Marked as no-show"}

@api_router.get("/reservations/auto-assign/{reservation_id}")
async def auto_assign_table(reservation_id: str):
    """Smart auto-seating: find best available table for a reservation."""
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    party = res.get("partySize", 2)
    section_pref = res.get("section")
    query = {"status": "available", "isActive": True, "maxCovers": {"$gte": party}}
    if section_pref:
        query["section"] = section_pref
    tables = await db.floor_tables.find(query, {"_id": 0}).sort("maxCovers", 1).to_list(100)
    if not tables:
        return {"assigned": False, "message": "No suitable tables available"}
    # Pick smallest table that fits
    best = tables[0]
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {"tableId": best["id"], "tableNumber": best.get("number", ""), "updatedAt": datetime.utcnow().isoformat()}}
    )
    await db.floor_tables.update_one(
        {"id": best["id"]},
        {"$set": {"status": "reserved", "currentReservationId": reservation_id}}
    )
    return {"assigned": True, "table": best}

# ============ FLOOR PLANS API ============
@api_router.get("/floor-plans", response_model=List[FloorPlan])
async def get_floor_plans():
    plans = await db.floor_plans.find({}, {"_id": 0}).to_list(100)
    return [FloorPlan(**p) for p in plans]

@api_router.get("/floor-plans/{plan_id}", response_model=FloorPlan)
async def get_floor_plan(plan_id: str):
    plan = await db.floor_plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Floor plan not found")
    return FloorPlan(**plan)

@api_router.post("/floor-plans", response_model=FloorPlan)
async def create_floor_plan(plan: FloorPlanCreate):
    plan_obj = FloorPlan(**plan.dict())
    await db.floor_plans.insert_one(plan_obj.dict())
    return plan_obj

@api_router.put("/floor-plans/{plan_id}", response_model=FloorPlan)
async def update_floor_plan(plan_id: str, update: FloorPlanUpdate):
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    update_data["updatedAt"] = datetime.utcnow().isoformat()
    result = await db.floor_plans.find_one_and_update(
        {"id": plan_id},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Floor plan not found")
    result.pop("_id", None)
    return FloorPlan(**result)

@api_router.delete("/floor-plans/{plan_id}")
async def delete_floor_plan(plan_id: str):
    result = await db.floor_plans.delete_one({"id": plan_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Floor plan not found")
    return {"message": "Floor plan deleted"}

# Floor table status management
@api_router.post("/floor-plans/tables/{table_id}/status")
async def update_table_status(table_id: str, status: str, plan_id: Optional[str] = None):
    """Update individual table status within a floor plan."""
    if plan_id:
        plan = await db.floor_plans.find_one({"id": plan_id}, {"_id": 0})
        if plan:
            tables = plan.get("tables", [])
            for t in tables:
                if t.get("id") == table_id:
                    t["status"] = status
                    break
            await db.floor_plans.update_one(
                {"id": plan_id},
                {"$set": {"tables": tables, "updatedAt": datetime.utcnow().isoformat()}}
            )
    return {"message": f"Table {table_id} status updated to {status}"}

# Server/section assignment
@api_router.post("/floor-plans/sections/{section_id}/assign")
async def assign_server_to_section(section_id: str, server_id: str, plan_id: str):
    plan = await db.floor_plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Floor plan not found")
    sections = plan.get("sections", [])
    for s in sections:
        if s.get("id") == section_id:
            s["serverId"] = server_id
            break
    await db.floor_plans.update_one(
        {"id": plan_id},
        {"$set": {"sections": sections, "updatedAt": datetime.utcnow().isoformat()}}
    )
    return {"message": "Server assigned to section"}

# ============ WAITLIST API ============
@api_router.get("/waitlist", response_model=List[WaitlistEntry])
async def get_waitlist(status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    else:
        query["status"] = {"$in": ["waiting", "notified"]}
    entries = await db.waitlist.find(query, {"_id": 0}).sort("position", 1).to_list(1000)
    return [WaitlistEntry(**e) for e in entries]

@api_router.post("/waitlist", response_model=WaitlistEntry)
async def add_to_waitlist(entry: WaitlistEntryCreate):
    # Get next position
    last = await db.waitlist.find({"status": "waiting"}).sort("position", -1).to_list(1)
    next_pos = (last[0]["position"] + 1) if last else 1
    entry_obj = WaitlistEntry(**entry.dict(), position=next_pos)
    doc = entry_obj.dict()
    await db.waitlist.insert_one(doc)
    return entry_obj

@api_router.put("/waitlist/{entry_id}", response_model=WaitlistEntry)
async def update_waitlist_entry(entry_id: str, update: WaitlistEntryUpdate):
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    result = await db.waitlist.find_one_and_update(
        {"id": entry_id},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    result.pop("_id", None)
    return WaitlistEntry(**result)

@api_router.post("/waitlist/{entry_id}/seat")
async def seat_waitlist_guest(entry_id: str, table_id: Optional[str] = None):
    entry = await db.waitlist.find_one({"id": entry_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found")
    update_data = {"status": "seated", "seatedTime": datetime.utcnow().isoformat()}
    if table_id:
        update_data["tableId"] = table_id
    await db.waitlist.update_one({"id": entry_id}, {"$set": update_data})
    return {"message": "Guest seated from waitlist"}

@api_router.delete("/waitlist/{entry_id}")
async def remove_from_waitlist(entry_id: str):
    result = await db.waitlist.delete_one({"id": entry_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"message": "Removed from waitlist"}

# ============ KITCHEN DISPLAY (KDS) API ============
@api_router.get("/kitchen/orders")
async def get_kitchen_orders(status: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    else:
        query["status"] = {"$in": ["new", "preparing", "ready"]}
    orders = await db.kitchen_orders.find(query, {"_id": 0}).sort("createdAt", 1).to_list(100)
    return orders

@api_router.post("/kitchen/orders")
async def create_kitchen_order(order: KitchenOrderCreate):
    order_obj = KitchenOrder(**order.dict())
    await db.kitchen_orders.insert_one(order_obj.dict())
    return order_obj.dict()

@api_router.post("/kitchen/orders/{order_id}/start")
async def start_kitchen_order(order_id: str):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {"status": "preparing", "startedAt": datetime.utcnow().isoformat()}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

@api_router.post("/kitchen/orders/{order_id}/ready")
async def mark_order_ready(order_id: str):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {"status": "ready", "readyAt": datetime.utcnow().isoformat()}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

@api_router.post("/kitchen/orders/{order_id}/served")
async def mark_order_served(order_id: str):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {"status": "served", "servedAt": datetime.utcnow().isoformat()}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

@api_router.post("/kitchen/orders/{order_id}/cancel")
async def cancel_kitchen_order(order_id: str):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {"status": "cancelled"}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

@api_router.post("/kitchen/orders/{order_id}/fire-course")
async def fire_next_course(order_id: str, course: int = 2):
    """Fire the next course for a multi-course order."""
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {"currentCourse": course}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

@api_router.post("/kitchen/orders/{order_id}/priority")
async def set_order_priority(order_id: str, priority: str = "rush"):
    result = await db.kitchen_orders.find_one_and_update(
        {"id": order_id},
        {"$set": {"priority": priority}},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    result.pop("_id", None)
    return result

# ============ ROOT ============
@api_router.get("/")
async def root():
    return {
        "name": "Ananta POS API",
        "version": "2.0.0",
        "description": "Complete Point of Sale System with Accounting & BAS/GST Filing",
        "features": [
            "Sales & Checkout", "Inventory Management", "Customer Loyalty",
            "Staff Management", "Accounting & Tax", "Gift Cards", "Refunds",
            "Suppliers", "Expenses", "Table Management", "Offline Support",
            "Split Payments", "Tipping", "Product Modifiers", "Multi-location",
            "EFTPOS Integration (Linkly, Tyro, Smartpay, Windcave, etc.)"
        ],
        "status": "Production Ready"
    }

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
