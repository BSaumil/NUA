"""POST /loyalty/v2/guest-lookup — a customer checking their own points/tier
by phone, with no staff login. Unauthenticated by design (same posture as
/vouchers/public-check): returns first name only, never the full customer
record, and a phone that matches nothing looks the same as a genuine miss.
"""
import asyncio
import uuid

from conftest import req


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_guest_lookup_finds_a_real_customer_by_phone(client, owner_headers):
    from database import db

    cust_id = str(uuid.uuid4())
    phone = "04" + str(uuid.uuid4().int)[:8]
    _run(db.customers.delete_many({"id": cust_id}))
    _run(db.customers.insert_one({
        "id": cust_id, "name": "Priya Sharma", "email": "priya@test.com",
        "phone": phone, "points": 250, "visits": 4, "totalSpent": 120.0,
    }))

    r = req(client, "POST", "/api/loyalty/v2/guest-lookup", json={"phone": phone})
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body["found"] is True
    assert body["firstName"] == "Priya"
    assert body["points"] == 250
    assert "email" not in body
    assert "phone" not in body
    assert "customerId" not in body


def test_guest_lookup_on_an_unknown_phone_returns_a_generic_miss(client):
    nonexistent_phone = "09" + str(uuid.uuid4().int)[:9]
    r = req(client, "POST", "/api/loyalty/v2/guest-lookup", json={"phone": nonexistent_phone})
    assert r.status_code == 200, r.text[:200]
    assert r.json() == {"found": False}


def test_guest_lookup_requires_no_authentication(anon):
    r = req(anon, "POST", "/api/loyalty/v2/guest-lookup", json={"phone": "0400000000"})
    assert r.status_code == 200, r.text[:200]


def test_guest_lookup_rejects_an_empty_phone(client):
    r = req(client, "POST", "/api/loyalty/v2/guest-lookup", json={"phone": ""})
    assert r.status_code == 400
