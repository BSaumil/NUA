"""Iter 39 — AI Weekly Plan + PATCH posts (calendar drag-to-reschedule)."""
import os
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

OWNER = {"email": "owner@nuva.com", "password": "NuvaOwner2026!"}


@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{API}/auth/login", json=OWNER, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def owner_h(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


# ---- ensure at least one connected account exists ----
@pytest.fixture(scope="module", autouse=True)
def ensure_connected_account(owner_h):
    accs = requests.get(f"{API}/social/accounts", headers=owner_h, timeout=15).json()
    if not accs:
        requests.post(f"{API}/social/accounts", headers=owner_h,
                      json={"platform": "instagram", "handle": "nuva_iter39", "displayName": "iter39"}, timeout=15)


# ============ ai-weekly-plan auth ============
def test_weekly_plan_anonymous_401():
    r = requests.post(f"{API}/social/ai-weekly-plan", json={"daysAhead": 7, "save": False}, timeout=15)
    assert r.status_code in (401, 403), r.text


# ============ weekly plan preview (save=false) ============
def test_weekly_plan_preview_does_not_persist(owner_h):
    before = len(requests.get(f"{API}/social/posts", headers=owner_h, timeout=15).json())
    r = requests.post(f"{API}/social/ai-weekly-plan", headers=owner_h,
                      json={"daysAhead": 3, "save": False, "postTime": "12:00"}, timeout=180)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["saved"] == 0
    assert len(data["preview"]) >= 1
    assert "planId" in data and "platformsUsed" in data
    after = len(requests.get(f"{API}/social/posts", headers=owner_h, timeout=15).json())
    assert before == after, "preview must not persist posts"


# ============ weekly plan save=true ============
def test_weekly_plan_save_true_returns_scheduled_with_flags(owner_h):
    r = requests.post(f"{API}/social/ai-weekly-plan", headers=owner_h,
                      json={"daysAhead": 7, "save": True, "postTime": "12:00"}, timeout=240)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["saved"] > 0, data
    assert len(data["posts"]) == data["saved"]
    assert len(data["platformsUsed"]) >= 1
    for p in data["posts"]:
        assert p["status"] == "scheduled"
        assert p.get("autoPlan") is True
        assert p.get("autoPlanRun") is True
        assert p.get("scheduledFor")
    # Confirm posts are visible via GET
    all_posts = requests.get(f"{API}/social/posts", headers=owner_h, params={"status": "scheduled"}, timeout=15).json()
    saved_ids = {p["id"] for p in data["posts"]}
    assert saved_ids.issubset({p["id"] for p in all_posts})


# ============ idempotency: re-run wipes prior autoPlanRun ============
def test_weekly_plan_idempotent_rerun(owner_h):
    r1 = requests.post(f"{API}/social/ai-weekly-plan", headers=owner_h,
                       json={"daysAhead": 7, "save": True, "postTime": "12:00"}, timeout=240)
    assert r1.status_code == 200
    first_ids = {p["id"] for p in r1.json()["posts"]}
    saved1 = r1.json()["saved"]
    # Re-run
    r2 = requests.post(f"{API}/social/ai-weekly-plan", headers=owner_h,
                       json={"daysAhead": 7, "save": True, "postTime": "12:00"}, timeout=240)
    assert r2.status_code == 200
    second_ids = {p["id"] for p in r2.json()["posts"]}
    assert second_ids.isdisjoint(first_ids), "Re-run must produce fresh ids; prior autoPlanRun should have been deleted"
    # Confirm prior ids no longer exist
    all_posts = {p["id"] for p in requests.get(f"{API}/social/posts", headers=owner_h, timeout=15).json()}
    assert first_ids.isdisjoint(all_posts), "Prior autoPlanRun posts must have been deleted"
    assert r2.json()["saved"] == saved1  # same window size → same count


# ============ PATCH posts ============
def test_patch_post_reschedule(owner_h):
    # Get a scheduled post (created by previous test)
    posts = requests.get(f"{API}/social/posts", headers=owner_h, params={"status": "scheduled"}, timeout=15).json()
    if not posts:
        pytest.skip("No scheduled posts to patch")
    pid = posts[0]["id"]
    new_when = "2026-06-15T12:00:00+00:00"
    r = requests.patch(f"{API}/social/posts/{pid}", headers=owner_h,
                       json={"scheduledFor": new_when}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scheduledFor"] == new_when


def test_patch_post_invalid_status_400(owner_h):
    posts = requests.get(f"{API}/social/posts", headers=owner_h, params={"status": "scheduled"}, timeout=15).json()
    if not posts:
        pytest.skip("No posts to patch")
    pid = posts[0]["id"]
    r = requests.patch(f"{API}/social/posts/{pid}", headers=owner_h,
                       json={"status": "hacked"}, timeout=15)
    assert r.status_code == 400, r.text


def test_patch_post_anonymous_401(owner_h):
    posts = requests.get(f"{API}/social/posts", headers=owner_h, timeout=15).json()
    if not posts:
        pytest.skip("No posts")
    pid = posts[0]["id"]
    r = requests.patch(f"{API}/social/posts/{pid}", json={"status": "draft"}, timeout=15)
    assert r.status_code in (401, 403)


def test_patch_post_404(owner_h):
    r = requests.patch(f"{API}/social/posts/does-not-exist-xyz", headers=owner_h,
                       json={"status": "draft"}, timeout=15)
    assert r.status_code == 404


# ============ weekly plan with no connected accounts ============
def test_weekly_plan_no_accounts_400(owner_h):
    # Force platforms=[] by sending unsupported platform key in list
    r = requests.post(f"{API}/social/ai-weekly-plan", headers=owner_h,
                      json={"daysAhead": 3, "save": False, "platforms": ["nonexistent_platform"]}, timeout=60)
    assert r.status_code == 400, r.text
