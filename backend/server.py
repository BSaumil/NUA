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
from routes.identity import router as identity_router
from routes.reservations import router as reservations_router
from routes.kitchen import router as kitchen_router
from routes.coursing import router as coursing_router
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
from routes.realtime import router as realtime_router
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
from routes.loyalty_v2 import router as loyalty_v2_router
from routes.measured_inventory import router as measured_inventory_router
from routes.notifications import router as notifications_router
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
from routes.payroll import router as payroll_router, _apply_persisted_wallet_credentials
from routes.commerce_v29 import router as commerce_v29_router
from routes.accounting import router as accounting_router
from routes.rules_engine import router as rules_engine_router
from routes.audit import router as audit_router
from routes.approvals import router as approvals_router
from routes.nua import router as nua_router
from routes.hq import router as hq_router
from middleware.license_middleware import LicenseEnforcementMiddleware
from middleware.actor_context import ActorContextMiddleware

app = FastAPI()

api_router = APIRouter(prefix="/api")

# Include all route modules
api_router.include_router(auth_router)
api_router.include_router(products_router)
api_router.include_router(transactions_router)
api_router.include_router(customers_router)
api_router.include_router(identity_router)
api_router.include_router(reservations_router)
api_router.include_router(kitchen_router)
api_router.include_router(coursing_router)
api_router.include_router(analytics_router)
api_router.include_router(automation_router)
api_router.include_router(settings_router)
api_router.include_router(loyalty_router)
api_router.include_router(loyalty_v2_router)
api_router.include_router(measured_inventory_router)
api_router.include_router(notifications_router)
api_router.include_router(public_router)
api_router.include_router(table_ordering_router)
api_router.include_router(integrations_router)
api_router.include_router(ai_pantry_router)
api_router.include_router(members_router)
api_router.include_router(advanced_features_router)  # Must be before multi_tenant to avoid /business/settings conflict
api_router.include_router(realtime_router)
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
api_router.include_router(payroll_router)
api_router.include_router(commerce_v29_router)
api_router.include_router(accounting_router)
api_router.include_router(rules_engine_router)
api_router.include_router(audit_router)
api_router.include_router(approvals_router)
api_router.include_router(nua_router)
api_router.include_router(hq_router)
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

def _rate_limit_identity(request) -> str:
    """Prefer the authenticated user (from the Bearer token or session cookie)
    over raw IP — several client apps (POS, Staff app, Dashboard app) can
    legitimately share one venue's NAT'd IP, and keying on IP alone would let
    them starve each other's bucket. Falls back to IP for unauthenticated
    requests (e.g. login itself)."""
    token = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get("access_token")
    if token:
        try:
            import jwt, os
            payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:
            pass
    ip = request.client.host if request.client else "?"
    return f"ip:{ip}"


# ═══════════════════════════════════════════════════════════════════════════
# Default-deny at the door.
#
# Auth used to be opt-in: an endpoint was protected only if whoever wrote it
# remembered a `Depends`. With ~280 GET routes that is a losing game, and it
# lost — a sweep found the customer list, the P&L, the command centre and the
# business settings (writable!) all answering with no credential at all.
#
# So the default is inverted here. Anything under /api/ needs a valid token
# unless it is on the list below, and the list is short because the genuinely
# public surface is small: the booking portal, the QR table menu, the online
# storefront, the member join page, login, and payment webhooks.
#
# This checks the token is *real* (signature, type, expiry) but not who it
# belongs to — the per-route Depends still do the user lookup and the role and
# permission checks. This layer only closes "no credential, or a forged one".
# ═══════════════════════════════════════════════════════════════════════════
PUBLIC_API_PREFIXES = (
    "/api/public/",              # booking portal: menu, slots, book, waitlist, events
    "/api/table/",               # QR table ordering: menu, place order, order status
    "/api/online/orders/track/", # order tracking by code, from the SMS link
    "/api/members/share-link/",  # member referral links
    "/api/stripe/checkout/status/",
)

PUBLIC_API_PATHS = {
    "/api/", "/api/health", "/api/healthz",
    # Auth itself, plus the endpoints the login screen needs before there is a user
    "/api/auth/login", "/api/auth/register", "/api/auth/logout", "/api/auth/refresh",
    "/api/auth/me", "/api/auth/forgot-password", "/api/auth/reset-password",
    "/api/business/theme",       # login-screen branding
    # The menu, as guests see it. /products strips cost/stock/sku for guests.
    "/api/products", "/api/categories", "/api/modifiers",
    "/api/online/categories", "/api/online/products", "/api/online/orders",
    # Member self-service signup
    "/api/members/login", "/api/members/signup",
    # Payment provider callbacks — signed by the provider, not by a user
    "/api/webhook/stripe", "/api/stripe/webhook",
}


def _is_public_api(path: str) -> bool:
    return path in PUBLIC_API_PATHS or path.startswith(PUBLIC_API_PREFIXES)


