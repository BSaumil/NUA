from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / '.env')

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
import logging
import os

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
from routes.auth import router as auth_router, seed_admin
from routes.ai_pantry import router as ai_pantry_router
from routes.members import router as members_router
from routes.multi_tenant import router as multi_tenant_router, seed_default_business
from routes.advanced_features import router as advanced_features_router
from routes.staff_management import router as staff_mgmt_router
from routes.menu_features import router as menu_features_router
from routes.enterprise_features import router as enterprise_router

app = FastAPI()

api_router = APIRouter(prefix="/api")

# Include all route modules
api_router.include_router(auth_router)
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
api_router.include_router(ai_pantry_router)
api_router.include_router(members_router)
api_router.include_router(advanced_features_router)  # Must be before multi_tenant to avoid /business/settings conflict
api_router.include_router(staff_mgmt_router)
api_router.include_router(menu_features_router)
api_router.include_router(enterprise_router)
api_router.include_router(multi_tenant_router)

@api_router.get("/")
async def root():
    return {
        "name": "NUVA POS API",
        "version": "5.0.0",
        "status": "Production Ready",
        "features": [
            "Staff Auth & RBAC", "AI Smart Pantry", "Member Portal & Vouchers",
            "Multi-Business Management", "Stripe Payments", "Table-Side QR Ordering",
            "18+ Hospitality Integrations", "Kitchen Display", "Reservations & Floor Plans",
            "Menu Engineering", "Demand Forecasting", "Automation Engine",
        ],
    }

app.include_router(api_router)

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup():
    await seed_admin()
    await seed_default_business()
    logger.info("Admin seeded, default business created")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
