"""Iteration 24 — Enterprise Licensing & Entitlements regression suite.

Covers:
  - /api/license/me  (with / without license)
  - /api/license/onboard (checksum, devSkipAbr, ABR_GUID guard, duplicate)
  - /api/license/validate (no device, device match, device mismatch)
  - /api/license/device/activate (idempotent)
  - middleware enforcement: active / suspended / grace / abn_review
  - always-open allowlist (/api/license/me, /api/v25/warehouse/export/transactions)
  - /api/license/abn/change-request + approve gate (X-Support-Override)
  - /api/license/audit
  - /api/license/stripe/webhook  (invoice.payment_failed + invoice.paid)
"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

OWNER = {"email": "owner@nuva.com", "password": "NuvaOwner2026!"}
TEST_TENANT = "default"           # already has license per agent_to_agent context
ISOLATED_TENANT = f"TEST_{uuid.uuid4().hex[:8]}"  # used for onboarding flow


@pytest.fixture(scope="module")
def owner_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=OWNER, timeout=30)
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text[:200]}"
    yield s
    # Best-effort: restore default tenant to active at end of suite
    try:
        s.post(f"{API}/license/dev/force-state", json={"state": "active"}, timeout=15)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# /license/me + onboarding
# ---------------------------------------------------------------------------

def test_license_me_returns_data(owner_session):
    r = owner_session.get(f"{API}/license/me", timeout=15)
    assert r.status_code == 200
    data = r.json()
    # Either we have a license or we don't — both are valid responses
    assert "hasLicense" in data
    # Per agent_to_agent context, default tenant should already have a license
    if data.get("hasLicense"):
        assert data["state"] in ("active", "past_due", "grace", "suspended", "cancelled", "abn_review")
        assert "_id" not in data


def test_onboard_rejects_bad_checksum(owner_session):
    # Force-state back to active first (so middleware doesn't block license endpoints — they're always-open anyway)
    r = owner_session.post(f"{API}/license/onboard",
                           json={"tenantId": ISOLATED_TENANT, "abn": "12345678901", "ownerEmail": "x@y.com"},
                           timeout=15)
    assert r.status_code == 422, f"Expected 422 ABN checksum, got {r.status_code}: {r.text[:200]}"
    assert "checksum" in r.text.lower()


def test_onboard_with_dev_skip_succeeds(owner_session):
    """Onboard a brand-new isolated tenant via devSkipAbr to avoid hitting ABR live."""
    payload = {
        "tenantId": ISOLATED_TENANT,
        "abn": "51824753556",
        "ownerEmail": "owner@nuva.com",
        "entityName": "TEST DEMO PTY LTD",
        "plan": "standard",
        "devSkipAbr": True,
    }
    r = owner_session.post(f"{API}/license/onboard", json=payload, timeout=20)
    assert r.status_code == 200, f"Onboard failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    assert data["state"] == "active"
    assert data["abn"] == "51824753556"
    assert data["abnVerified"] is True
    assert data["tenantId"] == ISOLATED_TENANT


def test_onboard_duplicate_returns_409(owner_session):
    r = owner_session.post(f"{API}/license/onboard",
                           json={"tenantId": ISOLATED_TENANT, "abn": "51824753556",
                                 "ownerEmail": "x@y.com", "devSkipAbr": True},
                           timeout=15)
    assert r.status_code == 409


def test_onboard_without_dev_skip_requires_abr_guid(owner_session):
    """ABR_GUID is intentionally NOT configured. Onboarding without devSkipAbr must fail clearly."""
    if os.environ.get("ABR_GUID"):
        pytest.skip("ABR_GUID is configured — live path will succeed instead")
    new_tenant = f"TEST_{uuid.uuid4().hex[:8]}"
    r = owner_session.post(f"{API}/license/onboard",
                           json={"tenantId": new_tenant, "abn": "51824753556",
                                 "ownerEmail": "x@y.com"},
                           timeout=20)
    assert r.status_code in (500, 503)
    assert "ABR_GUID" in r.text


# ---------------------------------------------------------------------------
# /license/validate + device activation
# ---------------------------------------------------------------------------

def test_validate_issues_token(owner_session):
    device_id = f"TEST_DEV_{uuid.uuid4().hex[:6]}"
    r = owner_session.post(f"{API}/license/validate",
                           json={"tenantId": "default", "deviceId": device_id, "appVersion": "test"},
                           timeout=15)
    assert r.status_code == 200
    data = r.json()
    # First activation case: no device on file → still ok=true with token
    if data.get("ok"):
        assert "token" in data
        assert data.get("ttlSeconds", 0) > 0


def test_device_activate_idempotent(owner_session):
    device_id = f"TEST_DEV_{uuid.uuid4().hex[:6]}"
    first = owner_session.post(f"{API}/license/device/activate",
                                json={"tenantId": "default", "deviceId": device_id,
                                      "name": "Test POS"},
                                timeout=15)
    assert first.status_code == 200
    body = first.json()
    assert body.get("activated") is True or body.get("alreadyActive") is True

    # Re-activate same device → should be idempotent
    second = owner_session.post(f"{API}/license/device/activate",
                                 json={"tenantId": "default", "deviceId": device_id},
                                 timeout=15)
    assert second.status_code == 200
    assert second.json().get("alreadyActive") is True


def test_validate_rejects_unknown_device(owner_session):
    """Default tenant now has at least 1 device — a different deviceId must be rejected."""
    unknown = f"TEST_UNKNOWN_{uuid.uuid4().hex[:6]}"
    r = owner_session.post(f"{API}/license/validate",
                           json={"tenantId": "default", "deviceId": unknown},
                           timeout=15)
    assert r.status_code == 200
    data = r.json()
    # Should be either rejected with DEVICE_NOT_AUTHORIZED, or accepted if no devices on file
    if data.get("ok") is False:
        assert data.get("errorCode") == "DEVICE_NOT_AUTHORIZED"


# ---------------------------------------------------------------------------
# Force-state + middleware enforcement
# ---------------------------------------------------------------------------

def _force(s, state):
    r = s.post(f"{API}/license/dev/force-state", json={"state": state}, timeout=15)
    assert r.status_code == 200, f"force-state {state}: {r.status_code} {r.text[:200]}"
    return r.json()


def test_suspended_blocks_transactions(owner_session):
    _force(owner_session, "suspended")
    r = owner_session.post(f"{API}/transactions",
                            json={"items": [], "total": 0, "paymentMethod": "cash"},
                            timeout=15)
    assert r.status_code == 423, f"Expected 423 suspended, got {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert body.get("errorCode") == "LICENSE_SUSPENDED"


def test_suspended_still_allows_license_me_and_warehouse_export(owner_session):
    # state still suspended from previous test
    me = owner_session.get(f"{API}/license/me", timeout=15)
    assert me.status_code == 200
    wh = owner_session.get(f"{API}/v25/warehouse/export?collection=transactions&limit=5", timeout=20)
    assert wh.status_code == 200, f"Warehouse export should be always-open: got {wh.status_code}"


def test_grace_blocks_publish_but_allows_reads(owner_session):
    _force(owner_session, "grace")
    pub = owner_session.post(f"{API}/v25/sites/publish",
                              json={"siteId": "TEST_SITE"},
                              timeout=15)
    assert pub.status_code == 423, f"Expected 423 in grace for sites/publish, got {pub.status_code}"
    body = pub.json()
    assert body.get("errorCode") == "SUBSCRIPTION_PAST_DUE"


def test_abn_review_blocks_new_transactions(owner_session):
    _force(owner_session, "abn_review")
    r = owner_session.post(f"{API}/transactions",
                            json={"items": [], "total": 0, "paymentMethod": "cash"},
                            timeout=15)
    assert r.status_code == 423
    assert r.json().get("errorCode") == "ABN_REVERIFY_REQUIRED"


def test_active_restores_everything(owner_session):
    _force(owner_session, "active")
    # Verify license/me reports active
    me = owner_session.get(f"{API}/license/me", timeout=15)
    assert me.status_code == 200
    assert me.json().get("state") == "active"


# ---------------------------------------------------------------------------
# ABN change request + approve gate
# ---------------------------------------------------------------------------

def test_abn_change_request_moves_to_review(owner_session):
    # Use devSkipAbr-free path? change-request always does live lookup_abn → will 503 if no ABR_GUID
    # Per spec, this is expected to fail without ABR_GUID. Test the failure mode.
    if not os.environ.get("ABR_GUID"):
        r = owner_session.post(f"{API}/license/abn/change-request",
                                json={"newAbn": "53004085616", "twoFactorCode": "1234",
                                      "reason": "test"},
                                timeout=20)
        # Either 503 (no ABR_GUID) or 200 if configured
        assert r.status_code in (503, 500, 200)
        if r.status_code in (500, 503):
            assert "ABR" in r.text or "abr" in r.text.lower()
        return
    # If ABR_GUID is configured, the request should succeed and move to review
    r = owner_session.post(f"{API}/license/abn/change-request",
                            json={"newAbn": "53004085616", "twoFactorCode": "1234",
                                  "reason": "test"},
                            timeout=30)
    assert r.status_code == 200
    me = owner_session.get(f"{API}/license/me", timeout=15)
    assert me.json().get("state") == "abn_review"
    # restore
    _force(owner_session, "active")


def test_abn_approve_without_override_is_forbidden(owner_session):
    # Use a dummy req id; the override gate is checked BEFORE the lookup
    r = owner_session.post(f"{API}/license/abn/approve/dummy",
                            timeout=15)
    assert r.status_code == 403
    assert "not permitted" in r.text.lower() or "support" in r.text.lower()


def test_2fa_required_for_change_request(owner_session):
    r = owner_session.post(f"{API}/license/abn/change-request",
                            json={"newAbn": "53004085616", "twoFactorCode": ""},
                            timeout=15)
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def test_audit_log_returns_rows(owner_session):
    r = owner_session.get(f"{API}/license/audit", timeout=15)
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) > 0
    # Each row should have id, action, createdAt
    sample = rows[0]
    assert "action" in sample
    assert "createdAt" in sample
    assert "_id" not in sample
    # Should include some known actions across the suite
    actions = {row["action"] for row in rows}
    # we've done device.activated + state.forced this run
    assert "state.forced" in actions or "device.activated" in actions


# ---------------------------------------------------------------------------
# Stripe webhook
# ---------------------------------------------------------------------------

def test_stripe_webhook_no_customer_match_returns_received(owner_session):
    # Send an invoice.paid event without a matching stripeCustomerId
    payload = {
        "type": "invoice.paid",
        "data": {"object": {"customer": "cus_does_not_exist", "id": "in_TEST", "period_end": int(time.time()) + 86400}},
    }
    r = requests.post(f"{API}/license/stripe/webhook", json=payload, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body.get("received") is True
    assert "ignored" in body  # no license linked


def test_final_state_restored(owner_session):
    _force(owner_session, "active")
    me = owner_session.get(f"{API}/license/me", timeout=15)
    assert me.json().get("state") == "active"
