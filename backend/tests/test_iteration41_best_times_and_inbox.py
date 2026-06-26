"""
Iteration 41 backend tests.

Covers:
 1. /api/social/best-times — one row per platform, expected shape
 2. /api/social/ai-weekly-plan preview with useBestTimes=true → per-platform hours
 3. /api/social/ai-weekly-plan preview with useBestTimes=false → fixed postTime
 4. /api/social/ai-weekly-plan save=true → queues a job + bestTimeMap; job completes
 5. /api/bookings/inbox — x-ai-parsed-fallback header + aiParsedFallback body
 6. CORS exposes x-ai-parsed-fallback header
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
SUPPORTED = {"instagram", "facebook", "tiktok", "x", "google_business"}


@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"},
                      timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"no token in response: {r.json()}"
    return tok


@pytest.fixture(scope="module")
def auth_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module", autouse=True)
def ensure_connected_accounts(auth_headers):
    """Make sure all 5 supported platforms have at least one connected account."""
    existing = requests.get(f"{BASE_URL}/api/social/accounts", headers=auth_headers, timeout=15)
    existing_platforms = {a["platform"] for a in existing.json()} if existing.status_code == 200 else set()
    for p in SUPPORTED:
        if p not in existing_platforms:
            requests.post(
                f"{BASE_URL}/api/social/accounts",
                headers=auth_headers,
                json={"platform": p, "handle": f"nuva_iter41_{p}", "displayName": f"Iter41 {p}"},
                timeout=15,
            )


# ---------- best-times ----------
class TestBestTimes:
    def test_best_times_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/social/best-times", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_best_times_shape(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/social/best-times", headers=auth_headers, timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data, list)
        platforms = {row["platform"] for row in data}
        assert platforms == SUPPORTED, f"missing/extra platforms: {platforms}"
        for row in data:
            assert "platformLabel" in row
            assert isinstance(row["recommendedHour"], int)
            assert 0 <= row["recommendedHour"] <= 23
            assert row["recommendedTime"] == f"{row['recommendedHour']:02d}:00"
            assert "sampleSize" in row and isinstance(row["sampleSize"], int)
            assert row["source"] in ("pos_peak", "pos_peak_clamped", "default_band")
            assert isinstance(row["band"], list) and len(row["band"]) == 2
            assert row["band"][0] <= row["recommendedHour"] <= row["band"][1]


# ---------- weekly plan preview ----------
class TestWeeklyPlanPreview:
    def test_preview_with_best_times(self, auth_headers):
        # Fetch best-times to compare
        bt = requests.get(f"{BASE_URL}/api/social/best-times", headers=auth_headers, timeout=15).json()
        bt_map = {row["platform"]: row["recommendedHour"] for row in bt}

        r = requests.post(
            f"{BASE_URL}/api/social/ai-weekly-plan",
            headers=auth_headers,
            json={"daysAhead": 2, "useBestTimes": True, "save": False, "tone": "warm"},
            timeout=120,
        )
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert "bestTimeMap" in body, "preview response must include bestTimeMap"
        assert body["bestTimeMap"], "bestTimeMap should be populated when useBestTimes=true"
        preview = body.get("preview") or body.get("posts") or []
        assert len(preview) > 0, "preview should contain posts"
        # Each post's scheduledFor hour must match the platform's recommended hour.
        for post in preview:
            platform = post["platform"]
            expected_hour = bt_map[platform]
            from datetime import datetime
            dt = datetime.fromisoformat(post["scheduledFor"])
            assert dt.hour == expected_hour, (
                f"{platform}: scheduledFor hour={dt.hour}, expected={expected_hour}"
            )

    def test_preview_without_best_times_uses_fixed_postTime(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/social/ai-weekly-plan",
            headers=auth_headers,
            json={"daysAhead": 2, "useBestTimes": False, "save": False,
                  "postTime": "12:00", "tone": "warm"},
            timeout=120,
        )
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        # bestTimeMap can be {} or absent, but all hours must be 12.
        preview = body.get("preview") or body.get("posts") or []
        assert preview, "preview should contain posts"
        from datetime import datetime
        hours = {datetime.fromisoformat(p["scheduledFor"]).hour for p in preview}
        assert hours == {12}, f"expected all posts at 12:00, got hours={hours}"


# ---------- weekly plan save path ----------
class TestWeeklyPlanSave:
    def test_save_queues_job_with_best_time_map(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/social/ai-weekly-plan",
            headers=auth_headers,
            json={"daysAhead": 1, "useBestTimes": True, "save": True, "tone": "warm"},
            timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["status"] == "queued"
        assert "planId" in body
        assert "bestTimeMap" in body and body["bestTimeMap"], "save response must include bestTimeMap"
        plan_id = body["planId"]

        # Poll until complete or timeout
        deadline = time.time() + 180
        last = None
        while time.time() < deadline:
            try:
                jr = requests.get(f"{BASE_URL}/api/social/plan-jobs/{plan_id}",
                                  headers=auth_headers, timeout=45)
            except requests.exceptions.ReadTimeout:
                # Worker may be hammering the LLM endpoint — just retry
                time.sleep(3)
                continue
            assert jr.status_code == 200
            last = jr.json()
            if last["status"] in ("complete", "failed"):
                break
            time.sleep(3)
        assert last and last["status"] == "complete", f"job did not complete: {last}"

        # Verify generated social_posts have correct per-platform hours
        bt = requests.get(f"{BASE_URL}/api/social/best-times",
                          headers=auth_headers, timeout=15).json()
        bt_map = {row["platform"]: row["recommendedHour"] for row in bt}
        posts = requests.get(f"{BASE_URL}/api/social/posts?status=scheduled",
                             headers=auth_headers, timeout=15).json()
        plan_posts = [p for p in posts if p.get("autoPlanId") == plan_id]
        assert plan_posts, "expected at least one post for this planId"
        from datetime import datetime
        for p in plan_posts:
            expected_hour = bt_map[p["platform"]]
            dt = datetime.fromisoformat(p["scheduledFor"])
            assert dt.hour == expected_hour, (
                f"{p['platform']}: hour={dt.hour}, expected={expected_hour}"
            )


# ---------- bookings inbox header ----------
class TestBookingsInboxFallbackHeader:
    def test_ingest_returns_header_and_body_flag(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/bookings/inbox",
            headers=auth_headers,
            json={"channel": "instagram_dm",
                  "rawMessage": "TEST_iter41 — table for 2 tomorrow 7pm",
                  "fromHandle": "@iter41tester"},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        # Header must be set to 'true' or 'false' (lowercase string)
        header = r.headers.get("x-ai-parsed-fallback")
        assert header in ("true", "false"), f"unexpected header value: {header!r}"
        body = r.json()
        assert "aiParsedFallback" in body, "body must include aiParsedFallback"
        assert isinstance(body["aiParsedFallback"], bool)
        # Header and body should agree
        assert (header == "true") == body["aiParsedFallback"]

    def test_cors_exposes_header(self):
        # Preflight
        r = requests.options(
            f"{BASE_URL}/api/bookings/inbox",
            headers={
                "Origin": "https://pos-checkout-16.preview.emergentagent.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
            timeout=15,
        )
        # Either preflight or simple GET — expose header surfaces on actual response
        # Some CORS impls only return expose-headers on the actual request, so also check ingest.
        expose = r.headers.get("access-control-expose-headers", "")
        if "x-ai-parsed-fallback" not in expose.lower():
            # Fall back to checking actual response headers from POST
            tok = requests.post(f"{BASE_URL}/api/auth/login",
                                json={"email": "owner@nuva.com",
                                      "password": "NuvaOwner2026!"},
                                timeout=15).json().get("token")
            r2 = requests.post(
                f"{BASE_URL}/api/bookings/inbox",
                headers={"Authorization": f"Bearer {tok}",
                         "Content-Type": "application/json",
                         "Origin": "https://pos-checkout-16.preview.emergentagent.com"},
                json={"channel": "instagram_dm", "rawMessage": "TEST_iter41 cors check"},
                timeout=60,
            )
            expose = r2.headers.get("access-control-expose-headers", "")
        assert "x-ai-parsed-fallback" in expose.lower(), \
            f"CORS expose-headers missing x-ai-parsed-fallback: {expose!r}"


# ---------- regression: login + products + composer ----------
class TestRegression:
    def test_login(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"},
                          timeout=15)
        assert r.status_code == 200

    def test_list_products(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/products", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_social_posts(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/social/posts", headers=auth_headers, timeout=15)
        assert r.status_code == 200
