"""
Iteration 25 — v26 commerce regression suite.

Covers:
  - Unified gift voucher / gift-card lifecycle (mint pending → activate → partial redeem → ledger)
  - Idempotent activation, insufficient-balance guard, listing filters
  - Counter-channel gift-card sell (activates immediately + writes activate ledger)
  - AI marketing email generator, list, patch, delete
  - Auto-roster blackoutDates honouring + excluded[] reason
  - CFD push + enriched (live cart, customer/table/points)

Auth: owner@nua.com / NuaOwner2026!
"""
import os
import time
import uuid
import requests
import pytest

def _load_backend_url() -> str:
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        # Fall back to /app/frontend/.env (test environment)
        env_path = "/app/frontend/.env"
        if os.path.exists(env_path):
            with open(env_path) as fh:
                for line in fh:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
    assert url, "REACT_APP_BACKEND_URL is not configured"
    return url.rstrip("/")


BASE_URL = _load_backend_url()
OWNER_EMAIL = "owner@nua.com"
OWNER_PASSWORD = "NuaOwner2026!"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def owner_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    body = r.json()
    token = body.get("access_token") or body.get("token")
    assert token, f"no token in login response: {body}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def owner_user_id(owner_client):
    r = owner_client.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    return r.json().get("id")


# ---------------------------------------------------------------------------
# Gift Voucher → Gift Card lifecycle
# ---------------------------------------------------------------------------
class TestGiftCardLifecycle:
    voucher = None
    card = None
    code = None

    def test_01_create_gift_voucher_mints_pending_card(self, owner_client):
        payload = {
            "name": f"TEST_GiftVoucher_{uuid.uuid4().hex[:6]}",
            "kind": "gift",
            "value": 100,
            "bonus": 20,
            "recipientName": "Alice",
            "recipientEmail": "alice@test.local",
            "purchaserName": "Bob",
            "occasion": "birthday",
            "message": "Happy birthday",
        }
        r = owner_client.post(f"{BASE_URL}/api/v26/vouchers", json=payload)
        assert r.status_code == 200, r.text
        v = r.json()
        assert v["kind"] == "gift"
        assert v.get("manualCode") and v.get("barcode") == v["manualCode"]
        assert v.get("giftCard"), "giftCard payload missing on voucher response"
        card = v["giftCard"]
        assert card["status"] == "pending_activation"
        assert card["currentBalance"] == 0.0
        assert card["initialBalance"] == 100.0
        assert card["bonus"] == 20.0
        assert card["voucherId"] == v["id"]
        assert card["code"] == v["manualCode"]
        assert card["barcode"] == v["barcode"]
        TestGiftCardLifecycle.voucher = v
        TestGiftCardLifecycle.card = card
        TestGiftCardLifecycle.code = card["code"]

    def test_02_lookup_card_by_code_returns_pending(self, owner_client):
        code = TestGiftCardLifecycle.code
        r = owner_client.get(f"{BASE_URL}/api/v26/gift-cards/lookup/{code}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "pending_activation"
        assert body["currentBalance"] == 0.0
        assert body["initialBalance"] == 100.0

    def test_03_redeem_fails_while_pending(self, owner_client):
        code = TestGiftCardLifecycle.code
        r = owner_client.post(f"{BASE_URL}/api/v26/gift-cards/{code}/redeem",
                              json={"amount": 10})
        assert r.status_code == 400, r.text
        assert "pending_activation" in r.text.lower()

    def test_04_activate_transitions_to_active_and_writes_ledger(self, owner_client):
        code = TestGiftCardLifecycle.code
        r = owner_client.post(f"{BASE_URL}/api/v26/gift-cards/{code}/activate",
                              json={"transactionId": "TEST_TX_ACT_1"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["activated"] is True
        card = body["card"]
        assert card["status"] == "active"
        assert card["currentBalance"] == 120.0  # 100 + 20 bonus
        txn = body["transaction"]
        assert txn["type"] == "activate"
        assert txn["amount"] == 120.0
        assert txn["balanceBefore"] == 0.0
        assert txn["balanceAfter"] == 120.0

    def test_05_activate_is_idempotent(self, owner_client):
        code = TestGiftCardLifecycle.code
        r = owner_client.post(f"{BASE_URL}/api/v26/gift-cards/{code}/activate",
                              json={})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("alreadyActive") is True
        assert body["card"]["status"] == "active"
        assert body["card"]["currentBalance"] == 120.0

    def test_06_partial_redeem_decrements_balance(self, owner_client):
        code = TestGiftCardLifecycle.code
        r = owner_client.post(f"{BASE_URL}/api/v26/gift-cards/{code}/redeem",
                              json={"amount": 30, "transactionId": "TEST_TX_R1"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["redeemed"] == 30
        assert body["newBalance"] == 90.0
        assert body["transaction"]["type"] == "redeem"
        assert body["transaction"]["balanceBefore"] == 120.0
        assert body["transaction"]["balanceAfter"] == 90.0

    def test_07_second_partial_redeem(self, owner_client):
        code = TestGiftCardLifecycle.code
        r = owner_client.post(f"{BASE_URL}/api/v26/gift-cards/{code}/redeem",
                              json={"amount": 25, "transactionId": "TEST_TX_R2"})
        assert r.status_code == 200, r.text
        assert r.json()["newBalance"] == 65.0

    def test_08_insufficient_balance_returns_400(self, owner_client):
        code = TestGiftCardLifecycle.code
        r = owner_client.post(f"{BASE_URL}/api/v26/gift-cards/{code}/redeem",
                              json={"amount": 9999, "transactionId": "TEST_TX_FAIL"})
        assert r.status_code == 400, r.text
        assert "insufficient" in r.text.lower()

    def test_09_ledger_in_time_order(self, owner_client):
        code = TestGiftCardLifecycle.code
        r = owner_client.get(f"{BASE_URL}/api/v26/gift-cards/{code}/transactions")
        assert r.status_code == 200, r.text
        rows = r.json()
        # Expect at least: activate, redeem 30, redeem 25
        assert len(rows) >= 3
        assert rows[0]["type"] == "activate"
        redeems = [x for x in rows if x["type"] == "redeem"]
        assert len(redeems) >= 2
        # Ensure sorted ascending by createdAt
        timestamps = [r["createdAt"] for r in rows]
        assert timestamps == sorted(timestamps)
        # No mongo _id leak
        for row in rows:
            assert "_id" not in row

    def test_10_list_includes_card_and_status_filter(self, owner_client):
        code = TestGiftCardLifecycle.code
        r = owner_client.get(f"{BASE_URL}/api/v26/gift-cards")
        assert r.status_code == 200, r.text
        all_cards = r.json()
        assert any(c["code"] == code for c in all_cards)
        # filter active
        r2 = owner_client.get(f"{BASE_URL}/api/v26/gift-cards?status=active")
        assert r2.status_code == 200
        active = r2.json()
        assert all(c["status"] == "active" for c in active)
        assert any(c["code"] == code for c in active)


# ---------------------------------------------------------------------------
# Counter-channel sell (immediate activation)
# ---------------------------------------------------------------------------
class TestGiftCardSellCounter:
    def test_sell_counter_card_is_active_with_ledger(self, owner_client):
        r = owner_client.post(f"{BASE_URL}/api/v26/gift-cards/sell", json={
            "amount": 50,
            "channel": "counter",
            "purchaserName": "TEST_Counter",
            "paymentMethod": "cash",
        })
        assert r.status_code == 200, r.text
        card = r.json()
        assert card["status"] == "active"
        assert card["currentBalance"] == card["amount"]  # 50 + bonus (0 since <100)
        # ledger should have activate row
        code = card["code"]
        tx = owner_client.get(f"{BASE_URL}/api/v26/gift-cards/{code}/transactions").json()
        assert len(tx) >= 1
        assert tx[0]["type"] == "activate"
        assert tx[0]["balanceAfter"] == card["currentBalance"]


# ---------------------------------------------------------------------------
# Marketing email
# ---------------------------------------------------------------------------
class TestMarketingEmail:
    draft_id = None

    def test_01_generate_draft(self, owner_client):
        # Ensure at least one event/voucher exists (we just created vouchers above
        # so this should be safe — but guard anyway).
        r = owner_client.post(f"{BASE_URL}/api/v26/marketing/email/generate", json={
            "audience": "all", "tone": "friendly", "horizonDays": 30,
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("id", "").startswith("MKT-")
        assert body["status"] == "draft"
        # Non-empty draft
        assert body.get("subject"), "subject empty"
        assert body.get("emailBody"), "emailBody empty"
        assert body.get("sms"), "sms empty"
        assert body.get("cta"), "cta empty"
        TestMarketingEmail.draft_id = body["id"]

    def test_02_list_drafts_contains_new(self, owner_client):
        r = owner_client.get(f"{BASE_URL}/api/v26/marketing/emails")
        assert r.status_code == 200
        rows = r.json()
        assert any(row["id"] == TestMarketingEmail.draft_id for row in rows)
        for row in rows:
            assert "_id" not in row

    def test_03_patch_updates_field(self, owner_client):
        mid = TestMarketingEmail.draft_id
        r = owner_client.patch(f"{BASE_URL}/api/v26/marketing/emails/{mid}",
                               json={"subject": "TEST_Updated subject"})
        assert r.status_code == 200, r.text
        # verify by re-listing
        rows = owner_client.get(f"{BASE_URL}/api/v26/marketing/emails").json()
        match = next((x for x in rows if x["id"] == mid), None)
        assert match and match["subject"] == "TEST_Updated subject"

    def test_04_delete_owner_only(self, owner_client):
        mid = TestMarketingEmail.draft_id
        r = owner_client.delete(f"{BASE_URL}/api/v26/marketing/emails/{mid}")
        assert r.status_code == 200, r.text
        # verify removed
        rows = owner_client.get(f"{BASE_URL}/api/v26/marketing/emails").json()
        assert not any(x["id"] == mid for x in rows)


# ---------------------------------------------------------------------------
# Auto-roster blackout honouring
# ---------------------------------------------------------------------------
class TestAutoRosterBlackouts:
    test_staff_id = None
    test_staff_name = None

    def test_01_pick_a_staff_and_set_blackout(self, owner_client):
        # Pick a non-owner active staff member
        staffs = owner_client.get(f"{BASE_URL}/api/auth/staff").json()
        assert isinstance(staffs, list) and len(staffs) > 0, f"unexpected staff list response: {staffs}"
        target = next((s for s in staffs if s.get("role") != "owner"
                       and s.get("status", "active") == "active"), None)
        assert target, "no eligible non-owner staff for blackout test"
        TestAutoRosterBlackouts.test_staff_id = target["id"]
        TestAutoRosterBlackouts.test_staff_name = target.get("name")

        # week starts Monday 2026-06-08 → Tuesday 2026-06-09
        r = owner_client.put(
            f"{BASE_URL}/api/v26/staff/{target['id']}/availability",
            json={
                "weeklyAvailable": [],   # empty: no weekly restriction
                "blackoutDates": [
                    {"from": "2026-06-08", "to": "2026-06-09", "reason": "TEST_holiday"}
                ],
            },
        )
        assert r.status_code == 200, r.text

    def test_02_auto_roster_excludes_blackout_days(self, owner_client):
        r = owner_client.post(f"{BASE_URL}/api/staff/auto-roster",
                              json={"weekStart": "2026-06-08"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "suggestions" in body and "excluded" in body
        sid = TestAutoRosterBlackouts.test_staff_id
        # Staff should NOT appear in Monday/Tuesday suggestions
        for sug in body["suggestions"]:
            if sug["staffId"] == sid:
                assert sug["date"] not in ("Monday", "Tuesday"), (
                    f"Blacked-out staff scheduled on {sug['date']}")
        # And SHOULD appear in excluded[] for Monday + Tuesday with reason
        excl_days = {e["date"] for e in body["excluded"]
                     if e["staffId"] == sid}
        assert "Monday" in excl_days, f"Monday not in excluded: {body['excluded']}"
        assert "Tuesday" in excl_days, f"Tuesday not in excluded: {body['excluded']}"
        # Reason should reflect either 'TEST_holiday' or 'blackout'
        reasons = {e["reason"] for e in body["excluded"]
                   if e["staffId"] == sid}
        assert reasons & {"TEST_holiday", "blackout"}, reasons

    def test_99_teardown_clear_blackout(self, owner_client):
        sid = TestAutoRosterBlackouts.test_staff_id
        if not sid:
            return
        owner_client.put(f"{BASE_URL}/api/v26/staff/{sid}/availability",
                         json={"weeklyAvailable": [], "blackoutDates": []})


# ---------------------------------------------------------------------------
# CFD push + enriched
# ---------------------------------------------------------------------------
class TestCFD:
    def test_push_then_enriched(self, owner_client):
        terminal_id = f"TEST_TERM_{uuid.uuid4().hex[:6]}"
        cart = [
            {"productId": "P1", "name": "Latte", "price": 5, "quantity": 2},
            {"productId": "P2", "name": "Croissant", "price": 4, "quantity": 1},
        ]
        push = owner_client.post(f"{BASE_URL}/api/v26/cfd/push", json={
            "terminalId": terminal_id,
            "cart": cart,
            "selectedCustomer": {"id": "CUST1", "name": "TEST_Diana",
                                 "membershipTier": "Gold"},
            "tableNumber": 7,
        })
        assert push.status_code == 200, push.text

        r = owner_client.get(f"{BASE_URL}/api/v26/cfd/enriched",
                             params={"terminalId": terminal_id})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["customerName"] == "TEST_Diana"
        assert body["tableNumber"] == 7
        assert body["subtotal"] == 14.0
        # pointsEarned must be a non-negative int
        assert isinstance(body["pointsEarned"], int)
        assert body["pointsEarned"] >= 0
        assert body["isMember"] is True
        # cart fully echoed
        assert len(body["cart"]) == 2
