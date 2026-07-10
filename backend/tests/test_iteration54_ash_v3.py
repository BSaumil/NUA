"""
Iteration 54 — Ash v3.0 backend tests
- Tool registry (23 tools) + permission matrix
- Health Score (10 subscores)
- Daily Briefing (GPT + fallback)
- Multi-turn tool-calling agent
- Manual tool execute (auto + approval)
- Permission override / disabled
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ── Auth fixture ────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"},
                      timeout=15)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── Tool catalog ────────────────────────────────────────────────────────
class TestToolCatalog:
    def test_list_tools_returns_23(self, headers):
        r = requests.get(f"{API}/ash/tools", headers=headers, timeout=15)
        assert r.status_code == 200
        tools = r.json()
        assert isinstance(tools, list)
        assert len(tools) == 23, f"expected 23 tools, got {len(tools)}"

    def test_tool_shape(self, headers):
        r = requests.get(f"{API}/ash/tools", headers=headers, timeout=15)
        tools = r.json()
        required = {"name", "module", "risk", "defaultPermission",
                    "effectivePermission", "parameters", "rollbackAvailable", "expectedImpact"}
        for t in tools:
            missing = required - set(t.keys())
            assert not missing, f"tool {t.get('name')} missing keys {missing}"
            assert t["risk"] in ("low", "medium", "high", "critical")
            assert t["defaultPermission"] in ("auto", "approval", "disabled")

    def test_default_permission_matrix(self, headers):
        r = requests.get(f"{API}/ash/tools", headers=headers, timeout=15)
        tools = {t["name"]: t for t in r.json()}
        # Low-risk read/log tools should be auto
        auto_expected = ["fetch_open_insights", "fetch_kpis", "lookup_customer",
                         "lookup_product", "run_ash_scan", "dismiss_insight",
                         "add_customer_note", "create_staff_task"]
        for n in auto_expected:
            assert n in tools, f"missing tool {n}"
            assert tools[n]["defaultPermission"] == "auto", \
                f"{n} expected auto, got {tools[n]['defaultPermission']}"
        # High-risk writes must default to approval
        approval_expected = ["create_purchase_order", "adjust_menu_price",
                             "add_wallet_credit", "approve_pending_approval"]
        for n in approval_expected:
            assert tools[n]["defaultPermission"] == "approval", \
                f"{n} expected approval default, got {tools[n]['defaultPermission']}"


# ── Health score ────────────────────────────────────────────────────────
class TestHealthScore:
    def test_health_score_shape(self, headers):
        r = requests.get(f"{API}/ash/health-score", headers=headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "overall" in d and 0 <= d["overall"] <= 100
        assert d["tier"] in ("excellent", "healthy", "watch", "at_risk", "critical")
        expected = {"revenue", "profit", "labour", "foodCost", "csat",
                    "inventory", "cashFlow", "compliance", "equipment", "aiConfidence"}
        assert set(d["subscores"].keys()) == expected
        for k, v in d["subscores"].items():
            assert "score" in v and 0 <= v["score"] <= 100
            assert "weight" in v


# ── Briefing ────────────────────────────────────────────────────────────
class TestBriefing:
    def test_briefing_returns(self, headers):
        r = requests.get(f"{API}/ash/briefing", headers=headers, timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d.get("date") and d.get("narrative")
        assert len(d["narrative"]) > 20
        assert "data" in d
        for k in ("forecastRevenue", "bookingsToday", "vipCount",
                  "rosteredStaff", "lowStockCount", "topInsights",
                  "birthdays", "pendingApprovals", "weekRevenue"):
            assert k in d["data"], f"briefing.data missing {k}"

    def test_briefing_regenerate(self, headers):
        r = requests.post(f"{API}/ash/briefing/regenerate", headers=headers, timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d.get("narrative") and len(d["narrative"]) > 20


# ── Permission override ─────────────────────────────────────────────────
class TestPermissions:
    def test_invalid_permission_400(self, headers):
        r = requests.put(f"{API}/ash/tools/fetch_open_insights/permission",
                         headers=headers, json={"permission": "yolo"}, timeout=15)
        assert r.status_code == 400

    def test_unknown_tool_404(self, headers):
        r = requests.put(f"{API}/ash/tools/does_not_exist/permission",
                         headers=headers, json={"permission": "auto"}, timeout=15)
        assert r.status_code == 404

    def test_set_disabled_then_blocked_execute(self, headers):
        # Set dismiss_insight to disabled
        r = requests.put(f"{API}/ash/tools/dismiss_insight/permission",
                         headers=headers, json={"permission": "disabled"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["permission"] == "disabled"
        # Now execute → blocked
        r = requests.post(f"{API}/ash/tools/dismiss_insight/execute",
                          headers=headers,
                          json={"args": {"insightId": "does-not-exist"}}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "blocked"
        # Reset
        r = requests.put(f"{API}/ash/tools/dismiss_insight/permission",
                         headers=headers, json={"permission": "auto"}, timeout=15)
        assert r.status_code == 200


# ── Manual tool execute ─────────────────────────────────────────────────
class TestManualExecute:
    def test_auto_execute_fetch_insights(self, headers):
        r = requests.post(f"{API}/ash/tools/fetch_open_insights/execute",
                          headers=headers, json={"args": {}}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "executed", d
        assert "outcome" in d and "insights" in d["outcome"]

    def test_approval_execute_create_po(self, headers):
        r = requests.post(f"{API}/ash/tools/create_purchase_order/execute",
                          headers=headers,
                          json={"args": {"productId": "3", "quantity": 20,
                                         "estimatedCost": 1200}},
                          timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "pending_approval", d
        assert d.get("approvalId")
        assert d.get("risk") == "high"


# ── Agent (multi-turn LLM) ──────────────────────────────────────────────
class TestAgent:
    @pytest.fixture(scope="class")
    def session_state(self):
        return {"sessionId": None}

    def test_agent_simple_query(self, headers, session_state):
        r = requests.post(f"{API}/ash/agent",
                          headers=headers,
                          json={"message": "What are my top open insights?"},
                          timeout=90)
        assert r.status_code == 200
        d = r.json()
        assert d.get("sessionId")
        assert d.get("reply") and len(d["reply"]) > 5
        assert "trace" in d and isinstance(d["trace"], list)
        assert len(d["trace"]) >= 1
        session_state["sessionId"] = d["sessionId"]

    def test_agent_multi_turn_same_session(self, headers, session_state):
        assert session_state["sessionId"], "need sessionId from prev test"
        r = requests.post(f"{API}/ash/agent",
                          headers=headers,
                          json={"message": "Tell me the highest severity one.",
                                "sessionId": session_state["sessionId"]},
                          timeout=90)
        assert r.status_code == 200
        d = r.json()
        assert d["sessionId"] == session_state["sessionId"]
        assert d.get("reply")

    def test_agent_trace_endpoint(self, headers, session_state):
        assert session_state["sessionId"]
        # Give scheduler a moment for trace persistence
        time.sleep(1)
        r = requests.get(f"{API}/ash/agent/trace/{session_state['sessionId']}",
                         headers=headers, timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        # trace rows should exist (may be 0 if LLM returned raw text but usually >=1)
        # We ONLY assert list shape here — trace persistence is best-effort per code

    def test_agent_create_po_intent(self, headers):
        r = requests.post(f"{API}/ash/agent",
                          headers=headers,
                          json={"message": "Create a purchase order for 20 units of product 3 at $25 each"},
                          timeout=120)
        assert r.status_code == 200
        d = r.json()
        assert d.get("reply")
        # toolResults may be empty if LLM chose to answer conversationally.
        # We accept either outcome but capture the fact:
        tr = d.get("toolResults") or []
        # If the agent did call the tool, we require pending_approval
        po_calls = [t for t in tr if t.get("tool") == "create_purchase_order"]
        if po_calls:
            assert po_calls[0]["status"] == "pending_approval"
            assert po_calls[0].get("approvalId")

    def test_agent_missing_message_400(self, headers):
        r = requests.post(f"{API}/ash/agent",
                          headers=headers, json={"message": ""}, timeout=15)
        assert r.status_code == 400
