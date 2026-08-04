"""Real TOTP, checked at login, not the "123456" stub it replaced.

Every code here is generated from the enrolled secret with pyotp, so this
fails if verification is ever faked — which is exactly how the old stub would
have been caught, had anything been testing it.
"""
import time

import pyotp
import pytest

from conftest import OWNER, req

pytestmark = pytest.mark.usefixtures("client")


@pytest.fixture
def enrolled(client, owner_headers):
    """Enrol the owner in 2FA and hand back (headers, totp, recovery_codes).

    The owner account is shared with every other test module through the
    session-scoped client and its in-memory database, so enrolling it here
    would leave 2FA switched on for whoever runs next — including the plain
    owner_headers fixture other suites rely on for a password-only login.
    Teardown clears it directly against the database rather than through the
    API, since these tests are exercising enrolment and login, not the
    disable-with-password flow (that gets its own test below).
    """
    setup = req(client, "POST", "/api/auth/2fa/setup", headers=owner_headers, json={}).json()
    totp = pyotp.TOTP(setup["secret"])
    enrol_code = totp.now()
    r = req(client, "POST", "/api/auth/2fa/verify", headers=owner_headers,
            json={"code": enrol_code})
    assert r.status_code == 200, r.text[:200]
    try:
        # The enrolment code itself is now burned — a test asking for a fresh
        # one straight after must not be handed this same still-current code.
        yield owner_headers, totp, r.json()["recoveryCodes"], {enrol_code}
    finally:
        import asyncio
        from database import db
        asyncio.get_event_loop().run_until_complete(
            db.auth_users.update_one(
                {"email": OWNER["email"]},
                {"$unset": {"twoFactorSecret": "", "twoFactorEnabled": "",
                           "twoFactorSecretPending": "", "recoveryCodes": "",
                           "twoFactorEnabledAt": ""}}))
        asyncio.get_event_loop().run_until_complete(
            db.trusted_devices.delete_many({}))
        asyncio.get_event_loop().run_until_complete(
            db.settings.delete_one({"key": "two_factor_policy"}))
        client.cookies.clear()


def _fresh_code(totp, used):
    for _ in range(70):
        code = totp.now()
        if code not in used:
            used.add(code)
            return code
        time.sleep(1)
    raise RuntimeError("TOTP window never rolled")


def test_setup_issues_a_real_totp_secret(client, owner_headers):
    setup = req(client, "POST", "/api/auth/2fa/setup", headers=owner_headers, json={}).json()
    assert len(setup["secret"]) >= 16
    assert setup["otpauthUri"].startswith("otpauth://totp/")
    assert len(pyotp.TOTP(setup["secret"]).now()) == 6


def test_the_old_hardcoded_code_is_rejected(client, owner_headers):
    req(client, "POST", "/api/auth/2fa/setup", headers=owner_headers, json={})
    r = req(client, "POST", "/api/auth/2fa/verify", headers=owner_headers, json={"code": "123456"})
    assert r.status_code == 400


def test_unconfirmed_setup_does_not_lock_out_login(client, owner_headers):
    req(client, "POST", "/api/auth/2fa/setup", headers=owner_headers, json={})
    client.cookies.clear()
    r = req(client, "POST", "/api/auth/login", json=OWNER)
    assert "token" in r.json()


def test_recovery_codes_are_hashed_at_rest(client, enrolled):
    _, _, codes, _ = enrolled
    import asyncio
    from database import db
    row = asyncio.get_event_loop().run_until_complete(
        db.auth_users.find_one({"email": OWNER["email"]}))
    stored = {r["hash"] for r in row["recoveryCodes"]}
    assert not (stored & set(codes)), "a plaintext recovery code was found stored"


def test_password_alone_no_longer_completes_login(client, enrolled):
    client.cookies.clear()
    r = req(client, "POST", "/api/auth/login", json=OWNER)
    body = r.json()
    assert body.get("twoFactorRequired") is True
    assert "token" not in body


def test_challenge_token_cannot_read_data_on_its_own(client, enrolled):
    client.cookies.clear()
    challenge = req(client, "POST", "/api/auth/login", json=OWNER).json()["challengeToken"]
    r = req(client, "GET", "/api/customers", headers={"Authorization": f"Bearer {challenge}"})
    assert r.status_code == 401


def test_wrong_code_at_the_challenge_is_refused(client, enrolled):
    client.cookies.clear()
    challenge = req(client, "POST", "/api/auth/login", json=OWNER).json()["challengeToken"]
    r = req(client, "POST", "/api/auth/2fa/challenge",
            json={"challengeToken": challenge, "code": "111111"})
    assert r.status_code == 401


