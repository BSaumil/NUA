"""Iter 42 — CRM customers + subscription member edit/delete."""
import os, pytest, requests, uuid

def _load_url():
    import re
    with open("/app/frontend/.env") as f:
        for ln in f:
            m = re.match(r"REACT_APP_BACKEND_URL=(.+)", ln.strip())
            if m: return m.group(1).rstrip("/")
    raise RuntimeError("no REACT_APP_BACKEND_URL")
BASE = os.environ.get("REACT_APP_BACKEND_URL") or _load_url()
BASE = BASE.rstrip("/")
CRED_OWNER = {"email": "owner@nua.com", "password": "NuaOwner2026!"}
CRED_MGR = {"email": "manager@nua.com", "password": "Staff2026!"}

def _login(c):
    r = c.post(f"{BASE}/api/auth/login", json=CRED_OWNER, timeout=15); r.raise_for_status()
    return r.json()["token"]

def _login_mgr(c):
    r = c.post(f"{BASE}/api/auth/login", json=CRED_MGR, timeout=15); r.raise_for_status()
    return r.json()["token"]

@pytest.fixture(scope="module")
def owner():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login(s)}"})
    return s

@pytest.fixture(scope="module")
def manager():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login_mgr(s)}"})
    return s

# ---- CRM customer list resilience ----
def test_customers_list_200(owner):
    r = owner.get(f"{BASE}/api/customers", timeout=20)
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list) and len(rows) >= 5
    # no @nua.local
    assert not any((c.get("email") or "").endswith("@nua.local") for c in rows)

def test_five_seeded_present(owner):
    r = owner.get(f"{BASE}/api/customers", timeout=20)
    emails = {c["email"] for c in r.json() if c.get("email")}
    for e in ["olivia.bennett@example.com","marcus.tan@example.com","priya.sharma@example.com","james.odonnell@example.com","sofia.reyes@example.com"]:
        assert e in emails, f"missing seed {e}"

def test_olivia_profile_has_history(owner):
    rows = owner.get(f"{BASE}/api/customers", timeout=20).json()
    olivia = next(c for c in rows if c["email"]=="olivia.bennett@example.com")
    r = owner.get(f"{BASE}/api/customers/{olivia['id']}/profile", timeout=20)
    assert r.status_code == 200
    p = r.json()
    assert len(p.get("reservationHistory",[])) >= 2
    assert len(p.get("transactionHistory",[])) >= 2
    assert len(p.get("feedbackHistory",[])) >= 2

# ---- Subscriptions member PATCH/DELETE ----
@pytest.fixture(scope="module")
def plan_and_member(owner):
    # Get/seed a plan
    plans = owner.get(f"{BASE}/api/v25/subscriptions/plans", timeout=15).json()
    plan = plans[0] if plans else owner.post(f"{BASE}/api/v25/subscriptions/plans",
        json={"name":"TEST_iter42 Plan","priceMonthly":19,"perks":["x"]}, timeout=15).json()
    # Enroll a member
    cust_id = owner.get(f"{BASE}/api/customers", timeout=15).json()[0]["id"]
    m = owner.post(f"{BASE}/api/v25/subscriptions/enroll", json={"customerId":cust_id,"planId":plan["id"]}, timeout=15).json()
    return plan, m

def test_member_patch_valid(owner, plan_and_member):
    _, member = plan_and_member
    r = owner.patch(f"{BASE}/api/v25/subscriptions/members/{member['id']}",
        json={"status":"paused","notes":"TEST_iter42"}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json().get("status") == "paused"

def test_member_patch_bad_status_400(owner, plan_and_member):
    _, member = plan_and_member
    r = owner.patch(f"{BASE}/api/v25/subscriptions/members/{member['id']}",
        json={"status":"frozen"}, timeout=15)
    assert r.status_code == 400

def test_member_patch_unknown_plan_404(owner, plan_and_member):
    _, member = plan_and_member
    r = owner.patch(f"{BASE}/api/v25/subscriptions/members/{member['id']}",
        json={"planId":"PLAN-NOPE-"+uuid.uuid4().hex[:6]}, timeout=15)
    assert r.status_code == 404

def test_member_delete_owner_soft_cancels(owner, plan_and_member):
    _, member = plan_and_member
    r = owner.delete(f"{BASE}/api/v25/subscriptions/members/{member['id']}", timeout=15)
    assert r.status_code == 200
    rows = owner.get(f"{BASE}/api/v25/subscriptions/members", timeout=15).json()
    row = next((m for m in rows if m["id"]==member["id"]), None)
    assert row and row.get("status") == "cancelled" and row.get("cancelledAt")

def test_member_delete_manager_403(manager, plan_and_member):
    _, member = plan_and_member
    r = manager.delete(f"{BASE}/api/v25/subscriptions/members/{member['id']}", timeout=15)
    assert r.status_code == 403

# ---- v26 plan PATCH/DELETE still works ----
def test_v26_plan_patch_and_delete(owner):
    p = owner.post(f"{BASE}/api/v25/subscriptions/plans",
        json={"name":"TEST_iter42 patchable","priceMonthly":15,"perks":["a"]}, timeout=15).json()
    r = owner.patch(f"{BASE}/api/v26/subscriptions/plans/{p['id']}",
        json={"priceMonthly":25,"perks":["a","b"],"trialDays":7,"active":True,
              "name":"TEST_iter42 renamed","termsAndConditions":"T&C"}, timeout=15)
    assert r.status_code == 200
    plans = owner.get(f"{BASE}/api/v25/subscriptions/plans", timeout=15).json()
    updated = next(x for x in plans if x["id"]==p["id"])
    assert updated["priceMonthly"] == 25 and updated["name"]=="TEST_iter42 renamed"
    r = owner.delete(f"{BASE}/api/v26/subscriptions/plans/{p['id']}", timeout=15)
    assert r.status_code == 200
