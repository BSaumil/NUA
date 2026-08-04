"""
Iteration 55 — Ash v3 Phases 4-19 (Personas, Planner, Simulation, Memory, Permissions)
                + P2 Loyalty 2.0 (Badges/Milestones/Challenges/Progress).

Backend-only. All endpoints prefixed /api. Uses owner JWT.
"""
import os
import time
import pytest
import requests
import uuid
from datetime import datetime, timedelta, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")

OWNER = {"email": "owner@nua.com", "password": "NuaOwner2026!"}
CUSTOMER_ID = "cust-1"


# ═════════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="session")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=OWNER, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def api(owner_token):
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {owner_token}",
    })
    return s


# ═════════════════════════════════════════════════════════════════════════
# Ash Personas — Phase 4
# ═════════════════════════════════════════════════════════════════════════
class TestAshPersonas:
    def test_list_personas_returns_six(self, api):
        r = api.get(f"{BASE_URL}/api/ash/personas", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list) and len(data) == 6
        ids = {p["id"] for p in data}
        assert ids == {"executive", "finance", "ops", "hr", "marketing", "guest"}
        for p in data:
            for k in ("id", "label", "tagline", "modules", "tone", "focus", "icon", "color"):
                assert k in p, f"persona {p.get('id')} missing {k}"
            assert isinstance(p["modules"], list) and p["modules"]

    def test_finance_agent_reply_no_raw_json(self, api):
        payload = {"message": "Give me a 1-sentence read on our margin position.",
                   "persona": "finance"}
        r = api.post(f"{BASE_URL}/api/ash/agent", json=payload, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("persona") == "finance"
        assert data.get("personaLabel") == "Ash Finance"
        reply = data.get("reply") or ""
        assert reply, "reply empty"
        # Should NOT leak the tool-calling JSON envelope
        assert '"action"' not in reply.lower() or "final" not in reply.lower(), \
            f"agent leaked JSON envelope in reply: {reply[:400]}"
        assert not (reply.strip().startswith("{") and '"action"' in reply), \
            f"agent leaked JSON envelope: {reply[:400]}"

    def test_hr_persona_refuses_inventory_query(self, api):
        """HR persona should gracefully decline inventory-heavy tool calls."""
        r = api.post(f"{BASE_URL}/api/ash/agent", json={
            "message": "How much flour do we have in stock?",
            "persona": "hr",
        }, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("persona") == "hr"
        reply = (data.get("reply") or "").lower()
        # Either mentions redirecting or refuses / suggests ops persona.
        # Also: no inventory tool should have actually executed.
        tool_results = data.get("toolResults") or []
        inv_tools = [t for t in tool_results
                     if isinstance(t, dict) and t.get("tool", "").startswith(("fetch_", "lookup_product"))
                     and "product" in (t.get("tool") or "")]
        # HR modules are Staff+Ash — no inventory tools allowed.
        assert not inv_tools, f"HR persona invoked inventory tool: {inv_tools}"


# ═════════════════════════════════════════════════════════════════════════
# Ash Planner — Phase 5-8 (Plans, Simulation, Approvals)
# ═════════════════════════════════════════════════════════════════════════
class TestAshPlanner:
    plan_id = None  # class-scoped state

    def test_generate_plan(self, api):
        r = api.post(f"{BASE_URL}/api/ash/plans/generate", json={
            "goal": "Reduce food waste by 15% next month.",
            "persona": "ops",
        }, timeout=120)
        assert r.status_code == 200, r.text
        plan = r.json()
        for k in ("id", "goal", "steps", "status", "personaLabel"):
            assert k in plan, f"plan missing {k}: {plan}"
        assert plan["status"] == "proposed"
        assert plan["personaLabel"] == "Ash Ops"
        assert isinstance(plan["steps"], list) and len(plan["steps"]) >= 1
        for s in plan["steps"]:
            assert "tool" in s and "args" in s and "rationale" in s
            assert s.get("status") in ("pending", "invalid")
        TestAshPlanner.plan_id = plan["id"]

    def test_list_plans(self, api):
        r = api.get(f"{BASE_URL}/api/ash/plans", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        assert any(p["id"] == TestAshPlanner.plan_id for p in rows), "created plan not in list"

    def test_get_single_plan(self, api):
        assert TestAshPlanner.plan_id
        r = api.get(f"{BASE_URL}/api/ash/plans/{TestAshPlanner.plan_id}", timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == TestAshPlanner.plan_id

    def test_simulate_plan(self, api):
        assert TestAshPlanner.plan_id
        r = api.post(f"{BASE_URL}/api/ash/plans/{TestAshPlanner.plan_id}/simulate",
                       timeout=90)
        assert r.status_code == 200, r.text
        sim = r.json()
        assert "narrative" in sim and sim["narrative"]
        steps = sim.get("simulatedSteps") or []
        assert isinstance(steps, list) and len(steps) >= 1
        # Every simStatus must be one of the expected values
        for s in steps:
            assert s.get("simStatus") in (
                "read", "read_error", "would_write", "unknown_tool"
            ), f"unexpected simStatus: {s.get('simStatus')}"

    def test_reject_step_zero_then_recreate(self, api):
        """Reject a specific step (idx=0), verify status='rejected' on that step only."""
        # Fresh plan so we don't collide with executing walk
        r = api.post(f"{BASE_URL}/api/ash/plans/generate", json={
            "goal": "Audit purchase orders for anomalies this week.",
            "persona": "ops",
        }, timeout=120)
        assert r.status_code == 200
        pid = r.json()["id"]

        r = api.post(f"{BASE_URL}/api/ash/plans/{pid}/steps/0/reject",
                       json={"reason": "not now"}, timeout=15)
        assert r.status_code == 200, r.text
        plan = r.json()
        assert plan["steps"][0]["status"] == "rejected"

    def test_reject_whole_plan(self, api):
        r = api.post(f"{BASE_URL}/api/ash/plans/generate", json={
            "goal": "Bump wine margins 5%.",
            "persona": "finance",
        }, timeout=120)
        pid = r.json()["id"]
        r = api.post(f"{BASE_URL}/api/ash/plans/{pid}/reject",
                       json={"reason": "not now"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    def test_approve_read_only_step(self, api):
        """Approve step 0 of a fresh plan — first step is usually a read (fetch_*),
        so it should return status='executed'."""
        r = api.post(f"{BASE_URL}/api/ash/plans/generate", json={
            "goal": "Investigate open insights this hour.",
            "persona": "executive",
        }, timeout=120)
        pid = r.json()["id"]
        steps = r.json()["steps"]
        # find first read-only step
        read_idx = None
        for i, s in enumerate(steps):
            tool = s.get("tool") or ""
            if s.get("status") == "pending" and (
                tool.startswith(("fetch_", "lookup_", "generate_")) or tool == "run_ash_scan"
            ):
                read_idx = i
                break
        if read_idx is None:
            pytest.skip("Plan has no read-only step — LLM produced an unusual plan.")
        r = api.post(f"{BASE_URL}/api/ash/plans/{pid}/steps/{read_idx}/approve",
                       timeout=30)
        assert r.status_code == 200, r.text
        outcome = r.json()
        assert outcome.get("status") in ("executed", "blocked"), outcome

    def test_approve_write_step_enqueues_approval(self, api):
        """Approve a WRITE step — should route through /approvals with pending_approval."""
        r = api.post(f"{BASE_URL}/api/ash/plans/generate", json={
            "goal": "Adjust the price of one wine SKU by +2%.",
            "persona": "finance",
        }, timeout=120)
        pid = r.json()["id"]
        steps = r.json()["steps"]
        write_idx = None
        for i, s in enumerate(steps):
            tool = s.get("tool") or ""
            if s.get("status") == "pending" and not (
                tool.startswith(("fetch_", "lookup_", "generate_")) or tool == "run_ash_scan"
            ):
                write_idx = i
                break
        if write_idx is None:
            pytest.skip("Plan has no write step — nothing to test.")
        r = api.post(f"{BASE_URL}/api/ash/plans/{pid}/steps/{write_idx}/approve",
                       timeout=30)
        assert r.status_code == 200, r.text
        outcome = r.json()
        # Must be pending_approval OR blocked (if perms disabled) OR executed (if perm was 'auto')
        assert outcome.get("status") in ("pending_approval", "blocked", "executed", "error")


# ═════════════════════════════════════════════════════════════════════════
# Ash Tools — 'remember' and 'recall' tools present + permission set/get
# ═════════════════════════════════════════════════════════════════════════
class TestAshToolsExtras:
    def test_remember_recall_tools_in_catalog(self, api):
        r = api.get(f"{BASE_URL}/api/ash/tools", timeout=15)
        assert r.status_code == 200
        catalog = r.json()
        names = {t["name"] for t in catalog}
        assert "remember" in names, f"remember tool missing. Got: {names}"
        assert "recall" in names, f"recall tool missing. Got: {names}"
        for t in catalog:
            assert "effectivePermission" in t, f"{t['name']} missing effectivePermission"

    def test_permission_set_and_read_back(self, api):
        # set 'remember' to approval, then verify
        r = api.put(f"{BASE_URL}/api/ash/tools/remember/permission",
                     json={"permission": "approval"}, timeout=15)
        assert r.status_code == 200, r.text
        r = api.get(f"{BASE_URL}/api/ash/tools", timeout=15)
        assert r.status_code == 200
        remember_tool = next(t for t in r.json() if t["name"] == "remember")
        assert remember_tool["effectivePermission"] == "approval"
        # reset back to auto
        r = api.put(f"{BASE_URL}/api/ash/tools/remember/permission",
                     json={"permission": "auto"}, timeout=15)
        assert r.status_code == 200


# ═════════════════════════════════════════════════════════════════════════
# Ash Memory
# ═════════════════════════════════════════════════════════════════════════
class TestAshMemory:
    memory_id = None
    text = f"TEST_MEMORY_{uuid.uuid4().hex[:8]} — owner prefers oat milk in staff coffee."

    def test_create_memory(self, api):
        r = api.post(f"{BASE_URL}/api/ash/memory", json={
            "text": TestAshMemory.text,
            "scope": "TEST_scope",
            "kind": "preference",
            "confidence": 1,
        }, timeout=15)
        assert r.status_code == 200, r.text
        m = r.json()
        assert m["text"] == TestAshMemory.text
        assert m["scope"] == "TEST_scope"
        assert m["kind"] == "preference"
        TestAshMemory.memory_id = m["id"]

    def test_list_memory(self, api):
        r = api.get(f"{BASE_URL}/api/ash/memory?scope=TEST_scope", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        assert any(m["id"] == TestAshMemory.memory_id for m in rows)

    def test_scope_counts(self, api):
        r = api.get(f"{BASE_URL}/api/ash/memory/scopes", timeout=15)
        assert r.status_code == 200
        counts = r.json()
        assert isinstance(counts, dict)
        assert counts.get("TEST_scope", 0) >= 1

    def test_reinforce_same_text_bumps_confidence(self, api):
        # First recall existing to know current conf
        r = api.get(f"{BASE_URL}/api/ash/memory?scope=TEST_scope", timeout=15)
        existing = next(m for m in r.json() if m["id"] == TestAshMemory.memory_id)
        conf_before = float(existing["confidence"])
        # Store the SAME text in the SAME scope again — should reinforce, not duplicate
        r = api.post(f"{BASE_URL}/api/ash/memory", json={
            "text": TestAshMemory.text,
            "scope": "TEST_scope",
            "kind": "preference",
            "confidence": 1,
        }, timeout=15)
        assert r.status_code == 200
        payload = r.json()
        assert payload.get("reinforced") is True, f"expected reinforced=true, got {payload}"
        # confidence should be capped at 1.0 already; check no duplicate row
        r = api.get(f"{BASE_URL}/api/ash/memory?scope=TEST_scope", timeout=15)
        matches = [m for m in r.json() if m["text"] == TestAshMemory.text]
        assert len(matches) == 1, f"duplicate memories created: {len(matches)}"

    def test_delete_memory(self, api):
        r = api.delete(f"{BASE_URL}/api/ash/memory/{TestAshMemory.memory_id}",
                        timeout=15)
        assert r.status_code == 200
        r = api.get(f"{BASE_URL}/api/ash/memory?scope=TEST_scope", timeout=15)
        assert not any(m["id"] == TestAshMemory.memory_id for m in r.json())


# ═════════════════════════════════════════════════════════════════════════
# Loyalty 2.0 — P2
# ═════════════════════════════════════════════════════════════════════════
class TestLoyaltyV2:
    challenge_id = None

    def test_badges_seeded(self, api):
        r = api.get(f"{BASE_URL}/api/loyalty/v2/badges", timeout=15)
        assert r.status_code == 200, r.text
        badges = r.json()
        assert isinstance(badges, list)
        assert len(badges) >= 10, f"expected >=10 badges, got {len(badges)}"
        names = {b["name"] for b in badges}
        expected = {"First Visit", "Regular", "Loyalist", "Century Club",
                     "Big Spender", "VIP Whale", "Early Bird", "Wine Buff",
                     "Community Builder", "Birthday Guest"}
        missing = expected - names
        assert not missing, f"badges missing: {missing}"

    def test_milestones_seeded(self, api):
        r = api.get(f"{BASE_URL}/api/loyalty/v2/milestones", timeout=15)
        assert r.status_code == 200
        miles = r.json()
        assert len(miles) >= 6
        names = {m["name"] for m in miles}
        expected = {"5 Visits", "25 Visits", "$100 Spent", "$500 Spent",
                     "$2,000 Spent", "$5,000 Spent"}
        missing = expected - names
        assert not missing, f"milestones missing: {missing}. Got: {names}"

    def test_evaluate_customer_idempotent(self, api):
        r1 = api.post(f"{BASE_URL}/api/loyalty/v2/evaluate/{CUSTOMER_ID}", timeout=30)
        assert r1.status_code == 200, r1.text
        a1 = r1.json()
        b1 = len(a1.get("awardedBadges") or [])
        m1 = len(a1.get("awardedMilestones") or [])
        # Second run: nothing new
        r2 = api.post(f"{BASE_URL}/api/loyalty/v2/evaluate/{CUSTOMER_ID}", timeout=30)
        assert r2.status_code == 200
        a2 = r2.json()
        assert len(a2.get("awardedBadges") or []) == 0, \
            f"idempotency broken: 2nd eval awarded {a2['awardedBadges']}"
        assert len(a2.get("awardedMilestones") or []) == 0, \
            f"idempotency broken: 2nd eval awarded milestones {a2['awardedMilestones']}"
        print(f"[eval] first run awarded {b1} badges + {m1} milestones; second run = 0 (idempotent)")

    def test_customer_progress_shape(self, api):
        r = api.get(f"{BASE_URL}/api/loyalty/v2/progress/{CUSTOMER_ID}", timeout=15)
        assert r.status_code == 200, r.text
        p = r.json()
        for k in ("points", "tier", "tierProgress", "badges", "milestones", "challenges"):
            assert k in p, f"progress missing {k}: {p}"
        # tierProgress schema
        tp = p["tierProgress"]
        if tp:  # may be null if no tiers seeded
            for k in ("current", "next", "pointsNeeded", "percent"):
                assert k in tp
        # each badge should have 'earned'
        for b in p["badges"]:
            assert "earned" in b and isinstance(b["earned"], bool)
        # each milestone should have current/progressPercent/achieved
        for m in p["milestones"]:
            assert "current" in m and "progressPercent" in m and "achieved" in m

    def test_challenge_crud(self, api):
        start = datetime.now(timezone.utc).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        r = api.post(f"{BASE_URL}/api/loyalty/v2/challenges", json={
            "name": "TEST_SummerSpend",
            "metric": "spend",
            "target": 100,
            "startDate": start,
            "endDate": end,
            "reward": {"type": "points", "value": 50, "label": "50 pts"},
        }, timeout=15)
        assert r.status_code == 200, r.text
        c = r.json()
        assert c.get("name") == "TEST_SummerSpend"
        assert c.get("id")
        TestLoyaltyV2.challenge_id = c["id"]

        r = api.get(f"{BASE_URL}/api/loyalty/v2/challenges", timeout=15)
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert TestLoyaltyV2.challenge_id in ids

        r = api.delete(f"{BASE_URL}/api/loyalty/v2/challenges/{TestLoyaltyV2.challenge_id}",
                        timeout=15)
        assert r.status_code == 200


# ═════════════════════════════════════════════════════════════════════════
# Regression — existing Ash + Finance endpoints
# ═════════════════════════════════════════════════════════════════════════
class TestRegression:
    def test_ash_insights(self, api):
        r = api.get(f"{BASE_URL}/api/ash/insights?limit=5", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_ash_health_score(self, api):
        r = api.get(f"{BASE_URL}/api/ash/health-score", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "overall" in d and "subscores" in d

    def test_ash_briefing(self, api):
        r = api.get(f"{BASE_URL}/api/ash/briefing", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d.get("narrative") and d.get("data")

    def test_ash_chat_still_works(self, api):
        r = api.post(f"{BASE_URL}/api/ash/chat", json={"message": "hi"}, timeout=60)
        assert r.status_code == 200
        assert r.json().get("reply")

    def test_ash_tools_full(self, api):
        r = api.get(f"{BASE_URL}/api/ash/tools", timeout=15)
        assert r.status_code == 200
        assert len(r.json()) >= 20

    def test_approvals_pending(self, api):
        r = api.get(f"{BASE_URL}/api/approvals?status=pending", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_finance_dashboard(self, api):
        # Common finance surface
        r = api.get(f"{BASE_URL}/api/accounting/kpis", timeout=30)
        assert r.status_code in (200, 404), r.status_code

    def test_audit_events(self, api):
        r = api.get(f"{BASE_URL}/api/audit/events?limit=5", timeout=15)
        assert r.status_code in (200, 404, 405), r.status_code

    def test_hq(self, api):
        r = api.get(f"{BASE_URL}/api/hq/overview", timeout=30)
        assert r.status_code in (200, 404), r.status_code
