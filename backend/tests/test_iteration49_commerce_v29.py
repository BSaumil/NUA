"""Iteration 49 — Customer Commerce Platform (v29) backend tests.

Covers:
 - Universal Voucher Engine (issue, bulk, list, lookup, validate, redeem,
   duplicate guard, revoke).
 - Unified Wallet Ledger (get, credit, debit, insufficient guard, timeline).
 - Flexible Refund Engine (splits: store_credit + points).
 - AI Promotion Builder (LLM or heuristic fallback).
 - Loyalty 2.0 status (tiers, milestones, streaks, badges).
 - AI Personalisation.
 - Gift Card 2.0 (scheduled + reload).
 - Promotion Analytics summary.
 - Regression check: legacy /gift-cards buy endpoint still works.
"""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@nua.com"
OWNER_PASSWORD = "NuaOwner2026!"
CUSTOMER_ID = "cust-1"  # Sarah Johnson (seeded)

# Shared state between voucher tests (module-level, survives across tests in class)
STATE: dict = {}


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="session")
def owner_token():
    r = requests.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text}"
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture
def client(owner_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"})
    return s


# ═══════════════════════════════════════════════════════════════════════
# Universal Voucher Engine
# ═══════════════════════════════════════════════════════════════════════
class TestVouchers:
    def test_issue_amount_voucher(self, client):
        body = {
            "label": "TEST_iter49 partial voucher",
            "valueType": "amount",
            "value": 25,
            "usageType": "one_time",
            "partialRedeemable": True,
        }
        r = client.post(f"{API}/vouchers", json=body)
        assert r.status_code == 200, r.text
        v = r.json()
        assert v.get("id")
        assert v.get("code", "").startswith("NUA-") and len(v["code"]) == 13  # NUA-XXXX-XXXX
        assert v.get("qrPayload") and "." in v["qrPayload"]
        assert v["value"] == 25.0
        assert v["residualValue"] == 25.0
        assert v["status"] == "active"
        # Cache for downstream tests
        STATE["voucher"] = v

    def test_bulk_issue(self, client):
        r = client.post(f"{API}/vouchers/bulk", json={
            "count": 3, "label": "TEST_iter49 Corporate",
            "valueType": "amount", "value": 10,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["issued"] == 3
        codes = {v["code"] for v in data["vouchers"]}
        assert len(codes) == 3  # all unique
        for c in codes:
            assert c.startswith("NUA-")

    def test_list_vouchers(self, client):
        r = client.get(f"{API}/vouchers")
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        assert any(v.get("id") == STATE["voucher"]["id"] for v in rows)

    def test_lookup_code(self, client):
        v = STATE["voucher"]
        r = client.get(f"{API}/vouchers/lookup/{v['code']}")
        assert r.status_code == 200
        assert r.json()["id"] == v["id"]

    def test_validate_by_code(self, client):
        v = STATE["voucher"]
        r = client.post(f"{API}/vouchers/validate", json={"code": v["code"]})
        assert r.status_code == 200
        assert r.json()["valid"] is True

    def test_validate_by_token(self, client):
        v = STATE["voucher"]
        r = client.post(f"{API}/vouchers/validate", json={"token": v["qrPayload"]})
        assert r.status_code == 200
        assert r.json()["valid"] is True

    def test_redeem_transitions_partial(self, client):
        v = STATE["voucher"]
        tx_id = f"TEST_iter49-tx-{uuid.uuid4().hex[:6]}"
        r = client.post(f"{API}/vouchers/redeem", json={
            "code": v["code"], "amount": 10, "transactionId": tx_id,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["amountApplied"] == 10.0
        assert data["voucher"]["status"] == "partial"
        assert data["voucher"]["residualValue"] == 15.0
        assert data["voucher"]["redemptionCount"] == 1
        STATE["tx_id"] = tx_id

    def test_redeem_duplicate_guard(self, client):
        v = STATE["voucher"]
        r = client.post(f"{API}/vouchers/redeem", json={
            "code": v["code"], "amount": 5, "transactionId": STATE["tx_id"],
        })
        assert r.status_code == 409, f"Expected 409 on duplicate, got {r.status_code} {r.text}"

    def test_redeem_to_full(self, client):
        v = STATE["voucher"]
        # Redeem remaining 15 with a new transactionId
        r = client.post(f"{API}/vouchers/redeem", json={
            "code": v["code"], "amount": 15,
            "transactionId": f"TEST_iter49-tx2-{uuid.uuid4().hex[:6]}",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["voucher"]["status"] == "redeemed"
        assert data["voucher"]["residualValue"] == 0.0

    def test_redeem_after_full_rejected(self, client):
        v = STATE["voucher"]
        r = client.post(f"{API}/vouchers/redeem", json={
            "code": v["code"], "amount": 5,
            "transactionId": f"TEST_iter49-tx3-{uuid.uuid4().hex[:6]}",
        })
        assert r.status_code == 400
        assert "redeemed" in r.text.lower() or "residual" in r.text.lower()

    def test_revoke_voucher(self, client):
        # Fresh voucher for revoke path
        r = client.post(f"{API}/vouchers", json={
            "label": "TEST_iter49 revoke", "valueType": "amount", "value": 5,
        })
        assert r.status_code == 200
        vid = r.json()["id"]
        code = r.json()["code"]
        r = client.post(f"{API}/vouchers/{vid}/revoke", json={"reason": "test"})
        assert r.status_code == 200
        # Verify status
        r = client.get(f"{API}/vouchers/{vid}")
        assert r.status_code == 200
        v = r.json()
        assert v["status"] == "revoked"
        assert v.get("revokedBy") == OWNER_EMAIL
        assert v.get("revokedAt")
        # Redeem after revoke → 400
        r = client.post(f"{API}/vouchers/redeem", json={
            "code": code, "amount": 5,
            "transactionId": f"TEST_iter49-revtx-{uuid.uuid4().hex[:6]}",
        })
        assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════════════
# Wallet
# ═══════════════════════════════════════════════════════════════════════
class TestWallet:
    def test_get_wallet_structure(self, client):
        r = client.get(f"{API}/wallet/{CUSTOMER_ID}")
        assert r.status_code == 200, r.text
        w = r.json()
        assert w["customerId"] == CUSTOMER_ID
        for bucket in ("points", "store_credit", "gift_card", "voucher", "cashback", "referral"):
            assert bucket in w["balances"]
        assert "vouchers" in w
        assert "expiringSoon" in w
        assert "recentEntries" in w

    def test_credit_and_debit_wallet(self, client):
        # Credit $20 store_credit
        r = client.post(f"{API}/wallet/{CUSTOMER_ID}/credit", json={
            "customerId": CUSTOMER_ID, "type": "store_credit", "amount": 20,
            "sourceType": "manual", "note": "TEST_iter49 credit",
        })
        assert r.status_code == 200, r.text
        entry = r.json()
        assert entry["type"] == "store_credit"
        assert entry["sign"] == 1
        assert entry["balanceAfter"] is not None
        prev_bal = entry["balanceAfter"]

        # Debit $5
        r = client.post(f"{API}/wallet/{CUSTOMER_ID}/debit", json={
            "customerId": CUSTOMER_ID, "type": "store_credit", "amount": 5,
            "sourceType": "manual", "note": "TEST_iter49 debit",
        })
        assert r.status_code == 200, r.text
        entry = r.json()
        assert entry["sign"] == -1
        assert entry["balanceAfter"] == round(prev_bal - 5, 2)

    def test_debit_insufficient_balance(self, client):
        # Try to debit $999,999 gift_card (no balance)
        r = client.post(f"{API}/wallet/{CUSTOMER_ID}/debit", json={
            "customerId": CUSTOMER_ID, "type": "gift_card", "amount": 999999,
            "sourceType": "manual",
        })
        assert r.status_code == 400
        assert "insufficient" in r.text.lower()

    def test_timeline(self, client):
        r = client.get(f"{API}/wallet/{CUSTOMER_ID}/timeline")
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["customerId"] == CUSTOMER_ID
        assert "events" in t and isinstance(t["events"], list)
        assert "lifetimeValue" in t
        assert "totalOrders" in t
        # Sorted DESC by 'at'
        ats = [e["at"] for e in t["events"] if e.get("at")]
        assert ats == sorted(ats, reverse=True)


# ═══════════════════════════════════════════════════════════════════════
# Flexible Refund
# ═══════════════════════════════════════════════════════════════════════
class TestRefunds:
    def test_flexible_refund_splits(self, client):
        r = client.post(f"{API}/refunds/flexible", json={
            "customerId": CUSTOMER_ID,
            "amount": 10,
            "reason": "TEST_iter49 refund",
            "splits": [
                {"mode": "store_credit", "amount": 6},
                {"mode": "points", "amount": 4, "pointsPerDollar": 10},
            ],
        })
        assert r.status_code == 200, r.text
        rf = r.json()
        assert rf["status"] == "completed"
        assert len(rf["splits"]) == 2
        modes = {s["mode"] for s in rf["splits"]}
        assert modes == {"store_credit", "points"}
        points_split = next(s for s in rf["splits"] if s["mode"] == "points")
        assert points_split["pointsAwarded"] == 40.0

    def test_split_sum_mismatch_rejected(self, client):
        r = client.post(f"{API}/refunds/flexible", json={
            "customerId": CUSTOMER_ID,
            "amount": 10,
            "splits": [{"mode": "store_credit", "amount": 8}],
        })
        assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════════════
# AI Promotion Builder
# ═══════════════════════════════════════════════════════════════════════
class TestAIPromoBuilder:
    def test_promotion_goal(self, client):
        r = client.post(f"{API}/ai/promotion-goal", json={"goal": "Boost Tuesday lunch"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("name")
        assert data.get("voucherTemplate")
        assert data.get("rules")
        # heuristic Tuesday route should include activeDays
        if data.get("source") == "heuristic":
            assert "Tuesday" in data["rules"].get("activeDays", [])
        assert data.get("smsCopy")
        assert data.get("emailBody")
        assert data.get("estimatedROI") is not None

    def test_empty_goal_rejected(self, client):
        r = client.post(f"{API}/ai/promotion-goal", json={"goal": ""})
        assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════════════
# Loyalty 2.0
# ═══════════════════════════════════════════════════════════════════════
class TestLoyalty:
    def test_loyalty_status(self, client):
        r = client.get(f"{API}/loyalty/status/{CUSTOMER_ID}")
        assert r.status_code == 200, r.text
        s = r.json()
        assert s["customerId"] == CUSTOMER_ID
        assert s["tier"] in ("Bronze", "Silver", "Gold", "Platinum", "VIP")
        assert "totalVisits" in s
        assert "totalSpend" in s
        assert "streakWeeks" in s
        assert "milestones" in s and len(s["milestones"]) >= 1
        for m in s["milestones"]:
            assert "achieved" in m and "progress" in m
        assert "badges" in s
        assert "tierProgressPct" in s


# ═══════════════════════════════════════════════════════════════════════
# AI Personalisation
# ═══════════════════════════════════════════════════════════════════════
class TestPersonalisation:
    def test_personalisation(self, client):
        r = client.get(f"{API}/personalisation/{CUSTOMER_ID}")
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["customerId"] == CUSTOMER_ID
        assert "insights" in p
        for key in ("favouriteItems", "typicalVisitHour", "typicalWeekday", "daysSinceLastVisit", "averageCheck"):
            assert key in p["insights"]
        assert "recommendations" in p
        assert isinstance(p["recommendations"], list)


# ═══════════════════════════════════════════════════════════════════════
# Gift Card 2.0
# ═══════════════════════════════════════════════════════════════════════
class TestGiftCards:
    def test_schedule_and_reload(self, client):
        # Schedule
        r = client.post(f"{API}/gift-cards/schedule", json={
            "amount": 50, "recipientCustomerId": CUSTOMER_ID,
            "recipientEmail": "TEST_iter49@example.com",
            "recipientName": "Test Recipient",
            "senderName": "Test Sender",
            "personalMessage": "Happy Birthday",
            "deliverAt": "2026-12-01T09:00:00Z",
        })
        assert r.status_code == 200, r.text
        gc = r.json()
        assert gc.get("id")
        assert gc.get("sourceType") == "gift_card"
        assert gc.get("value") == 50.0
        assert gc.get("metadata", {}).get("deliverAt") == "2026-12-01T09:00:00Z"

        # Reload +$25
        r = client.post(f"{API}/gift-cards/{gc['id']}/reload", json={"amount": 25})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["newBalance"] >= 75.0

        # Verify persisted increments
        r = client.get(f"{API}/vouchers/{gc['id']}")
        assert r.status_code == 200
        v = r.json()
        assert v["value"] == 75.0
        assert v["faceValue"] == 75.0
        assert v["residualValue"] == 75.0


# ═══════════════════════════════════════════════════════════════════════
# Promotion Analytics
# ═══════════════════════════════════════════════════════════════════════
class TestPromoAnalytics:
    def test_summary(self, client):
        r = client.get(f"{API}/promo-analytics/summary?days=30")
        assert r.status_code == 200, r.text
        s = r.json()
        for key in ("issued", "redeemed", "redemptionRate", "faceValueIssued", "revenueGenerated", "bySource"):
            assert key in s
        assert isinstance(s["bySource"], dict)
        assert s["issued"] >= 1  # this test session issued vouchers


# ═══════════════════════════════════════════════════════════════════════
# Regression
# ═══════════════════════════════════════════════════════════════════════
class TestRegression:
    def test_legacy_gift_card_endpoint(self, client):
        # v26 gift-cards list — must still be alive
        r = client.get(f"{API}/gift-cards")
        assert r.status_code == 200, f"Legacy /api/gift-cards list broken: {r.status_code} {r.text}"
        assert isinstance(r.json(), list)
