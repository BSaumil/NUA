"""What's New — owners/managers had no way to see what changed in NUA POS
recently or what's coming next. GET /changelog (windowed), /upcoming, and
/summary back the new What's New page.
"""
import asyncio

from conftest import req


def _seed_entries():
    loop = asyncio.get_event_loop()
    from database import db
    from datetime import datetime, timezone, timedelta

    def iso(days_ago):
        return (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()

    entries = [
        {"id": "CL-1", "title": "Recent feature", "description": "d", "category": "feature",
         "area": "Test", "audience": "owner", "status": "shipped", "releasedAt": iso(2),
         "createdAt": datetime.now(timezone.utc).isoformat()},
        {"id": "CL-2", "title": "Older this-month feature", "description": "d", "category": "feature",
         "area": "Test", "audience": "owner", "status": "shipped", "releasedAt": iso(20),
         "createdAt": datetime.now(timezone.utc).isoformat()},
        {"id": "CL-3", "title": "Ancient feature", "description": "d", "category": "feature",
         "area": "Test", "audience": "owner", "status": "shipped", "releasedAt": iso(90),
         "createdAt": datetime.now(timezone.utc).isoformat()},
        {"id": "CL-4", "title": "Upcoming feature", "description": "d", "category": "feature",
         "area": "Test", "audience": "owner", "status": "upcoming", "releasedAt": None,
         "createdAt": datetime.now(timezone.utc).isoformat()},
    ]
    loop.run_until_complete(db.changelog_entries.delete_many({"id": {"$in": [e["id"] for e in entries]}}))
    loop.run_until_complete(db.changelog_entries.insert_many(entries))


def test_week_window_only_returns_recent_entries(client, owner_headers):
    _seed_entries()
    r = req(client, "GET", "/api/changelog", headers=owner_headers, params={"window": "week"})
    assert r.status_code == 200, r.text[:200]
    titles = {e["title"] for e in r.json()}
    assert "Recent feature" in titles
    assert "Older this-month feature" not in titles
    assert "Ancient feature" not in titles


def test_month_window_includes_week_and_older_this_month(client, owner_headers):
    _seed_entries()
    r = req(client, "GET", "/api/changelog", headers=owner_headers, params={"window": "month"})
    titles = {e["title"] for e in r.json()}
    assert "Recent feature" in titles
    assert "Older this-month feature" in titles
    assert "Ancient feature" not in titles


def test_no_window_returns_everything_shipped_but_not_upcoming(client, owner_headers):
    _seed_entries()
    r = req(client, "GET", "/api/changelog", headers=owner_headers)
    titles = {e["title"] for e in r.json()}
    assert "Ancient feature" in titles
    assert "Upcoming feature" not in titles


def test_upcoming_endpoint_returns_only_upcoming(client, owner_headers):
    _seed_entries()
    r = req(client, "GET", "/api/changelog/upcoming", headers=owner_headers)
    assert r.status_code == 200, r.text[:200]
    titles = {e["title"] for e in r.json()}
    assert titles == {"Upcoming feature"} or "Upcoming feature" in titles
    assert all(e["status"] == "upcoming" for e in r.json())


def test_summary_counts_match_the_windows(client, owner_headers):
    _seed_entries()
    r = req(client, "GET", "/api/changelog/summary", headers=owner_headers)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body["thisWeek"] >= 1
    assert body["thisMonth"] >= body["thisWeek"]
    assert body["upcoming"] >= 1


def test_changelog_requires_owner_or_manager(client, owner_headers):
    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Changelog Cashier", "email": "changelog.cashier@nua.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={
        "email": "changelog.cashier@nua.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    cashier_headers = {"Authorization": f"Bearer {tok['token']}"}

    assert req(client, "GET", "/api/changelog", headers=cashier_headers).status_code == 403
    assert req(client, "GET", "/api/changelog/upcoming", headers=cashier_headers).status_code == 403
    assert req(client, "GET", "/api/changelog/summary", headers=cashier_headers).status_code == 403


def test_changelog_endpoints_refuse_an_anonymous_caller(anon):
    assert req(anon, "GET", "/api/changelog").status_code == 401