def test_a_genuine_code_completes_login_and_cannot_be_replayed(client, enrolled):
    _, totp, _, used = enrolled
    client.cookies.clear()
    challenge = req(client, "POST", "/api/auth/login", json=OWNER).json()["challengeToken"]
    code = _fresh_code(totp, used)
    r = req(client, "POST", "/api/auth/2fa/challenge",
            json={"challengeToken": challenge, "code": code})
    assert r.status_code == 200, r.text[:200]
    out = r.json()
    assert out.get("token")
    assert "twoFactorSecret" not in (out.get("user") or {})
    h2 = {"Authorization": f"Bearer {out['token']}"}
    assert req(client, "GET", "/api/customers", headers=h2).status_code == 200

    # Replay of the same code, against a fresh challenge, must fail.
    client.cookies.clear()
    challenge2 = req(client, "POST", "/api/auth/login", json=OWNER).json()["challengeToken"]
    r2 = req(client, "POST", "/api/auth/2fa/challenge",
             json={"challengeToken": challenge2, "code": code})
    assert r2.status_code == 401
    assert "already used" in r2.text.lower()


def test_recovery_code_works_once_and_reports_remaining(client, enrolled):
    _, _, codes, _ = enrolled
    client.cookies.clear()
    challenge = req(client, "POST", "/api/auth/login", json=OWNER).json()["challengeToken"]
    r = req(client, "POST", "/api/auth/2fa/challenge",
            json={"challengeToken": challenge, "code": codes[0]})
    assert r.status_code == 200, r.text[:200]
    assert r.json().get("verifiedBy") == "recovery"
    assert r.json().get("recoveryCodesRemaining") == 9

    client.cookies.clear()
    challenge2 = req(client, "POST", "/api/auth/login", json=OWNER).json()["challengeToken"]
    r2 = req(client, "POST", "/api/auth/2fa/challenge",
             json={"challengeToken": challenge2, "code": codes[0]})
    assert r2.status_code == 401


def test_trusted_device_skips_the_code_and_is_bound_to_the_browser(client, enrolled):
    _, totp, _, used = enrolled
    client.cookies.clear()
    challenge = req(client, "POST", "/api/auth/login", json=OWNER).json()["challengeToken"]
    r = req(client, "POST", "/api/auth/2fa/challenge",
            json={"challengeToken": challenge, "code": _fresh_code(totp, used), "trustDevice": True})
    assert r.status_code == 200
    device_token = r.json()["deviceToken"]

    client.cookies.clear()
    r = req(client, "POST", "/api/auth/login", json={**OWNER, "deviceToken": device_token})
    assert "token" in r.json()

    # A forged token, or the real one from a different agent, must not skip the code.
    r = req(client, "POST", "/api/auth/login", json={**OWNER, "deviceToken": "forged.token"})
    assert r.json().get("twoFactorRequired") is True

    r = req(client, "POST", "/api/auth/login", json={**OWNER, "deviceToken": device_token},
            headers={"User-Agent": "SomeoneElsesBrowser/1.0"})
    assert r.json().get("twoFactorRequired") is True


def test_disabling_requires_the_password(client, enrolled):
    headers, _, _, _ = enrolled
    r = req(client, "POST", "/api/auth/2fa/disable", headers=headers, json={"password": "wrong"})
    assert r.status_code == 403


def test_venue_policy_forces_enrolment_for_managers_but_not_cashiers(client, enrolled):
    headers, _, _, _ = enrolled
    req(client, "POST", "/api/auth/2fa/policy", headers=headers, json={"required": True})
    req(client, "POST", "/api/auth/staff/add", headers=headers, json={
        "name": "Gate Manager", "email": "gate.manager@nua.com",
        "password": "MgrPass123!", "role": "manager"})
    req(client, "POST", "/api/auth/staff/add", headers=headers, json={
        "name": "Gate Cashier2", "email": "gate.cashier2@nua.com",
        "password": "CashPass123!", "role": "cashier"})
    client.cookies.clear()

    r = req(client, "POST", "/api/auth/login",
            json={"email": "gate.manager@nua.com", "password": "MgrPass123!"})
    body = r.json()
    assert body.get("enrolmentRequired") is True
    assert "token" not in body

    r = req(client, "POST", "/api/auth/login",
            json={"email": "gate.cashier2@nua.com", "password": "CashPass123!"})
    assert "token" in r.json()
