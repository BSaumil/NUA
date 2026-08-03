"""Ephemeral collections get an expiry; financial ones deliberately don't.

Kiosk carts, in-app notifications and login lockouts pick up an `expiresAt`
(or, for login_attempts, reuse the existing `locked_until`) at write time,
backed by a TTL index. The important negative here is just as real as the
positive: transactions, refunds and the audit log must never appear in the
retention policy, because an automatic purge job is not something that
should ever be able to touch a financial record.
"""
from datetime import datetime, timedelta, timezone

from conftest import req


def test_kiosk_session_carries_an_expiry(client, owner_headers):
    # /kiosk is a staff-operated terminal (registered under the protected
    # route tree in App.js, not the public one) — it authenticates the same
    # as any other staff screen.
    r = req(client, "POST", "/api/v25/kiosk/session", json={"guests": 2, "tableId": "T-RET"},
            headers=owner_headers)
    assert r.status_code == 200

    import asyncio
    from database import db
    row = asyncio.get_event_loop().run_until_complete(
        db.kiosk_sessions.find_one({"id": r.json()["id"]}))
    assert row.get("expiresAt") is not None
    # Mongo (and mongomock) hand back naive UTC datetimes even though a
    # tz-aware one was stored.
    expires = row["expiresAt"]
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    assert expires > datetime.now(timezone.utc)


def test_notification_carries_an_expiry():
    import asyncio
    from services import notification_service
    loop = asyncio.get_event_loop()
    doc = loop.run_until_complete(notification_service.send(
        kind="system", title="retention probe", role="owner"))
    assert doc.get("expiresAt") is not None
    assert doc["expiresAt"] > datetime.now(timezone.utc)


def test_retention_status_lists_only_ephemeral_collections(client, owner_headers):
    r = req(client, "GET", "/api/ops/retention", headers=owner_headers)
    assert r.status_code == 200
    collections = {row["collection"] for row in r.json()["policy"]}
    assert collections == {"kiosk_sessions", "notifications", "login_attempts"}
    assert "transactions" not in collections
    assert "audit_log" not in collections
    assert "bas_reports" not in collections


def test_retention_status_requires_owner_or_manager(anon):
    assert req(anon, "GET", "/api/ops/retention").status_code == 401


def test_purge_removes_only_what_is_already_past_expiry(client, owner_headers):
    import asyncio
    from database import db
    loop = asyncio.get_event_loop()

    # One already expired, one still fresh.
    loop.run_until_complete(db.kiosk_sessions.insert_many([
        {"id": "KSK-OLD", "status": "active", "cart": [],
         "expiresAt": datetime.now(timezone.utc) - timedelta(days=1)},
        {"id": "KSK-FRESH", "status": "active", "cart": [],
         "expiresAt": datetime.now(timezone.utc) + timedelta(days=1)},
    ]))

    r = req(client, "POST", "/api/ops/retention/purge", headers=owner_headers)
    assert r.status_code == 200

    remaining = loop.run_until_complete(
        db.kiosk_sessions.find({"id": {"$in": ["KSK-OLD", "KSK-FRESH"]}}).to_list(10))
    ids = {row["id"] for row in remaining}
    assert ids == {"KSK-FRESH"}, "purge should remove the expired row and leave the fresh one"
