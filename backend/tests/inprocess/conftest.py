"""In-process tests: the whole app, no server, no database daemon.

The 50+ suites in the parent directory all talk to a live BASE_URL, which is
why none of them ever ran in CI — they need a booted backend and a real Mongo
before they can even be collected. The tests in here mount the real FastAPI app
through TestClient with an in-memory Mongo underneath, so they run anywhere in
seconds and can gate a pull request.

That matters most for the things that have no second chance: whether an
endpoint is reachable without a credential, and whether a second factor is
actually checked. Both were wrong in this codebase in ways no amount of
reading the diff would have caught.
"""
import os
import sys

import pytest

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "inprocess_tests")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")

# Swap the Mongo driver for an in-memory one before anything imports database.py.
import mongomock_motor                     # noqa: E402
import motor.motor_asyncio as motor_asyncio  # noqa: E402
motor_asyncio.AsyncIOMotorClient = mongomock_motor.AsyncMongoMockClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

OWNER = {"email": "owner@nuva.com", "password": "NuvaOwner2026!"}


@pytest.fixture(scope="session")
def app():
    import server
    return server.app


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture
def anon(client):
    """A caller with no credential at all.

    The cookie jar is the trap here: TestClient keeps the Set-Cookie from any
    login that happened earlier in the session, and get_current_user prefers
    cookies over bearer headers — so an 'anonymous' request would quietly be
    authenticated and the test would pass while proving nothing.
    """
    client.cookies.clear()
    return client


_probe = [0]


def req(client, method, path, **kw):
    """Send one request in its own rate-limit bucket.

    The app allows 120 requests a minute per (tenant, identity). A suite that
    sweeps a few hundred routes blows through that and every answer comes back
    429, which is not an authorisation result. A distinct tenant header per
    probe keeps what we read as the auth decision.
    """
    _probe[0] += 1
    headers = dict(kw.pop("headers", {}))
    headers.setdefault("X-Tenant-Id", f"probe-{_probe[0]}")
    return client.request(method, path, headers=headers, **kw)


@pytest.fixture
def owner_headers(client):
    r = req(client, "POST", "/api/auth/login", json=OWNER)
    body = r.json()
    assert "token" in body, f"owner login failed: {r.status_code} {r.text[:200]}"
    client.cookies.clear()
    return {"Authorization": f"Bearer {body['token']}"}
