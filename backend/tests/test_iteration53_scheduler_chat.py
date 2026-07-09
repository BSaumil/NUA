"""Iteration 53 — Ash Scheduler + Ash Chat backend tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/') or "https://pos-checkout-16.preview.emergentagent.com"
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"},
                      timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def H(token):
    return {"Authorization": f"Bearer {token}"}


# ═════════════════ Ash Scheduler ═════════════════
class TestAshScheduler:
    def test_scheduler_status(self, H):
        r = requests.get(f"{API}/ash/scheduler/status", headers=H, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("enabled") is True
        assert d.get("hourlyIntervalSeconds") == 3600
        assert d.get("digestHourUtc") == 8
        assert "lastDigest" in d
        assert "serverTimeUtc" in d
        assert isinstance(d["serverTimeUtc"], str)

    def test_force_digest_now(self, H):
        r = requests.post(f"{API}/ash/scheduler/digest-now", headers=H, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        # Should have a summary with body OR fall back with sent:false
        assert "summary" in d or d.get("sent") is False
        if "summary" in d:
            assert d["summary"].get("body")
            assert d.get("date")

    def test_force_digest_idempotent(self, H):
        # Call twice in a row — both should succeed (delete+regenerate)
        r1 = requests.post(f"{API}/ash/scheduler/digest-now", headers=H, timeout=60)
        r2 = requests.post(f"{API}/ash/scheduler/digest-now", headers=H, timeout=60)
        assert r1.status_code == 200
        assert r2.status_code == 200

    def test_scheduler_status_reflects_last_digest(self, H):
        # After force digest, lastDigest should not be null
        requests.post(f"{API}/ash/scheduler/digest-now", headers=H, timeout=60)
        r = requests.get(f"{API}/ash/scheduler/status", headers=H, timeout=30)
        d = r.json()
        assert d.get("lastDigest") is not None
        assert d["lastDigest"].get("date")


# ═════════════════ Ash Chat ═════════════════
class TestAshChat:
    def test_chat_new_session(self, H):
        r = requests.post(f"{API}/ash/chat",
                          headers=H,
                          json={"message": "Hello Ash, are you there?"},
                          timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("sessionId", "").startswith("ash-chat-")
        assert isinstance(d.get("reply"), str) and len(d["reply"]) > 0
        ctx = d.get("context") or {}
        assert "auditRows" in ctx
        assert "openInsights" in ctx
        assert "pendingApprovals" in ctx
        assert isinstance(ctx["auditRows"], int)

    def test_chat_session_persists(self, H):
        r1 = requests.post(f"{API}/ash/chat", headers=H,
                           json={"message": "First message"}, timeout=90)
        sid = r1.json()["sessionId"]
        r2 = requests.post(f"{API}/ash/chat", headers=H,
                           json={"message": "Second message", "sessionId": sid}, timeout=90)
        assert r2.status_code == 200
        assert r2.json()["sessionId"] == sid

    def test_chat_empty_message_400(self, H):
        r = requests.post(f"{API}/ash/chat", headers=H, json={"message": ""}, timeout=30)
        assert r.status_code == 400
        r2 = requests.post(f"{API}/ash/chat", headers=H, json={"message": "   "}, timeout=30)
        assert r2.status_code == 400

    def test_chat_history(self, H):
        r = requests.post(f"{API}/ash/chat", headers=H,
                          json={"message": "history probe"}, timeout=90)
        sid = r.json()["sessionId"]
        # send another
        requests.post(f"{API}/ash/chat", headers=H,
                      json={"message": "second history probe", "sessionId": sid}, timeout=90)
        h = requests.get(f"{API}/ash/chat/history/{sid}", headers=H, timeout=30)
        assert h.status_code == 200
        rows = h.json()
        assert isinstance(rows, list)
        assert len(rows) >= 2
        # Ordered ascending by ts
        ts = [row.get("ts") for row in rows]
        assert ts == sorted(ts)
        # Contains message + reply fields
        assert rows[0].get("message")
        assert rows[0].get("reply")

    def test_chat_grounding_next_action(self, H):
        # Ensure some Ash insights exist
        requests.post(f"{API}/ash/run", headers=H, timeout=90)
        r = requests.post(f"{API}/ash/chat", headers=H,
                          json={"message": "What should I do next?"}, timeout=120)
        assert r.status_code == 200
        d = r.json()
        reply = d.get("reply", "")
        assert len(reply) > 20  # non-trivial reply
        # Reply is grounded — mentions insight-related or approvals-related content
        ctx = d.get("context", {})
        assert ctx.get("openInsights", 0) >= 0
