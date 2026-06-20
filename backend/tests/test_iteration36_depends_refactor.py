"""
Iteration 36 — P2 cleanup: Validate `Depends`-based auth precedence refactor
across the remaining ~16 legacy routers (~230 endpoints). Plus regression on
endpoints validated in iteration 35.

For each refactored router we check:
  1) Anonymous POST returns 401 (NOT 422) — auth fires BEFORE body validation.
  2) Owner happy-path on at least one representative endpoint returns 2xx.
"""
import os
import pytest
import requests

def _load_backend_url():
    val = os.environ.get("REACT_APP_BACKEND_URL")
    if not val:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        val = line.split("=", 1)[1].strip()
                        break
        except FileNotFoundError:
            pass
    assert val, "REACT_APP_BACKEND_URL not set in env or frontend/.env"
    return val.rstrip("/")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@nuva.com"
OWNER_PASSWORD = "NuvaOwner2026!"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def anon_client():
    """Anonymous session - guaranteed no auth cookies."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def owner_token():
    """Use a throwaway session for login so the anon_client stays clean."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
               timeout=15)
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text[:300]}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"No token in login response: {r.text[:300]}"
    return tok


@pytest.fixture(scope="module")
def owner_client(owner_token):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {owner_token}",
    })
    return s


# ---------- 1. AUTH PRECEDENCE: anon → 401, not 422 ----------
ANON_POST_CASES = [
    # v25_suite
    ("/v25/sync-queue", {}),
    ("/v25/sites", {}),
    ("/v25/disputes", {}),
    # NOTE: /v25/kiosk/session and /online/orders are intentionally public
    # (kiosk + storefront) — they do NOT require auth.
    # v26_commerce
    ("/v26/vouchers", {}),
    ("/v26/gift-cards/sell", {}),
    ("/v26/events", {}),
    # inventory_accounting
    ("/ingredients", {}),
    ("/stock-takes", {}),
    ("/stock/deduct-recipe", {}),
    # loyalty_engine
    ("/loyalty/earn", {}),
    ("/loyalty/redeem", {}),
    ("/agent/tick", {}),
    # staff_management
    ("/staff/clock-in", {}),
    ("/staff/roster", {}),
    ("/receipt/settings", {}),
    # online_orders (place_order is public storefront — no auth)
    # menu_features
    ("/menu/ai-import", {}),
    ("/menu/price-adjust", {}),
    ("/pos/ghost-discount", {}),
    # gamification
    ("/tips/smart-distribute", {}),
    ("/print-routing/config", {}),
    # multi_tenant
    ("/business/create", {}),
    # v15_features
    ("/pos/tabs", {}),
    ("/items/bulk-import", {}),
    ("/pos/voice-order", {}),
    ("/ai/ask-nua", {}),
]


@pytest.mark.parametrize("path,body", ANON_POST_CASES)
def test_anon_post_returns_401_not_422(anon_client, path, body):
    r = anon_client.post(f"{API}{path}", json=body, timeout=10)
    assert r.status_code == 401, (
        f"POST {path}: expected 401 for anon (auth before body), got "
        f"{r.status_code} — body: {r.text[:200]}"
    )


# ---------- 2. OWNER HAPPY-PATH (GET regression) ----------
OWNER_GET_CASES = [
    # v25_suite
    "/v25/hardware",
    "/v25/suppliers/compare",
    "/v25/sites",
    "/v25/disputes",
    "/v25/exceptions",
    "/v25/cfd/current",
    "/v25/recovery/churn-risk",
    # v26_commerce
    "/v26/vouchers",
    "/v26/promotions/active-now",
    "/v26/gift-cards",
    "/v26/events",
    # inventory_accounting
    "/ingredients",
    "/ingredients/low-stock",
    "/recipes",
    "/stock-takes",
    # loyalty_engine
    "/loyalty/config",
    "/agent/segments",
    "/agent/decisions",
    "/agent/voice-catalog",
    # staff_management
    "/staff/my-status",
    "/staff/timecards",
    "/staff/roster",
    "/staff/reports",
    "/payrun/calculate",
    "/payrun/history",
    "/receipt/settings",
    # online_orders
    "/online/categories",
    "/online/products",
    "/online/orders",
    "/online/kitchen/load",
    # menu_features
    "/pos/ghost-discounts",
    # gamification
    "/staff/leaderboard",
    "/reports/quarterly-review",
    "/print-routing/config",
    "/print-routing/queue",
    # multi_tenant
    "/business/list",
    # v15_features
    "/dock/badges",
    "/pos/tabs",
    "/pos/favorites",
    "/analytics/inventory-anomalies",
    "/staff/shift-swaps",
    "/analytics/booking-heatmap",
    "/analytics/cohort-retention",
]


