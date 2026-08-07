"""POST /audit/restore/{entity_type}/{entity_id}/{version} already existed
and worked, but required a ?collection= query param the frontend had no
reliable way to supply — entity_type ("product") and the real Mongo
collection ("products") diverge often enough (singular/plural, "category"
-> "categories") that guessing it client-side risked restoring into the
wrong collection. Added a server-side entity_type -> collection map so the
common cases work with no collection param at all, which is what unlocked
building the "Restore to this version" button in AuditLogUniversal.jsx.
"""
from conftest import req


def test_restoring_a_product_works_without_a_collection_param(client, owner_headers):
    # Every call here needs to land in the SAME businessId bucket for the
    # audit trail to line up. Two different code paths resolve it two
    # different ways: entity_service's stamped_insert/update reads it from
    # the request's X-Tenant-Id header (via actor_context middleware, which
    # prefers the header over the token), while this route reads it
    # straight off the decoded JWT (`user["businessId"]`, "default" for the
    # OWNER fixture). The shared req() helper stamps a fresh per-call
    # X-Tenant-Id to dodge rate limiting, which would desync the two — so
    # pin the header to "default" here to match the token instead.
    tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})

    created = req(client, "POST", "/api/products", headers=tenant, json={
        "name": "Audit Widget", "price": 10, "cost": 4, "category": "Test",
        "stock": 20, "sku": "AUDIT-WIDGET-1"})
    assert created.status_code == 200, created.text[:200]
    product_id = created.json()["id"]

    updated = req(client, "PUT", f"/api/products/{product_id}", headers=tenant, json={"price": 25})
    assert updated.status_code == 200, updated.text[:200]
    assert updated.json()["price"] == 25

    events = req(client, "GET", "/api/audit/events", headers=tenant,
                 params={"entity_type": "product", "entity_id": product_id}).json()
    update_event = next(e for e in events if e["action"] == "updated")
    version = update_event["before"]["version"]

    restored = req(client, "POST", f"/api/audit/restore/product/{product_id}/{version}", headers=tenant)
    assert restored.status_code == 200, restored.text[:200]
    assert restored.json()["price"] == 10


def test_restoring_an_unmapped_entity_type_without_collection_is_a_clear_400(client, owner_headers):
    r = req(client, "POST", "/api/audit/restore/some_unmapped_thing/xyz/1", headers=owner_headers)
    assert r.status_code == 400
    assert "collection" in r.json()["detail"].lower()


def test_restoring_requires_owner_or_manager(client, owner_headers):
    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Audit Cashier", "email": "audit.cashier@nua.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={
        "email": "audit.cashier@nua.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    cashier_headers = {"Authorization": f"Bearer {tok['token']}"}

    r = req(client, "POST", "/api/audit/restore/product/xyz/1", headers=cashier_headers)
    assert r.status_code == 403
