"""POST /auth/refresh only ever set a fresh access_token as an httpOnly
cookie — but the frontend authenticates every API call with a Bearer header
read from localStorage, never the cookie, so refreshing only the cookie was
silently useless for the auth flow the app actually uses. Any session left
open past the 8-hour access-token expiry (an unattended kiosk, an overnight
shift) had no recovery but a full re-login. Fixed by also returning the new
token in the JSON body; this pins that it's actually there and actually
works as a Bearer credential.
"""
from conftest import OWNER, req


def test_refresh_returns_a_usable_bearer_token(client):
    # Login without clearing cookies afterward (unlike the owner_headers
    # fixture) — the refresh_token cookie set at login is exactly what
    # /auth/refresh needs to find.
    r = req(client, "POST", "/api/auth/login", json=OWNER)
    assert r.status_code == 200, r.text[:200]

    refreshed = req(client, "POST", "/api/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text[:200]
    body = refreshed.json()
    assert body.get("token"), "refresh must return a usable token, not just set a cookie"

    # The returned token must actually authenticate as a Bearer credential —
    # not just be a non-empty string that never gets validated.
    client.cookies.clear()
    me = req(client, "GET", "/api/auth/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200, me.text[:200]
    assert me.json()["email"] == OWNER["email"]


def test_refresh_without_a_refresh_cookie_is_refused(anon):
    r = req(anon, "POST", "/api/auth/refresh")
    assert r.status_code == 401
