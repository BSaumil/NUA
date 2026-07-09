"""Iteration 50 — targeted retest of 3 bug fixes from iter49.

Fixes under retest:
  (1) voucher partial-redeem allows N partials until residual=0
      - $30 voucher, partialRedeemable=True, usageType=one_time
      - $10 → $12 → $8 all succeed; residuals 20 → 8 → 0
      - statuses: partial → partial → redeemed
  (2) duplicate transactionId returns 409 (NOT 400 "max reached"),
      even after a partial has been consumed.
  (3) GET /api/transactions returns 200 (was 500).
      GET /api/gift-cards returns 200 (was 500).
"""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@nuva.com"
OWNER_PASSWORD = "NuvaOwner2026!"


@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text}"
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture
def client(owner_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {owner_token}",
                      "Content-Type": "application/json"})
    return s


# ═══════════════════════════════════════════════════════════════════════
# Bug fix (1) + (2): partial redemption chain + duplicate 409
# ═══════════════════════════════════════════════════════════════════════
class TestVoucherPartialChain:
    """$30 voucher; three partial redeems ($10, $12, $8) → residual 0."""

    def _issue(self, client, value=30):
        r = client.post(f"{API}/vouchers", json={
            "label": "TEST_iter50_partial_chain",
            "valueType": "amount", "value": value,
            "usageType": "one_time",
            "partialRedeemable": True,
        })
        assert r.status_code == 200, r.text
        v = r.json()
        assert v["value"] == float(value)
        assert v["residualValue"] == float(value)
        assert v["status"] == "active"
        return v

    def test_three_partials_and_dup_and_after_full(self, client):
        v = self._issue(client, 30)
        code = v["code"]

        # ── partial #1 ($10) ──
        tx1 = f"TEST_iter50-tx1-{uuid.uuid4().hex[:6]}"
        r = client.post(f"{API}/vouchers/redeem",
                        json={"code": code, "amount": 10, "transactionId": tx1})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["amountApplied"] == 10.0
        assert d["voucher"]["status"] == "partial"
        assert d["voucher"]["residualValue"] == 20.0
        assert d["voucher"]["redemptionCount"] == 1

        # ── partial #2 ($12) — this was broken pre-fix ──
        tx2 = f"TEST_iter50-tx2-{uuid.uuid4().hex[:6]}"
        r = client.post(f"{API}/vouchers/redeem",
                        json={"code": code, "amount": 12, "transactionId": tx2})
        assert r.status_code == 200, \
            f"2nd partial rejected — partial-redeem fix regressed: {r.status_code} {r.text}"
        d = r.json()
        assert d["amountApplied"] == 12.0
        assert d["voucher"]["status"] == "partial"
        assert d["voucher"]["residualValue"] == 8.0
        assert d["voucher"]["redemptionCount"] == 2

        # ── duplicate transactionId (tx2 again) → 409 (bug fix #2) ──
        r = client.post(f"{API}/vouchers/redeem",
                        json={"code": code, "amount": 3, "transactionId": tx2})
        assert r.status_code == 409, \
            f"Expected 409 on dup transactionId, got {r.status_code} {r.text}"
        assert "already applied" in r.text.lower() or "duplicate" in r.text.lower() \
               or "409" in str(r.status_code)

        # ── partial #3 ($8) drains to 0 ──
        tx3 = f"TEST_iter50-tx3-{uuid.uuid4().hex[:6]}"
        r = client.post(f"{API}/vouchers/redeem",
                        json={"code": code, "amount": 8, "transactionId": tx3})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["amountApplied"] == 8.0
        assert d["voucher"]["status"] == "redeemed"
        assert d["voucher"]["residualValue"] == 0.0
        assert d["voucher"]["redemptionCount"] == 3

        # ── attempt after fully redeemed → 400 (not 409) ──
        tx4 = f"TEST_iter50-tx4-{uuid.uuid4().hex[:6]}"
        r = client.post(f"{API}/vouchers/redeem",
                        json={"code": code, "amount": 1, "transactionId": tx4})
        assert r.status_code == 400, r.text


# ═══════════════════════════════════════════════════════════════════════
# Bug fix (3): legacy list endpoints now 200
# ═══════════════════════════════════════════════════════════════════════
class TestLegacyListEndpoints:
    def test_transactions_list_200(self, client):
        r = client.get(f"{API}/transactions")
        assert r.status_code == 200, f"GET /api/transactions still broken: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert isinstance(data, list)
        # each row must be JSON-serialisable (no ObjectId leak)
        for row in data[:5]:
            assert "_id" not in row

    def test_transactions_list_with_filters_200(self, client):
        r = client.get(f"{API}/transactions",
                       params={"payment_method": "card"})
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_gift_cards_list_200(self, client):
        r = client.get(f"{API}/gift-cards")
        assert r.status_code == 200, f"GET /api/gift-cards still broken: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert isinstance(data, list)
        for row in data[:5]:
            assert "_id" not in row


# ═══════════════════════════════════════════════════════════════════════
# Broad regression on other v29 endpoints
# ═══════════════════════════════════════════════════════════════════════
class TestV29Regression:
    def test_list_vouchers_still_ok(self, client):
        r = client.get(f"{API}/vouchers")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_wallet_endpoint(self, client):
        r = client.get(f"{API}/wallet/cust-1")
        assert r.status_code == 200
        w = r.json()
        assert w["customerId"] == "cust-1"
        assert "balances" in w

    def test_loyalty_status(self, client):
        r = client.get(f"{API}/loyalty/status/cust-1")
        assert r.status_code == 200
        assert "tier" in r.json()

    def test_personalisation(self, client):
        r = client.get(f"{API}/personalisation/cust-1")
        assert r.status_code == 200
        assert "recommendations" in r.json()

    def test_promo_analytics(self, client):
        r = client.get(f"{API}/promo-analytics/summary?days=30")
        assert r.status_code == 200
        assert "issued" in r.json()

    def test_wallet_timeline(self, client):
        r = client.get(f"{API}/wallet/cust-1/timeline")
        assert r.status_code == 200
        assert "events" in r.json()

    def test_ai_promotion_goal(self, client):
        r = client.post(f"{API}/ai/promotion-goal", json={"goal": "Boost Tuesday lunch"})
        assert r.status_code == 200
        assert r.json().get("name")
