"""The API is default-deny, and the guest surface still works.

Both halves have to hold. A sweep found 66 routes answering with no credential
at all — the customer list with names and emails, the P&L, writable business
settings — so the door was closed. Closing it without breaking the booking
portal, the QR menu and the storefront is the part that needs proving, so
those are walked end to end here as an anonymous guest.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from conftest import OWNER, req

# Reachable without logging in, on purpose. Anything not on this list that
# answers an anonymous caller is a finding.
INTENTIONALLY_PUBLIC = {
    "/api/", "/api/health", "/api/healthz",
    "/api/auth/login", "/api/auth/register", "/api/auth/logout",
    "/api/auth/refresh", "/api/auth/me",
    "/api/auth/forgot-password", "/api/auth/reset-password",
    "/api/business/theme",
    "/api/products", "/api/categories", "/api/modifiers",
    "/api/online/categories", "/api/online/products", "/api/online/orders",
    "/api/members/login", "/api/members/signup",
    "/api/webhook/stripe", "/api/stripe/webhook",
}
PUBLIC_PREFIXES = ("/api/public/", "/api/table/", "/api/online/orders/track/",
                   "/api/members/share-link/", "/api/stripe/checkout/status/")

MUST_BE_SHUT = [
    ("GET", "/api/customers"), ("GET", "/api/users"), ("GET", "/api/transactions"),
    ("GET", "/api/accounting/p-and-l"), ("GET", "/api/accounting/summary"),
    ("GET", "/api/analytics/command-center"), ("GET", "/api/analytics/menu-engineering"),
    ("GET", "/api/business/settings"), ("POST", "/api/business/settings"),
    ("GET", "/api/expenses"), ("GET", "/api/suppliers"), ("GET", "/api/bas-gst/reports"),
    ("GET", "/api/kitchen/orders"), ("GET", "/api/staff/smart-roster"),
    ("GET", "/api/pre-shift/today"), ("GET", "/api/auth/roles"),
    ("GET", "/api/permissions/roles"), ("GET", "/api/permissions/catalog"),
    ("GET", "/api/integrations"), ("GET", "/api/eftpos/transactions"),
    ("GET", "/api/vouchers"), ("GET", "/api/payment-links"), ("GET", "/api/floor-plans"),
    ("GET", "/api/tables/qr-codes"), ("GET", "/api/staff/commissions"),
    ("GET", "/api/reservations/guest-lookup"), ("GET", "/api/bookings/inbox"),
    ("GET", "/api/automation/alerts"), ("GET", "/api/kitchen/prep-list"),
    ("GET", "/api/receipt/settings"),
    ("POST", "/api/products"), ("POST", "/api/expenses"), ("POST", "/api/suppliers"),
]


def _is_public(path):
    return path in INTENTIONALLY_PUBLIC or path.startswith(PUBLIC_PREFIXES)


@pytest.mark.parametrize("method,path", MUST_BE_SHUT, ids=lambda v: str(v).replace("/", "_"))
def test_internal_endpoints_refuse_anonymous(anon, method, path):
    r = req(anon, method, path, json={})
    assert r.status_code in (401, 403), \
        f"{method} {path} answered {r.status_code} with no credential: {r.text[:200]}"


def test_no_get_route_answers_anonymously_unless_allow_listed(anon, app):
    """The sweep itself — this is what found the original 66."""
    paths = sorted({
        r.path for r in app.routes
        if "GET" in (getattr(r, "methods", set()) or set())
        and getattr(r, "path", "").startswith("/api")
        and "{" not in getattr(r, "path", "")
    })
    leaking = []
    for path in paths:
        try:
            r = req(anon, "GET", path)
        except Exception:
            continue                      # a route that raises isn't an auth answer
        if r.status_code < 400 and not _is_public(path):
            leaking.append((path, r.status_code, len(r.text)))
    assert not leaking, "these answered an anonymous caller:\n" + "\n".join(map(str, leaking))


def _forge(payload, key="test-secret-not-for-production"):
    return jwt.encode(payload, key, algorithm="HS256")


def test_garbage_token_is_refused(anon):
    r = req(anon, "GET", "/api/customers", headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401


def test_token_signed_with_another_key_is_refused(anon):
    tok = _forge({"sub": "x", "type": "access",
                  "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                 key="not-the-real-secret")
    r = req(anon, "GET", "/api/customers", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


def test_expired_token_is_refused(anon):
    tok = _forge({"sub": "x", "type": "access",
                  "exp": datetime.now(timezone.utc) - timedelta(hours=1)})
    r = req(anon, "GET", "/api/customers", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


def test_refresh_token_cannot_be_used_as_an_access_token(anon):
    tok = _forge({"sub": "x", "type": "refresh",
                  "exp": datetime.now(timezone.utc) + timedelta(days=1)})
    r = req(anon, "GET", "/api/customers", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


# ── Staff still get in, and are still held to their role ────────────────────

def test_owner_reaches_the_money_screens(client, owner_headers):
    assert req(client, "GET", "/api/customers", headers=owner_headers).status_code == 200
    assert req(client, "GET", "/api/accounting/p-and-l", headers=owner_headers).status_code == 200


def test_cashier_is_refused_the_pandl_but_keeps_the_kitchen_board(client, owner_headers):
    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Gate Cashier", "email": "gate.cashier@nua.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={
        "email": "gate.cashier@nua.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    assert "token" in tok, str(tok)[:200]
    ch = {"Authorization": f"Bearer {tok['token']}"}
    assert req(client, "GET", "/api/accounting/p-and-l", headers=ch).status_code == 403
    assert req(client, "GET", "/api/kitchen/orders", headers=ch).status_code == 200


# ── The guest surface still works ───────────────────────────────────────────

def test_booking_portal_works_for_a_guest(anon):
    assert req(anon, "GET", "/api/public/menu").status_code == 200
    assert req(anon, "GET", "/api/public/available-slots",
               params={"date": "2026-08-10", "party_size": 2}).status_code == 200
    r = req(anon, "POST", "/api/public/book", json={
        "name": "Anon Guest", "phone": "0400999888", "email": "anon@example.com",
        "date": "2026-08-10", "time": "18:30", "partySize": 2})
    assert r.status_code == 200, r.text[:200]


def test_storefront_order_and_tracking_work_for_a_guest(anon):
    products = req(anon, "GET", "/api/online/products")
    assert products.status_code == 200 and products.json()
    assert req(anon, "GET", "/api/online/categories").status_code == 200
    r = req(anon, "POST", "/api/online/orders", json={
        "channel": "pickup", "customerName": "Anon Guest", "customerPhone": "0400999888",
        "items": [{"productId": products.json()[0]["id"], "name": "Thing",
                   "quantity": 1, "price": 10.0}]})
    assert r.status_code == 200, r.text[:200]
    code = r.json().get("trackingCode") or r.json().get("code")
    if code:
        assert req(anon, "GET", f"/api/online/orders/track/{code}").status_code == 200


def test_login_and_brand_theme_stay_reachable(anon):
    assert req(anon, "POST", "/api/auth/login", json=OWNER).status_code == 200
    assert req(anon, "GET", "/api/business/theme").status_code == 200


# ── The public menu is the menu, not the trade catalogue ────────────────────

TRADE_FIELDS = ("cost", "stock", "sku")


def test_guest_menu_has_the_menu_but_not_the_trade_data(anon):
    r = req(anon, "GET", "/api/products")
    assert r.status_code == 200
    menu = r.json()
    assert any(p.get("name") and p.get("price") for p in menu), "guest menu had no sellable item"
    leaked = [p for p in menu if any(p.get(f) for f in TRADE_FIELDS)]
    assert not leaked, f"guest menu leaked cost/stock/sku: {leaked[:1]}"


def test_storefront_listing_hides_trade_data_too(anon):
    r = req(anon, "GET", "/api/online/products")
    assert r.status_code == 200
    leaked = [p for p in r.json() if any(p.get(f) for f in TRADE_FIELDS)]
    assert not leaked, f"storefront leaked cost/stock/sku: {leaked[:1]}"


def test_staff_still_see_cost_and_stock(client, owner_headers):
    r = req(client, "GET", "/api/products", headers=owner_headers)
    assert r.status_code == 200
    assert any(p.get("cost") for p in r.json()), "no product carried a cost for a logged-in user"
