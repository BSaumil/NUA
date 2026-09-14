"""routes/ops.py's GET /ops/backup — owner-gated but with no tenant check
of its own — called services/backup.create_backup() with no scoping at
all, dumping every business's customers, transactions, and auth_users
(password hashes included) on the whole deployment into one downloadable
archive any owner could request. /ops/errors and /ops/client-errors had
the same unscoped-read gap, one tier down in severity (crash reports and
stack traces, not raw customer/transaction data).
"""
import asyncio
import io
import json
import tarfile

from bson import json_util
from database import db
from tests.inprocess.conftest import req


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _login_as(client, owner_headers, *, email, business_id):
    client.post("/api/auth/register", headers=owner_headers, json={
        "name": "Ops Test Owner", "email": email, "password": "OpsTenantTest2026!",
    })
    _run(db.auth_users.update_one({"email": email}, {"$set": {"role": "owner", "businessId": business_id}}))
    r = client.post("/api/auth/login", json={"email": email, "password": "OpsTenantTest2026!"})
    assert r.status_code == 200, f"login failed: {r.text[:200]}"
    client.cookies.clear()
    body = r.json()
    return {"Authorization": f"Bearer {body['token']}"}


def _archive_customer_names(resp_content: bytes) -> set:
    names = set()
    with tarfile.open(fileobj=io.BytesIO(resp_content), mode="r:gz") as tar:
        if "customers.json" not in tar.getnames():
            return names
        docs = json_util.loads(tar.extractfile("customers.json").read())
        for d in docs:
            if d.get("name"):
                names.add(d["name"])
    return names


def test_backup_download_does_not_include_another_businesss_customers(client, owner_headers):
    other = _login_as(client, owner_headers, email="ops.backup.other@nua.com", business_id="ops-backup-other-biz")

    created = req(client, "POST", "/api/customers", headers=other, json={
        "name": "Secret Other Biz Customer", "email": "secretother@nua.com", "phone": "0400777888"})
    assert created.status_code == 200, created.text[:200]
    customer_id = created.json()["id"]
    try:
        r = req(client, "GET", "/api/ops/backup", headers=owner_headers)
        assert r.status_code == 200, r.text[:200]
        names = _archive_customer_names(r.content)
        assert "Secret Other Biz Customer" not in names, (
            "a business's backup download must never include another business's customer records"
        )

        # Sanity: the other business's own backup DOES include it.
        r_theirs = req(client, "GET", "/api/ops/backup", headers=other)
        assert "Secret Other Biz Customer" in _archive_customer_names(r_theirs.content)
    finally:
        _run(db.customers.delete_one({"id": customer_id}))


def test_error_logs_are_scoped_per_business(client, owner_headers):
    other = _login_as(client, owner_headers, email="ops.errors.other@nua.com", business_id="ops-errors-other-biz")

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    _run(db.error_log.insert_one({
        "requestId": "req-otherbiz", "method": "GET", "path": "/api/secret",
        "actor": {"businessId": "ops-errors-other-biz"}, "error": "Other biz secret error",
        "traceback": "x", "at": now, "expiresAt": now + timedelta(days=30),
        "businessId": "ops-errors-other-biz",
    }))
    _run(db.client_error_log.insert_one({
        "message": "Other biz client crash", "stack": "x", "url": "x", "userAgent": "x",
        "actor": {"businessId": "ops-errors-other-biz"}, "at": now, "expiresAt": now + timedelta(days=30),
        "businessId": "ops-errors-other-biz",
    }))
    try:
        mine_errors = req(client, "GET", "/api/ops/errors", headers=owner_headers).json()["errors"]
        assert not any(e["requestId"] == "req-otherbiz" for e in mine_errors)

        mine_client_errors = req(client, "GET", "/api/ops/client-errors", headers=owner_headers).json()["errors"]
        assert not any(e["message"] == "Other biz client crash" for e in mine_client_errors)

        theirs_errors = req(client, "GET", "/api/ops/errors", headers=other).json()["errors"]
        assert any(e["requestId"] == "req-otherbiz" for e in theirs_errors)
    finally:
        _run(db.error_log.delete_one({"requestId": "req-otherbiz"}))
        _run(db.client_error_log.delete_one({"message": "Other biz client crash"}))
