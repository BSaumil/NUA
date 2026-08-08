"""GET/PUT /identity/entitlements and GET /identity/customers back the new
Identity & Add-Ons settings page — the customer-identity layer was already
being written on every checkout and booking (create_or_match /
record_touchpoint) but had no owner-facing screen at all until this round.
"""
import asyncio
import uuid

from conftest import req


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_get_entitlements_returns_sane_defaults(client, owner_headers):
    r = req(client, "GET", "/api/identity/entitlements", headers=owner_headers)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body["feature_flags"]["customer_identity"] is True


def test_owner_can_toggle_an_addon_and_it_persists(client, owner_headers):
    # PUT replaces the whole feature_flags object (it's not a partial
    # merge) — the real settings page always sends its full current flag
    # set back, same as here, so this must too or it silently disables
    # every other addon for every test that runs after it in this session.
    original = req(client, "GET", "/api/identity/entitlements", headers=owner_headers).json()
    try:
        toggled = dict(original["feature_flags"], **{"punch_card.enabled": True})
        updated = req(client, "PUT", "/api/identity/entitlements", headers=owner_headers, json={
            "addons_enabled": original["addons_enabled"],
            "feature_flags": toggled,
        })
        assert updated.status_code == 200, updated.text[:200]
        assert updated.json()["feature_flags"]["punch_card.enabled"] is True

        fetched = req(client, "GET", "/api/identity/entitlements", headers=owner_headers)
        assert fetched.json()["feature_flags"]["punch_card.enabled"] is True
        # customer_identity is the one flag that can never be toggled off
        assert fetched.json()["feature_flags"]["customer_identity"] is True
    finally:
        req(client, "PUT", "/api/identity/entitlements", headers=owner_headers, json={
            "addons_enabled": original["addons_enabled"], "feature_flags": original["feature_flags"],
        })


def test_search_finds_a_seeded_identity_customer(client, owner_headers):
    from database import db

    cid = str(uuid.uuid4())
    _run(db.identity_customers.delete_many({"id": cid}))
    _run(db.identity_customers.insert_one({
        "id": cid, "venue_id": "main", "name": "Identity Search Target",
        "phone": "0400777888", "email": None, "source": "pos_checkout",
        "visit_count": 2, "last_seen_at": "2026-08-01T00:00:00+00:00",
    }))

    r = req(client, "GET", "/api/identity/customers", headers=owner_headers, params={"search": "Identity Search Target"})
    assert r.status_code == 200, r.text[:200]
    ids = {c["id"] for c in r.json()}
    assert cid in ids


def test_identity_endpoints_require_authentication(anon):
    assert req(anon, "GET", "/api/identity/entitlements").status_code == 401
    assert req(anon, "GET", "/api/identity/customers").status_code == 401
