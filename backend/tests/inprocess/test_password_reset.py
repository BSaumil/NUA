"""Password reset was half-built and abandoned: ForgotPasswordRequest and
ResetPasswordRequest Pydantic models existed in routes/auth.py with no
endpoint ever using them, no frontend "Forgot password?" link, and a staff
member locked out of their account had no self-service recovery at all.
Built on top of infrastructure that already existed and worked elsewhere
in this file: send_email (utils/notifications.py), hash_password/bcrypt,
and the create_challenge_token/read_challenge_token short-lived-JWT
pattern the 2FA flow already uses.
"""
import asyncio

from conftest import OWNER, req


def test_forgot_password_always_answers_the_same_way(client, monkeypatch):
    """Must not leak whether an email has an account — same response shape
    whether it matches a real user or not."""
    sent = []

    async def fake_send_email(to, subject, body):
        sent.append((to, subject, body))
        return {"channel": "email", "delivered": True, "to": to}

    import utils.notifications
    monkeypatch.setattr(utils.notifications, "send_email", fake_send_email)

    real = req(client, "POST", "/api/auth/forgot-password", json={"email": OWNER["email"]})
    fake = req(client, "POST", "/api/auth/forgot-password", json={"email": "definitely-nobody@nua.com"})

    assert real.status_code == 200
    assert fake.status_code == 200
    assert real.json() == fake.json()
    assert len(sent) == 1, "must only email the address that actually has an account"
    assert sent[0][0] == OWNER["email"]
    assert "reset-password?token=" in sent[0][2]


def test_the_emailed_reset_link_actually_resets_the_password(client, monkeypatch):
    import routes.auth as auth_module

    captured = {}

    async def fake_send_email(to, subject, body):
        captured["body"] = body
        return {"channel": "email", "delivered": True, "to": to}

    import utils.notifications
    monkeypatch.setattr(utils.notifications, "send_email", fake_send_email)

    r = req(client, "POST", "/api/auth/forgot-password", json={"email": OWNER["email"]})
    assert r.status_code == 200
    token = captured["body"].split("token=")[1].split('"')[0]

    reset = req(client, "POST", "/api/auth/reset-password", json={"token": token, "password": "NewOwnerPass1!"})
    assert reset.status_code == 200, reset.text[:200]

    # Old password must no longer work; the new one must.
    old_login = req(client, "POST", "/api/auth/login", json=OWNER)
    assert old_login.status_code == 401

    new_login = req(client, "POST", "/api/auth/login", json={"email": OWNER["email"], "password": "NewOwnerPass1!"})
    assert new_login.status_code == 200

    # Restore the fixture's expected password so other tests relying on
    # OWNER's credentials (the whole suite) keep working.
    loop = asyncio.get_event_loop()
    from database import db
    from routes.auth import hash_password
    loop.run_until_complete(db.auth_users.update_one(
        {"email": OWNER["email"]}, {"$set": {"password_hash": hash_password(OWNER["password"])}}))


def test_a_reset_token_cannot_be_reused_as_a_second_factor_or_access_credential(client, monkeypatch):
    """The challenge-token pattern is purpose-scoped on purpose — a
    password_reset token must not pass as a 2FA challenge token, and (like
    every challenge token) must never work as a Bearer access credential."""
    captured = {}

    async def fake_send_email(to, subject, body):
        captured["body"] = body
        return {"channel": "email", "delivered": True, "to": to}

    import utils.notifications
    monkeypatch.setattr(utils.notifications, "send_email", fake_send_email)

    req(client, "POST", "/api/auth/forgot-password", json={"email": OWNER["email"]})
    token = captured["body"].split("token=")[1].split('"')[0]

    # The session-scoped client keeps the access_token cookie from whatever
    # earlier test last logged in, and get_current_user prefers cookies over
    # the Authorization header — without clearing it, this would "pass" by
    # authenticating on the leftover cookie and never actually exercise the
    # Bearer-token path this test exists to check. Same trap the `anon`
    # fixture in conftest.py exists to document.
    client.cookies.clear()
    me = req(client, "GET", "/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 401

    twofa = req(client, "POST", "/api/auth/2fa/challenge", json={"challengeToken": token, "code": "000000"})
    assert twofa.status_code == 401
