"""
Iteration 52 — Foundational refactor tests.
Covers: Ash insights (16 capabilities), Approval Queue, Universal Audit,
Entity versioning + soft-delete, HQ roll-up.
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER = {"email": "owner@nuva.com", "password": "NuvaOwner2026!"}


# ── fixtures ─────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json=OWNER, timeout=30)
    assert r.status_code == 200, r.text
    return r.json().get("access_token") or r.json().get("token")


@pytest.fixture(scope="session")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


# ── Ash ──────────────────────────────────────────────────────────────────
class TestAsh:
    def test_capabilities_16(self, client):
        r = client.get(f"{API}/ash/capabilities", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "capabilities" in data
        assert len(data["capabilities"]) == 16, f"Expected 16 got {len(data['capabilities'])}"

    def test_run_and_list_insights(self, client):
        r = client.post(f"{API}/ash/run", timeout=60)
        assert r.status_code == 200, r.text
        j = r.json()
        assert "generated" in j
        # list
        r2 = client.get(f"{API}/ash/insights", timeout=30)
        assert r2.status_code == 200
        rows = r2.json()
        assert isinstance(rows, list)

    def test_weekly_summary(self, client):
        r = client.post(f"{API}/ash/summary/weekly", timeout=90)
        assert r.status_code == 200, r.text
        doc = r.json()
        assert doc is not None
        assert doc.get("category") == "summary"
        assert doc.get("body")
        data = doc.get("data") or {}
        assert "revenue" in data and "covers" in data

    def test_insights_summary_shape(self, client):
        r = client.get(f"{API}/ash/insights/summary", timeout=30)
        assert r.status_code == 200
        j = r.json()
        for k in ("total", "high", "warning", "byCategory"):
            assert k in j
        assert isinstance(j["byCategory"], dict)

    def test_dismiss_insight(self, client):
        # get any active insight
        rows = client.get(f"{API}/ash/insights?include_resolved=false", timeout=30).json()
        if not rows:
            # trigger a run to create some
            client.post(f"{API}/ash/run", timeout=60)
            rows = client.get(f"{API}/ash/insights?include_resolved=false", timeout=30).json()
        if not rows:
            pytest.skip("No active insights to dismiss")
        target = rows[0]
        iid = target["id"]
        r = client.post(f"{API}/ash/insights/{iid}/dismiss", timeout=30)
        assert r.status_code == 200
        # Verify no longer in default list
        after = client.get(f"{API}/ash/insights?include_resolved=false", timeout=30).json()
        assert not any(x["id"] == iid for x in after)


# ── Approvals ────────────────────────────────────────────────────────────
class TestApprovals:
    def test_policy(self, client):
        r = client.get(f"{API}/approvals/config/policy", timeout=15)
        assert r.status_code == 200
        j = r.json()
        for k in ("mode", "poAbove", "refundAbove", "tierDowngradesAlwaysApprove"):
            assert k in j

    def _make_rule(self, client, name, estimated_cost):
        rule = {
            "name": name,
            "triggerEvent": "inventory.low_stock",
            "active": True,
            "conditions": {"mode": "all", "clauses": []},
            "actions": [{
                "type": "create_purchase_order",
                "params": {"productId": f"TEST_iter52_{uuid.uuid4()}", "quantity": 1,
                           "estimatedCost": estimated_cost}
            }],
        }
        r = client.post(f"{API}/rules", json=rule, timeout=15)
        assert r.status_code in (200, 201), r.text
        return r.json()

    def test_large_po_requires_approval_and_execute(self, client):
        rule = self._make_rule(client, f"TEST_iter52_big_{uuid.uuid4()}", 999)
        # emit
        emit_body = {"eventType": "inventory.low_stock", "payload": {"productId": "TEST_iter52_p", "productName": "TP", "stock": 0, "threshold": 5}}
        r = client.post(f"{API}/rules/emit", json=emit_body, timeout=30)
        assert r.status_code == 200, r.text
        firings = r.json().get("ruleFirings", [])
        mine = [f for f in firings if f.get("ruleId") == rule["id"]]
        assert mine, f"Rule did not fire. Firings: {firings}"
        outcomes = mine[0].get("outcomes") or []
        assert outcomes
        result = outcomes[0].get("result") or {}
        assert result.get("status") == "pending_approval", f"Expected pending_approval, got {result}"
        approval_id = result.get("approvalId")
        assert approval_id

        # Approve
        r2 = client.post(f"{API}/approvals/{approval_id}/approve", json={}, timeout=30)
        assert r2.status_code == 200, r2.text
        approved = r2.json()
        assert approved["status"] == "approved"
        outcome = approved.get("outcome") or {}
        assert outcome.get("purchaseOrderId"), f"No purchaseOrderId in outcome: {outcome}"

        # list approved
        r3 = client.get(f"{API}/approvals?status=approved", timeout=15)
        assert r3.status_code == 200
        assert any(a["id"] == approval_id for a in r3.json())

    def test_small_po_no_approval(self, client):
        rule = self._make_rule(client, f"TEST_iter52_small_{uuid.uuid4()}", 100)
        emit_body = {"eventType": "inventory.low_stock", "payload": {"productId": "TEST_iter52_p_small"}}
        r = client.post(f"{API}/rules/emit", json=emit_body, timeout=30)
        assert r.status_code == 200
        firings = r.json().get("ruleFirings", [])
        mine = [f for f in firings if f.get("ruleId") == rule["id"]]
        assert mine
        outcomes = mine[0].get("outcomes") or []
        result = outcomes[0].get("result") or {}
        # For small PO — no approval; result is {status:executed, outcome:{purchaseOrderId:...}}
        assert result.get("status") == "executed", f"Expected executed, got {result}"
        assert (result.get("outcome") or {}).get("purchaseOrderId")

    def test_reject_flow(self, client):
        rule = self._make_rule(client, f"TEST_iter52_reject_{uuid.uuid4()}", 1200)
        emit_body = {"eventType": "inventory.low_stock", "payload": {"productId": "TEST_iter52_p_rej"}}
        r = client.post(f"{API}/rules/emit", json=emit_body, timeout=30)
        outcomes = r.json()["ruleFirings"][0]["outcomes"]
        approval_id = outcomes[0]["result"]["approvalId"]
        r2 = client.post(f"{API}/approvals/{approval_id}/reject",
                          json={"reason": "TEST_iter52 not this week"}, timeout=15)
        assert r2.status_code == 200
        j = r2.json()
        assert j["status"] == "rejected"
        assert j["resolvedBy"]


# ── Audit ────────────────────────────────────────────────────────────────
class TestAudit:
    def test_events_list_shape(self, client):
        r = client.get(f"{API}/audit/events?limit=50", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        if rows:
            row = rows[0]
            for k in ("id", "entityType", "entityId", "action", "actor", "ts"):
                assert k in row, f"missing {k} in audit row: {row}"

    def test_transaction_creates_audit_event(self, client):
        # Post a POS sale
        txn = {"items": [{"productId": "TEST_iter52", "productName": "TEST_iter52 item",
                          "name": "TEST_iter52 item", "price": 5.0, "quantity": 1}],
                "total": 5.0, "paymentMethod": "cash", "location": "Main", "cashier": "owner@nuva.com"}
        r = client.post(f"{API}/transactions", json=txn, timeout=30)
        assert r.status_code in (200, 201), r.text
        time.sleep(1)
        r2 = client.get(f"{API}/audit/events?entity_type=transaction&limit=20", timeout=15)
        assert r2.status_code == 200
        rows = r2.json()
        assert any(row.get("action") == "created" for row in rows), "No transaction:created event"

    def test_summary_shape(self, client):
        r = client.get(f"{API}/audit/summary", timeout=30)
        assert r.status_code == 200
        j = r.json()
        for k in ("byAction", "byEntity", "byActor", "total"):
            assert k in j
        assert isinstance(j["byAction"], list)

    def test_customer_create_audit_and_history(self, client):
        payload = {"name": "TEST_iter52 Cust", "email": f"TEST_iter52_{uuid.uuid4()}@ex.com", "phone": "555"}
        r = client.post(f"{API}/customers", json=payload, timeout=15)
        assert r.status_code in (200, 201), r.text
        cust = r.json()
        cid = cust["id"]
        time.sleep(1)
        # audit event
        r2 = client.get(f"{API}/audit/events?entity_type=customer&entity_id={cid}", timeout=15)
        assert r2.status_code == 200
        rows = r2.json()
        created = [x for x in rows if x.get("action") == "created"]
        assert created, f"No customer:created event, rows: {rows}"
        assert created[0]["actor"] in ("owner@nuva.com", "system"), created[0]
        # Update
        r3 = client.put(f"{API}/customers/{cid}", json={"name": "TEST_iter52 Cust Updated"}, timeout=15)
        assert r3.status_code == 200, r3.text
        time.sleep(1)
        # history
        r4 = client.get(f"{API}/audit/history/customer/{cid}?collection=customers", timeout=15)
        assert r4.status_code == 200, r4.text
        h = r4.json()
        assert "versions" in h and "audit" in h
        assert len(h["versions"]) >= 1, f"Expected version snapshot, got {h}"

    def test_product_soft_delete(self, client):
        # create
        payload = {"name": f"TEST_iter52 Prod {uuid.uuid4()}", "price": 9.0, "cost": 3.0,
                    "sku": f"TEST_iter52_{uuid.uuid4().hex[:8]}", "category": "test", "stock": 10}
        r = client.post(f"{API}/products", json=payload, timeout=15)
        assert r.status_code in (200, 201), r.text
        pid = r.json()["id"]
        # delete
        rd = client.delete(f"{API}/products/{pid}", timeout=15)
        assert rd.status_code in (200, 204), rd.text
        # Default list excludes it
        r2 = client.get(f"{API}/products", timeout=15)
        assert r2.status_code == 200
        assert not any(p["id"] == pid for p in r2.json()), "Soft-deleted product should not appear by default"


# ── HQ ───────────────────────────────────────────────────────────────────
class TestHQ:
    def test_kpi_rollup(self, client):
        r = client.get(f"{API}/hq/kpi-roll-up?days=30", timeout=30)
        assert r.status_code == 200, r.text
        j = r.json()
        assert "totalRevenue" in j and "locations" in j
        assert isinstance(j["locations"], list)

    def test_leaderboard(self, client):
        r = client.get(f"{API}/hq/leaderboard", timeout=30)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        if rows:
            assert "rank" in rows[0] and "location" in rows[0] and "revenue" in rows[0]
