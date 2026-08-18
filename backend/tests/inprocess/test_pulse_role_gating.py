"""Owner-level financials must not be readable by a cashier or kitchen login.

NUA serves three front doors from one build (app. / staff. / owner.
nuapos.com.au). Standing up owner.nuapos.com.au made this urgent: the owner
shell landed *every* authenticated role on /owner-dashboard, and the five
endpoints that dashboard and the Today screen read were all
`Depends(get_user)` — i.e. any role. A cashier could pull takings vs
target, labour cost and %, the AI briefing, and the health score including
gross and net margin.

Today.jsx already skipped the today-pulse call for non-management roles and
hid the tiles, but that is a client-side courtesy, not access control — the
endpoint answered anyone who asked it directly. All five are now gated
server-side, matching POST /nua/briefing/regenerate which was already
owner/manager-only.
"""
import asyncio

from database import db
from tests.inprocess.conftest import req


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

MANAGEMENT_ONLY_ENDPOINTS = [
    "/api/analytics/today-pulse",
    "/api/nua/health-score",
    "/api/nua/briefing",
    "/api/nua/insights",
    "/api/nua/insights/summary",
]


def _login_as(client, owner_headers, *, email, role):
    """Create (idempotently) a user of `role` and return its auth header.

    POST /api/auth/register deliberately forces every new account to
    `cashier` regardless of the role in the body — you can't self-assign your
    way up. Roles are granted elsewhere, so the role is set directly here to
    get a deterministic fixture; going through register alone would silently
    hand back a cashier and make a "manager" test pass for the wrong reason.
    """
    client.post("/api/auth/register", headers=owner_headers, json={
        "name": f"Pulse Test {role}", "email": email, "password": "PulseTest2026!",
    })
    _run(db.auth_users.update_one({"email": email}, {"$set": {"role": role}}))
    r = client.post("/api/auth/login", json={"email": email, "password": "PulseTest2026!"})
    assert r.status_code == 200, f"login as {role} failed: {r.text[:200]}"
    client.cookies.clear()
    body = r.json()
    assert body["user"]["role"] == role, f"fixture did not become a {role}: {body['user']['role']}"
    return {"Authorization": f"Bearer {body['token']}"}


def test_cashier_cannot_read_any_management_endpoint(client, owner_headers):
    cashier = _login_as(client, owner_headers, email="pulse.cashier@nua.com", role="cashier")
    for path in MANAGEMENT_ONLY_ENDPOINTS:
        r = req(client, "GET", path, headers=cashier)
        assert r.status_code == 403, f"{path} leaked to a cashier: {r.status_code} {r.text[:200]}"


def test_kitchen_cannot_read_any_management_endpoint(client, owner_headers):
    kitchen = _login_as(client, owner_headers, email="pulse.kitchen@nua.com", role="kitchen")
    for path in MANAGEMENT_ONLY_ENDPOINTS:
        r = req(client, "GET", path, headers=kitchen)
        assert r.status_code == 403, f"{path} leaked to kitchen: {r.status_code} {r.text[:200]}"


def test_owner_can_still_read_them_all(client, owner_headers):
    for path in MANAGEMENT_ONLY_ENDPOINTS:
        r = req(client, "GET", path, headers=owner_headers)
        assert r.status_code == 200, f"{path} broke for the owner: {r.status_code} {r.text[:200]}"


def test_manager_can_still_read_them_all(client, owner_headers):
    manager = _login_as(client, owner_headers, email="pulse.manager@nua.com", role="manager")
    for path in MANAGEMENT_ONLY_ENDPOINTS:
        r = req(client, "GET", path, headers=manager)
        assert r.status_code == 200, f"{path} broke for a manager: {r.status_code} {r.text[:200]}"


def test_health_score_really_does_carry_margin(client, owner_headers):
    # Guards the premise of this whole file: if the payload ever stopped
    # carrying margin, the gate above would be over-restrictive rather than
    # protective, and someone should reconsider it deliberately.
    r = req(client, "GET", "/api/nua/health-score", headers=owner_headers)
    assert r.status_code == 200
    subscores = r.json().get("subscores", {})
    assert "profit" in subscores
    assert {"grossMarginPct", "netMarginPct"} <= set(subscores["profit"])


def test_a_cashier_can_still_do_their_own_job(client, owner_headers):
    # The gate must not spill over into the endpoints a till actually needs.
    cashier = _login_as(client, owner_headers, email="pulse.cashier2@nua.com", role="cashier")
    for path in ["/api/products", "/api/categories", "/api/staff/my-status"]:
        r = req(client, "GET", path, headers=cashier)
        assert r.status_code == 200, f"{path} should stay open to a cashier: {r.status_code}"