class RequireAuthMiddleware(BaseHTTPMiddleware):
    """Reject /api/ traffic that carries no valid token, before it reaches a route."""

    async def dispatch(self, request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or not path.startswith("/api/"):
            return await call_next(request)
        if _is_public_api(path):
            return await call_next(request)

        token = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        if not token:
            token = request.cookies.get("access_token")
        if not token:
            # EventSource cannot set headers, so the SSE stream passes its JWT
            # as a query parameter. Same token, verified the same way here.
            token = request.query_params.get("token")
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

        try:
            import jwt
            payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
        # A refresh token must not be usable as an access token.
        if payload.get("type") not in (None, "access"):
            return JSONResponse(status_code=401, content={"detail": "Invalid token type"})
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """120 req/min per (tenant, identity). Excludes static & public booking."""
    def __init__(self, app):
        super().__init__(app)
        self.buckets = defaultdict(list)
        self.limit = 120
        self.window = 60
        self._last_evict = time()

    async def dispatch(self, request, call_next):
        path = request.url.path
        if not path.startswith("/api/") or path.startswith("/api/public") or path.startswith("/api/table"):
            return await call_next(request)
        tenant = request.headers.get("X-Tenant-Id", "default")
        identity = _rate_limit_identity(request)
        key = f"{tenant}:{identity}"
        now = time()
        # Evict idle clients every 5 min so the bucket dict can't grow unbounded
        if now - self._last_evict > 300:
            self._last_evict = now
            stale = [k for k, ts in self.buckets.items() if not ts or now - ts[-1] > self.window]
            for k in stale:
                del self.buckets[k]
        self.buckets[key] = [t for t in self.buckets[key] if now - t < self.window]
        if len(self.buckets[key]) >= self.limit:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded — 120 req/min per tenant"})
        self.buckets[key].append(now)
        return await call_next(request)

# Added before RateLimit so RateLimit ends up the outer of the two: an
# unauthenticated flood is still rate-limited rather than each request paying
# for a JWT verification.
app.add_middleware(RequireAuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LicenseEnforcementMiddleware)
app.add_middleware(ActorContextMiddleware)


# ═════════════════════════════════════════════════════════════════════════
# /api/ash/* → /api/nua/* alias (backwards-compat shim after Ash → NUA rebrand)
# ═════════════════════════════════════════════════════════════════════════
class NuaAliasMiddleware(BaseHTTPMiddleware):
    """Rewrite /api/ash/... to /api/nua/... so old tests keep working after
    the routes were renamed to the /nua namespace."""
    async def dispatch(self, request, call_next):
        p = request.url.path
        if p.startswith("/api/ash/") or p == "/api/ash":
            new_path = "/api/nua/" + p[len("/api/ash/"):] if p != "/api/ash" else "/api/nua"
            request.scope["path"] = new_path
            request.scope["raw_path"] = new_path.encode()
        return await call_next(request)


app.add_middleware(NuaAliasMiddleware)

# CORS: set FRONTEND_URL (comma-separated for multiple origins) in production.
# With explicit origins we allow credentialed (cookie) requests; without it we
# fall back to a wildcard WITHOUT credentials — Bearer-token auth still works,
# but any-origin-with-cookies (a CSRF vector) does not.
frontend_url = os.environ.get("FRONTEND_URL", "").strip()
if frontend_url:
    cors_origins = [o.strip().rstrip("/") for o in frontend_url.split(",") if o.strip()]
    cors_origins += ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_credentials = True
else:
    cors_origins = ["*"]
    cors_credentials = False
app.add_middleware(
    CORSMiddleware,
    allow_credentials=cors_credentials,
    allow_origins=cors_origins,
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
    # Preload persisted wallet credentials into process env
    try:
        await _apply_persisted_wallet_credentials()
    except Exception as exc:
        logger.warning("Wallet credentials preload skipped: %s", exc)
    # Seed Enterprise Chart of Accounts (idempotent)
    try:
        from services.accounting_service import seed_chart_of_accounts
        r = await seed_chart_of_accounts()
        if r.get("seeded"):
            logger.info("Chart of Accounts seeded: %s new accounts", r["seeded"])
    except Exception as exc:
        logger.warning("COA seed skipped: %s", exc)
    # Seed alcohol catalog + measured stock (idempotent)
    try:
        from services.alcohol_seeder import seed_alcohol_catalog
        r = await seed_alcohol_catalog()
        if r.get("categoriesInserted") or r.get("productsInserted"):
            logger.info("Alcohol catalog seeded: +%s categories, +%s products, +%s stock-units",
                          r["categoriesInserted"], r["productsInserted"], r["stockUnitsInserted"])
    except Exception as exc:
        logger.warning("Alcohol seed skipped: %s", exc)
    # Start Ash background scheduler
    try:
        from services.nua_scheduler import start_scheduler
        start_scheduler()
    except Exception as exc:
        logger.warning("Ash scheduler failed to start: %s", exc)
    # Analytics filters the course-event trail on time, and the trail needs a
    # TTL so it can't grow forever.
    try:
        from services.course_events import ensure_indexes
        await ensure_indexes()
    except Exception as exc:
        logger.warning("Course event indexes failed: %s", exc)
    # Course timing rules need minute-level granularity, so they get their own
    # loop rather than riding the hourly Ash scheduler.
    try:
        from services.coursing_scheduler import start_scheduler as start_coursing
        start_coursing()
    except Exception as exc:
        logger.warning("Coursing scheduler failed to start: %s", exc)
    # Burned TOTP codes and trusted devices both expire on their own.
    try:
        from services.two_factor import ensure_indexes as ensure_2fa_indexes
        await ensure_2fa_indexes()
    except Exception as exc:
        logger.warning("2FA indexes failed: %s", exc)

@app.on_event("shutdown")
async def shutdown_db_client():
    try:
        from services.nua_scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    try:
        from services.coursing_scheduler import stop_scheduler as stop_coursing
        stop_coursing()
    except Exception:
        pass
    client.close()
