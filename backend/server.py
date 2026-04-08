from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
import logging

from database import db, client

from routes.products import router as products_router
from routes.transactions import router as transactions_router
from routes.customers import router as customers_router
from routes.reservations import router as reservations_router
from routes.kitchen import router as kitchen_router
from routes.analytics import router as analytics_router
from routes.automation import router as automation_router
from routes.settings import router as settings_router
from routes.loyalty import router as loyalty_router
from routes.public import router as public_router
from routes.table_ordering import router as table_ordering_router
from routes.integrations import router as integrations_router

# Create the main app
app = FastAPI()

# Create router with /api prefix
api_router = APIRouter(prefix="/api")

# Include all route modules
api_router.include_router(products_router)
api_router.include_router(transactions_router)
api_router.include_router(customers_router)
api_router.include_router(reservations_router)
api_router.include_router(kitchen_router)
api_router.include_router(analytics_router)
api_router.include_router(automation_router)
api_router.include_router(settings_router)
api_router.include_router(loyalty_router)
api_router.include_router(public_router)
api_router.include_router(table_ordering_router)
api_router.include_router(integrations_router)

# Root endpoint
@api_router.get("/")
async def root():
    return {
        "name": "Ananta POS API",
        "version": "3.0.0",
        "description": "Complete Point of Sale System with Accounting, BAS/GST, Reservations, Kitchen, and Analytics",
        "features": [
            "Sales & Checkout", "Inventory Management", "Customer Loyalty",
            "Staff Management", "Accounting & Tax", "Gift Cards", "Refunds",
            "Suppliers", "Expenses", "Table Management", "Offline Support",
            "Split Payments", "QR/UPI Payments", "Tipping", "Product Modifiers",
            "Multi-location", "EFTPOS Integration", "Reservations", "Floor Plans",
            "Waitlist", "Kitchen Display", "Menu Engineering", "AI Command Center",
            "Automation Engine", "Demand Forecasting", "Public Booking Portal",
        ],
        "status": "Production Ready"
    }

# Include router in app
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
