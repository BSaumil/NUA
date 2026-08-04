"""Iteration 23 — v25 Enterprise Suite regression.

Covers: GET smoke for all v25 endpoints + critical POST flows
(ash-pro/approve, sites, disputes, gift-cards issue+redeem, waste,
recipes/upsert, predictive-orders, concierge, marketing/auto, recovery/win-back).
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"
OWNER = {"email": "owner@nua.com", "password": "NuaOwner2026!"}


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def owner_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=OWNER, timeout=30)
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text[:200]}"
    return s


# ---------- GET smoke (every endpoint listed by main agent) ----------
GET_ENDPOINTS = [
    "/v25/sites",
    "/v25/hardware",
    "/v25/exceptions",
    "/v25/station-readiness",
    "/v25/margin-guardrails",
    "/v25/profit-guardian",
    "/v25/digital-twin",
    "/v25/shift-manager",
    "/v25/subscriptions/plans",
    "/v25/gift-cards",
    "/v25/recipes/list",
    "/v25/waste",
    "/v25/waste/insights",
    "/v25/recovery/churn-risk",
    "/v25/reputation",
    "/v25/franchise/dashboard",
    "/v25/benchmark",
    "/v25/fraud-detection",
    "/v25/dynamic-pricing",
    "/v25/marketing/auto",
    "/v25/disputes",
    "/v25/kiosk/sessions",
    "/v25/ash-pro/plan",
]


@pytest.mark.parametrize("path", GET_ENDPOINTS)
def test_v25_get_200(owner_session, path):
    r = owner_session.get(f"{API}{path}", timeout=60)
    assert r.status_code == 200, f"GET {path} -> {r.status_code} {r.text[:200]}"
    # Make sure response is JSON and excludes _id
    body = r.json()
    raw = r.text
    assert '"_id"' not in raw, f"_id leaked in {path}"
    assert body is not None


# ---------- POST: ash-pro/approve ----------
def test_ash_pro_approve(owner_session):
    plan = owner_session.get(f"{API}/v25/ash-pro/plan", timeout=60).json()
    plan_id = plan.get("id")
    actions = plan.get("actions") or []
    assert plan_id, f"Plan has no id: {plan}"
    # Approve whatever actions exist (empty actionIds = approve all)
    r = owner_session.post(
        f"{API}/v25/ash-pro/approve",
        json={"planId": plan_id, "actionIds": [a["id"] for a in actions]},
        timeout=30,
    )
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert "executed" in body and isinstance(body["executed"], int)
    assert "actions" in body and isinstance(body["actions"], list)


# ---------- POST: sites (owner) ----------
def test_create_site_owner(owner_session):
    payload = {"name": "TEST_SITE_v25", "city": "Melbourne"}
    r = owner_session.post(f"{API}/v25/sites", json=payload, timeout=30)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    assert data["name"] == payload["name"]
    assert data["city"] == payload["city"]
    assert "id" in data
    # Verify persistence
    sites = owner_session.get(f"{API}/v25/sites", timeout=30).json()
    assert any(s["id"] == data["id"] for s in sites), "Created site not persisted"


# ---------- POST: disputes ----------
def test_open_dispute(owner_session):
    payload = {"txId": "TEST_TX_001", "amount": 42.50, "reason": "fraud"}
    r = owner_session.post(f"{API}/v25/disputes", json=payload, timeout=30)
    assert r.status_code == 200, r.text[:200]
    d = r.json()
    assert d["txId"] == "TEST_TX_001"
    assert d["amount"] == 42.50
    assert d["status"] == "open"
    assert "id" in d


# ---------- POST: gift cards issue + redeem ----------
def test_gift_card_issue_and_redeem(owner_session):
    issue = owner_session.post(
        f"{API}/v25/gift-cards",
        json={"amount": 50, "recipientEmail": "TEST_buyer@example.com", "occasion": "birthday"},
        timeout=30,
    )
    assert issue.status_code == 200, issue.text[:200]
    card = issue.json()
    code = card.get("code")
    assert code, "gift card code missing"
    assert card.get("amount") == 50.0
    assert card.get("status") == "active"

    redeem = owner_session.post(
        f"{API}/v25/gift-cards/{code}/redeem", json={"amount": 20}, timeout=30
    )
    assert redeem.status_code == 200, redeem.text[:200]
    rj = redeem.json()
    assert rj.get("redeemed") == 20
    assert rj.get("code") == code


# ---------- POST: waste ----------
def test_record_waste(owner_session):
    payload = {"productId": "TEST_PROD", "productName": "TEST_item",
               "quantity": 3, "reason": "spoilage", "estCost": 13.5}
    r = owner_session.post(f"{API}/v25/waste", json=payload, timeout=30)
    assert r.status_code == 200, r.text[:200]
    w = r.json()
    assert w.get("quantity") == 3
    assert w.get("reason") == "spoilage"
    assert w.get("estCost") == 13.5


# ---------- POST: recipes/upsert ----------
def test_recipe_upsert(owner_session):
    # First, pick an existing product so the recipe links to something real
    prods = owner_session.get(f"{API}/products", timeout=30)
    if prods.status_code != 200 or not prods.json():
        pytest.skip("No products available to upsert recipe for")
    product = prods.json()[0]
    payload = {
        "productId": product["id"],
        "ingredients": [
            {"name": "TEST_flour", "qty": 0.2, "unit": "kg", "costPerUnit": 2.0},
            {"name": "TEST_sugar", "qty": 0.05, "unit": "kg", "costPerUnit": 3.0},
        ],
    }
    r = owner_session.post(f"{API}/v25/recipes/upsert", json=payload, timeout=30)
    assert r.status_code == 200, r.text[:200]
    rec = r.json()
    assert "computedCost" in rec or "cost" in rec, f"computedCost missing: {rec}"


# ---------- POST: predictive-orders ----------
def test_predictive_orders(owner_session):
    r = owner_session.post(f"{API}/v25/predictive-orders", json={"horizonDays": 7}, timeout=30)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert isinstance(body, (list, dict))


# ---------- POST: concierge (LLM) ----------
def test_concierge_llm(owner_session):
    r = owner_session.post(f"{API}/v25/concierge",
                           json={"message": "Do you have a vegan menu?", "customerId": "TEST_guest"},
                           timeout=90)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    # Tolerant: intent + reply expected, but allow LLM degraded mode
    assert "reply" in body or "intent" in body or "_error" in body, body


# ---------- POST: marketing/auto ----------
def test_marketing_auto(owner_session):
    r = owner_session.post(f"{API}/v25/marketing/auto",
                           json={"objective": "boost slow Tuesdays"}, timeout=90)
    assert r.status_code == 200, r.text[:200]


# ---------- POST: recovery/win-back ----------
def test_recovery_winback(owner_session):
    r = owner_session.post(f"{API}/v25/recovery/win-back",
                           json={"customerId": "TEST_guest"}, timeout=60)
    assert r.status_code == 200, r.text[:200]


# ---------- Sanity: unauthenticated requests are rejected ----------
def test_unauth_sites_rejected():
    r = requests.get(f"{API}/v25/sites", timeout=15)
    assert r.status_code in (401, 403), f"Unauthenticated /sites returned {r.status_code}"
