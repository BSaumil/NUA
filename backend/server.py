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
from routes.awards import router as awards_router
from routes.bookings_inbox import router as bookings_inbox_router
from routes.channel_menus import router as channel_menus_router
from routes.social_media import router as social_media_router
from routes.menu_features import router as menu_features_router
from routes.enterprise_features import router as enterprise_router
from routes.gamification import router as gamification_router
from routes.reservation_features import router as reservation_features_router
from routes.items_system import router as items_system_router
from routes.v15_features import router as v15_router
from routes.loyalty_engine import router as loyalty_engine_router
from routes.phase_ef import router as phase_ef_router
from routes.phase_ef_wave2 import router as phase_ef_wave2_router
from routes.v25_suite import router as v25_suite_router
from routes.licensing import router as licensing_router
from routes.v26_commerce import router as v26_commerce_router
from routes.online_orders import router as online_orders_router
from routes.inventory_accounting import router as inventory_accounting_router
from routes.super import router as super_router
from routes.temperature import router as temperature_router
from routes.table_courses import router as table_courses_router
from routes.finalize import router as finalize_router
from middleware.license_middleware import LicenseEnforcementMiddleware

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
api_router.include_router(awards_router)
api_router.include_router(bookings_inbox_router)
api_router.include_router(channel_menus_router)
api_router.include_router(social_media_router)
api_router.include_router(menu_features_router)
api_router.include_router(enterprise_router)
api_router.include_router(gamification_router)
api_router.include_router(reservation_features_router)
api_router.include_router(items_system_router)
api_router.include_router(v15_router)
api_router.include_router(loyalty_engine_router)
api_router.include_router(phase_ef_router)
api_router.include_router(phase_ef_wave2_router)
api_router.include_router(v25_suite_router)
api_router.include_router(licensing_router)
api_router.include_router(v26_commerce_router)
api_router.include_router(online_orders_router)
api_router.include_router(inventory_accounting_router)
api_router.include_router(super_router)
api_router.include_router(temperature_router)
api_router.include_router(table_courses_router)
api_router.include_router(finalize_router)
api_router.include_router(multi_tenant_router)

@api_router.get("/")
async def root():
    return {
        "name": "NUA API",
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

# ============ Per-tenant rate limiter (lightweight in-memory) ============
from collections import defaultdict
from time import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    """120 req/min per (tenant, IP). Excludes static & public booking."""
    def __init__(self, app):
        super().__init__(app)
        self.buckets = defaultdict(list)
        self.limit = 120
        self.window = 60

    async def dispatch(self, request, call_next):
        path = request.url.path
        if not path.startswith("/api/") or path.startswith("/api/public") or path.startswith("/api/table"):
            return await call_next(request)
        tenant = request.headers.get("X-Tenant-Id", "default")
        ip = request.client.host if request.client else "?"
        key = f"{tenant}:{ip}"
        now = time()
        self.buckets[key] = [t for t in self.buckets[key] if now - t < self.window]
        if len(self.buckets[key]) >= self.limit:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded — 120 req/min per tenant"})
        self.buckets[key].append(now)
        return await call_next(request)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(LicenseEnforcementMiddleware)

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    # Custom headers the SPA reads (e.g. AI fallback flag on booking inbox).
    expose_headers=["x-ai-parsed-fallback"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup():
    await seed_admin()
    await seed_default_business()
    # Seed 5 demo customers + reservations/transactions/feedback (idempotent).
    try:
        from seeds.seed_customers import seed_demo_customers
        result = await seed_demo_customers()
        if result.get("seeded"):
            logger.info("Seeded %s demo customers", result.get("count"))
    except Exception as exc:
        logger.warning("Customer seed skipped: %s", exc)
    logger.info("Admin seeded, default business created")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
