"""GET/PUT/export/summary on /business/{business_id} used to be gated only
by require_owner (a role check), never checking that the caller actually
owns *that* business — any owner-role account could pull or edit any other
business's data by id. Fixed by adding an ownership check that also keeps
working for the legacy single-tenant "default" business (owned by the
synthetic "system" account, not a real user, since it predates multi-
business support)."""
import uuid

from conftest import req


def _insert_second_owner(business_id="BIZ-OTHER"):
    from database import db
    from routes.auth import hash_password
    import asyncio

    owner_id = str(uuid.uuid4())

    async def run():
        await db.auth_users.insert_one({
            "id": owner_id, "name": "ZZZ Second Owner", "email": f"{owner_id}@nua.local",
            "password_hash": hash_password("SecondOwner2026!"), "role": "owner",
            "businessId": business_id, "status": "active",
        })
    asyncio.get_event_loop().run_until_complete(run())
    return owner_id


def _headers_for(owner_id, role="owner", business_id="BIZ-OTHER"):
    import jwt
    import os
    from datetime import datetime, timedelta, timezone
    token = jwt.encode(
        {"sub": owner_id, "email": f"{owner_id}@nua.local", "role": role,
         "businessId": business_id, "exp": datetime.now(timezone.utc) + timedelta(hours=8),
         "type": "access"},
        os.environ["JWT_SECRET"], algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_owner_can_fully_manage_a_business_they_created(client, owner_headers):
    r = req(client, "POST", "/api/business/create", headers=owner_headers, json={"name": "ZZZ Owner's Cafe"})
    assert r.status_code == 200, r.text
    biz = r.json()

    assert req(client, "GET", f"/api/business/{biz['id']}", headers=owner_headers).status_code == 200
    assert req(client, "GET", f"/api/business/{biz['id']}/summary", headers=owner_headers).status_code == 200
    assert req(client, "GET", f"/api/business/{biz['id']}/export", headers=owner_headers).status_code == 200
    r2 = req(client, "PUT", f"/api/business/{biz['id']}", headers=owner_headers, json={"name": "Renamed Cafe"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["name"] == "Renamed Cafe"


def test_owner_cannot_read_or_write_a_business_they_do_not_own(client, owner_headers):
    other_owner_id = _insert_second_owner("BIZ-OTHER-1")
    other_headers = _headers_for(other_owner_id, business_id="BIZ-OTHER-1")
    r = req(client, "POST", "/api/business/create", headers=other_headers, json={"name": "ZZZ Other Owner's Bistro"})
    assert r.status_code == 200, r.text
    other_biz = r.json()

    assert req(client, "GET", f"/api/business/{other_biz['id']}", headers=owner_headers).status_code == 404
    assert req(client, "GET", f"/api/business/{other_biz['id']}/summary", headers=owner_headers).status_code == 404
    assert req(client, "GET", f"/api/business/{other_biz['id']}/export", headers=owner_headers).status_code == 404
    r2 = req(client, "PUT", f"/api/business/{other_biz['id']}", headers=owner_headers, json={"name": "Hijacked"})
    assert r2.status_code == 404, r2.text

    # And the reverse: the second owner can't reach into the first owner's business.
    r = req(client, "POST", "/api/business/create", headers=owner_headers, json={"name": "ZZZ First Owner's Diner"})
    first_biz = r.json()
    assert req(client, "GET", f"/api/business/{first_biz['id']}/summary", headers=other_headers).status_code == 404


def test_seeded_default_business_stays_reachable_by_its_own_members(client, owner_headers):
    """The bootstrap "default" business is owned by the synthetic "system"
    account, not a real user id — its real owner is whoever's own token
    businessId is "default", the account this repo's tests already log in
    as via owner_headers."""
    assert req(client, "GET", "/api/business/default", headers=owner_headers).status_code == 200
    assert req(client, "GET", "/api/business/default/summary", headers=owner_headers).status_code == 200


def test_default_business_is_not_reachable_by_an_unrelated_owner(client):
    unrelated_id = _insert_second_owner("BIZ-UNRELATED")
    unrelated_headers = _headers_for(unrelated_id, business_id="BIZ-UNRELATED")
    assert req(client, "GET", "/api/business/default", headers=unrelated_headers).status_code == 404
    assert req(client, "GET", "/api/business/default/summary", headers=unrelated_headers).status_code == 404