@pytest.mark.parametrize("path", OWNER_GET_CASES)
def test_owner_get_no_500(owner_client, path):
    r = owner_client.get(f"{API}{path}", timeout=20)
    # accept 2xx, 404 for resource-not-found, but NEVER 500
    assert r.status_code < 500, (
        f"GET {path} returned {r.status_code} (5xx regression) — body: "
        f"{r.text[:300]}"
    )
    assert r.status_code != 401, (
        f"GET {path} returned 401 for OWNER (token issue): {r.text[:200]}"
    )
    assert r.status_code != 403, (
        f"GET {path} returned 403 for OWNER (role gate too strict): "
        f"{r.text[:200]}"
    )


# ---------- 3. OWNER HAPPY-PATH (POST writes — light, idempotent-ish) ----------
class TestOwnerPostHappyPath:
    """Carefully crafted POSTs with valid minimal bodies — confirm 2xx (not 422/500)."""

    def test_v25_sync_queue_post(self, owner_client):
        r = owner_client.post(f"{API}/v25/sync-queue",
                              json={"op": "test", "payload": {"x": 1}})
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:200]}"

    def test_v25_hardware_heartbeat_uses_device_secret(self, owner_client):
        # Heartbeat uses a separate device-secret auth, not JWT — so an
        # owner-JWT call is expected to be 401. Just confirm it doesn't 500.
        r = owner_client.post(f"{API}/v25/hardware/heartbeat",
                              json={"deviceId": "TEST_DEV_01", "status": "ok"})
        assert r.status_code in (200, 201, 401), f"{r.status_code} {r.text[:200]}"

    def test_inventory_create_ingredient(self, owner_client):
        r = owner_client.post(f"{API}/ingredients", json={
            "name": "TEST_ing_36",
            "unit": "g",
            "qty": 100,
            "costPerUnit": 0.05,
        })
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:200]}"
        data = r.json()
        assert data.get("name") == "TEST_ing_36" or "id" in data, data

    def test_staff_roster_post(self, owner_client):
        r = owner_client.post(f"{API}/staff/roster", json={
            "staffId": "TEST_staff_36",
            "date": "2026-02-01",
            "startTime": "09:00",
            "endTime": "17:00",
            "role": "cashier",
        })
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:200]}"

    def test_v15_pos_tab_create(self, owner_client):
        r = owner_client.post(f"{API}/pos/tabs",
                              json={"label": "TEST_Tab_36", "color": "#fff"})
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:200]}"

    def test_gamification_print_routing_config(self, owner_client):
        r = owner_client.post(f"{API}/print-routing/config", json={
            "routes": {"kitchen": "PRINTER_A"}
        })
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:200]}"

    def test_multi_tenant_branch_create(self, owner_client):
        r = owner_client.post(f"{API}/business/create", json={
            "name": "TEST_Branch_36",
            "type": "cafe",
            "address": "123 Test St",
        })
        # 200/201 success; 409 if already exists is acceptable
        assert r.status_code in (200, 201, 409), f"{r.status_code} {r.text[:200]}"

    def test_v26_voucher_create(self, owner_client):
        r = owner_client.post(f"{API}/v26/vouchers", json={
            "code": "TEST_V36",
            "type": "percent",
            "value": 10,
            "active": True,
        })
        assert r.status_code in (200, 201, 409), f"{r.status_code} {r.text[:200]}"

    def test_loyalty_engine_agent_tick(self, owner_client):
        r = owner_client.post(f"{API}/agent/tick", json={})
        # tick may return 200 with no-op
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:200]}"

    def test_online_order_create(self, owner_client):
        # need at least minimal cart — endpoint usually accepts a thin body
        r = owner_client.post(f"{API}/online/orders", json={
            "items": [{"productId": "p_test", "qty": 1, "price": 5}],
            "customer": {"name": "TEST_36", "phone": "0400000036"},
            "channel": "website",
            "total": 5,
        })
        # 200/201 success; if backend strictly validates product existence -> 400
        assert r.status_code in (200, 201, 400), f"{r.status_code} {r.text[:200]}"


# ---------- 4. ITERATION-35 REGRESSION (representative) ----------
class TestIteration35Regression:
    def test_products_list(self, owner_client):
        r = owner_client.get(f"{API}/products")
        assert r.status_code == 200, r.text[:200]
        assert isinstance(r.json(), list)

    def test_modifiers_list(self, owner_client):
        r = owner_client.get(f"{API}/modifiers")
        assert r.status_code == 200, r.text[:200]

    def test_categories_list(self, owner_client):
        r = owner_client.get(f"{API}/categories")
        assert r.status_code == 200, r.text[:200]

    def test_discounts_list(self, owner_client):
        r = owner_client.get(f"{API}/discounts")
        assert r.status_code == 200, r.text[:200]

    def test_channel_menus_channels(self, owner_client):
        r = owner_client.get(f"{API}/channel-menus/channels")
        assert r.status_code == 200, r.text[:200]

    def test_anon_products_bulk_edit_401(self, anon_client):
        r = anon_client.post(f"{API}/products/bulk-edit", json={})
        assert r.status_code == 401, r.text[:200]

    def test_anon_modifiers_401(self, anon_client):
        r = anon_client.post(f"{API}/modifiers", json={})
        assert r.status_code == 401, r.text[:200]
