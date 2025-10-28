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
    gst = subtotal_after_discount * 0.1
    total = subtotal_after_discount + gst
    
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
        gst=gst,
        total=total,
        paymentMethod=transaction.paymentMethod,
        customerId=transaction.customerId,
        customerName=customer_name,
        location=transaction.location,
        cashier=transaction.cashier
    )
    
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

# ============ ROOT ============
@api_router.get("/")
async def root():
    return {"message": "Square POS API", "version": "1.0.0"}

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
