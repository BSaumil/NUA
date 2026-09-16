"""routes/items_system.py (categories, modifiers, discounts, comp/void,
payment links) had ZERO tenant scoping anywhere — missed by every prior
tenant-isolation sweep. Found during a second independent final readiness
audit, commissioned specifically to check the results of the first one.

- GET /modifiers, GET /discounts, GET /payment-links had no auth
  dependency and no scoping at all: `db.<collection>.find({}, ...)`
  returned every business's full catalog to any authenticated caller.
- PUT/DELETE on a category/modifier/discount/payment-link, and
  POST /categories/{source}/merge/{target}, were gated only by
  require_owner/require_owner_or_manager (a role check, not an ownership
  check) — any owner/manager of ANY business could edit, delete, or merge
  any OTHER business's menu configuration by id.
- merge_categories's `db.products.update_many` had no businessId filter at
  all, so a merge could re-categorize every business's products sharing
  the same category name, not just the caller's own.
- create_modifier/create_discount/create_payment_link/create_comp_void
  never stamped a businessId on the new document at all.

Fixed with the same tenant_owns()/tenant_scope_filter() pattern used
throughout this codebase's other tenant-isolation fixes.
"""
import asyncio

from conftest import req


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_business(client, owner_headers, *, biz_id, email):
    from database import db
    _run(db.businesses.insert_one({
        "id": biz_id, "slug": biz_id, "name": f"Biz {biz_id}", "status": "active",
    }))
    client.post("/api/auth/register", headers=owner_headers, json={
        "name": "Items System Test Owner", "email": email, "password": "ItemsSystemTest2026!",
    })
    _run(db.auth_users.update_one({"email": email}, {"$set": {"role": "owner", "businessId": biz_id}}))
    r = client.post("/api/auth/login", json={"email": email, "password": "ItemsSystemTest2026!"})
    assert r.status_code == 200, f"login failed: {r.text[:200]}"
    client.cookies.clear()
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _cleanup_business(biz_id):
    from database import db
    _run(db.businesses.delete_many({"id": biz_id}))
    _run(db.auth_users.delete_many({"businessId": biz_id}))


# --------------------------------------------------------------- categories


def test_update_category_rejects_another_businesss_category(client, owner_headers):
    biz_b = "items-tenant-biz-cat-upd"
    try:
        biz_b_headers = _make_business(client, owner_headers, biz_id=biz_b, email="items-cat-upd-b@nua.com")
        created = req(client, "POST", "/api/categories", headers=biz_b_headers, json={"name": "B's Category"})
        assert created.status_code == 200, created.text[:200]
        cat_id = created.json()["id"]

        default_tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})
        r = req(client, "PUT", f"/api/categories/{cat_id}", headers=default_tenant, json={"name": "Hijacked"})
        assert r.status_code == 404, r.text
    finally:
        _cleanup_business(biz_b)


def test_delete_category_rejects_another_businesss_category(client, owner_headers):
    biz_b = "items-tenant-biz-cat-del"
    try:
        biz_b_headers = _make_business(client, owner_headers, biz_id=biz_b, email="items-cat-del-b@nua.com")
        created = req(client, "POST", "/api/categories", headers=biz_b_headers, json={"name": "B's Category 2"})
        cat_id = created.json()["id"]

        default_tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})
        r = req(client, "DELETE", f"/api/categories/{cat_id}", headers=default_tenant)
        assert r.status_code == 404, r.text

        from database import db
        still_there = _run(db.categories.find_one({"id": cat_id}))
        assert still_there is not None, "a rejected cross-tenant delete must not remove the category"
    finally:
        _cleanup_business(biz_b)


def test_merge_categories_rejects_a_target_belonging_to_another_business(client, owner_headers):
    biz_b = "items-tenant-biz-cat-merge"
    try:
        biz_b_headers = _make_business(client, owner_headers, biz_id=biz_b, email="items-cat-merge-b@nua.com")
        default_tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})

        own_cat = req(client, "POST", "/api/categories", headers=default_tenant, json={"name": "Own Source Cat"})
        own_cat_id = own_cat.json()["id"]
        other_cat = req(client, "POST", "/api/categories", headers=biz_b_headers, json={"name": "B's Target Cat"})
        other_cat_id = other_cat.json()["id"]

        r = req(client, "POST", f"/api/categories/{own_cat_id}/merge/{other_cat_id}", headers=default_tenant)
        assert r.status_code == 404, r.text

        from database import db
        still_there = _run(db.categories.find_one({"id": own_cat_id}))
        assert still_there is not None, "a rejected cross-tenant merge must not delete the caller's own source category"
    finally:
        _cleanup_business(biz_b)


def test_merge_categories_does_not_recategorize_another_businesss_products(client, owner_headers):
    """The real exploit: merge_categories's products.update_many had no
    businessId filter, so merging two SAME-NAMED categories (a very common
    case — most businesses start from the same seeded/default catalog)
    could silently re-tag every other business's matching products too."""
    biz_b = "items-tenant-biz-cat-prodmerge"
    try:
        biz_b_headers = _make_business(client, owner_headers, biz_id=biz_b, email="items-cat-prodmerge-b@nua.com")
        default_tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})

        # Both businesses create a same-named category (collision on purpose).
        own_source = req(client, "POST", "/api/categories", headers=default_tenant, json={"name": "Shared Name Src"})
        own_target = req(client, "POST", "/api/categories", headers=default_tenant, json={"name": "Shared Name Tgt"})
        own_source_id, own_target_id = own_source.json()["id"], own_target.json()["id"]

        from database import db
        _run(db.products.insert_one({
            "id": "ITEMS-TENANT-PROD-B1", "name": "B's Product", "price": 5.0,
            "category": "Shared Name Src", "categoryId": None, "businessId": biz_b,
        }))

        r = req(client, "POST", f"/api/categories/{own_source_id}/merge/{own_target_id}", headers=default_tenant)
        assert r.status_code == 200, r.text

        b_product = _run(db.products.find_one({"id": "ITEMS-TENANT-PROD-B1"}, {"_id": 0}))
        assert b_product["category"] == "Shared Name Src", (
            "another business's product sharing the same category NAME must not be recategorized "
            "by the caller's own merge"
        )
    finally:
        _run(__import__("database").db.products.delete_many({"id": "ITEMS-TENANT-PROD-B1"}))
        _cleanup_business(biz_b)


# ---------------------------------------------------------------- modifiers


def test_get_modifiers_never_returns_another_businesss_modifier(client, owner_headers):
    biz_b = "items-tenant-biz-mod-list"
    try:
        biz_b_headers = _make_business(client, owner_headers, biz_id=biz_b, email="items-mod-list-b@nua.com")
        created = req(client, "POST", "/api/modifiers", headers=biz_b_headers, json={"name": "B's Secret Modifier"})
        assert created.status_code == 200, created.text[:200]

        default_tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})
        r = req(client, "GET", "/api/modifiers", headers=default_tenant)
        assert r.status_code == 200, r.text
        names = [m.get("name") for m in r.json()]
        assert "B's Secret Modifier" not in names
    finally:
        _cleanup_business(biz_b)


def test_update_and_delete_modifier_reject_another_businesss_modifier(client, owner_headers):
    biz_b = "items-tenant-biz-mod-mut"
    try:
        biz_b_headers = _make_business(client, owner_headers, biz_id=biz_b, email="items-mod-mut-b@nua.com")
        created = req(client, "POST", "/api/modifiers", headers=biz_b_headers, json={"name": "B's Modifier"})
        mod_id = created.json()["id"]

        default_tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})
        r1 = req(client, "PUT", f"/api/modifiers/{mod_id}", headers=default_tenant, json={"name": "Hijacked"})
        assert r1.status_code == 404, r1.text
        r2 = req(client, "DELETE", f"/api/modifiers/{mod_id}", headers=default_tenant)
        assert r2.status_code == 404, r2.text

        from database import db
        still_there = _run(db.modifiers.find_one({"id": mod_id}))
        assert still_there is not None and still_there["name"] == "B's Modifier"
    finally:
        _cleanup_business(biz_b)


# ---------------------------------------------------------------- discounts


def test_get_discounts_never_returns_another_businesss_discount(client, owner_headers):
    biz_b = "items-tenant-biz-disc-list"
    try:
        biz_b_headers = _make_business(client, owner_headers, biz_id=biz_b, email="items-disc-list-b@nua.com")
        created = req(client, "POST", "/api/discounts", headers=biz_b_headers, json={"name": "B's Secret Discount"})
        assert created.status_code == 200, created.text[:200]

        default_tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})
        r = req(client, "GET", "/api/discounts", headers=default_tenant)
        assert r.status_code == 200, r.text
        names = [d.get("name") for d in r.json()]
        assert "B's Secret Discount" not in names
    finally:
        _cleanup_business(biz_b)


def test_update_and_delete_discount_reject_another_businesss_discount(client, owner_headers):
    biz_b = "items-tenant-biz-disc-mut"
    try:
        biz_b_headers = _make_business(client, owner_headers, biz_id=biz_b, email="items-disc-mut-b@nua.com")
        created = req(client, "POST", "/api/discounts", headers=biz_b_headers, json={"name": "B's Discount"})
        disc_id = created.json()["id"]

        default_tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})
        r1 = req(client, "PUT", f"/api/discounts/{disc_id}", headers=default_tenant, json={"name": "Hijacked"})
        assert r1.status_code == 404, r1.text
        r2 = req(client, "DELETE", f"/api/discounts/{disc_id}", headers=default_tenant)
        assert r2.status_code == 404, r2.text
    finally:
        _cleanup_business(biz_b)


# ------------------------------------------------------------- payment links


def test_get_payment_links_never_returns_another_businesss_link(client, owner_headers):
    biz_b = "items-tenant-biz-plink-list"
    try:
        biz_b_headers = _make_business(client, owner_headers, biz_id=biz_b, email="items-plink-list-b@nua.com")
        created = req(client, "POST", "/api/payment-links", headers=biz_b_headers, json={"productName": "B's Product"})
        assert created.status_code == 200, created.text[:200]

        default_tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})
        r = req(client, "GET", "/api/payment-links", headers=default_tenant)
        assert r.status_code == 200, r.text
        names = [p.get("productName") for p in r.json()]
        assert "B's Product" not in names
    finally:
        _cleanup_business(biz_b)


def test_delete_payment_link_rejects_another_businesss_link(client, owner_headers):
    biz_b = "items-tenant-biz-plink-del"
    try:
        biz_b_headers = _make_business(client, owner_headers, biz_id=biz_b, email="items-plink-del-b@nua.com")
        created = req(client, "POST", "/api/payment-links", headers=biz_b_headers, json={"productName": "B's Item"})
        link_id = created.json()["id"]

        default_tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})
        r = req(client, "DELETE", f"/api/payment-links/{link_id}", headers=default_tenant)
        assert r.status_code == 404, r.text
    finally:
        _cleanup_business(biz_b)


# ------------------------------------------------------------------ comp/void


def test_get_comp_voids_never_returns_another_businesss_record(client, owner_headers):
    biz_b = "items-tenant-biz-cv-list"
    try:
        biz_b_headers = _make_business(client, owner_headers, biz_id=biz_b, email="items-cv-list-b@nua.com")
        created = req(client, "POST", "/api/comp-void", headers=biz_b_headers, json={
            "type": "comp", "reason": "B's secret comp reason", "amount": 5})
        assert created.status_code == 200, created.text[:200]

        default_tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})
        r = req(client, "GET", "/api/comp-void", headers=default_tenant)
        assert r.status_code == 200, r.text
        reasons = [c.get("reason") for c in r.json()]
        assert "B's secret comp reason" not in reasons
    finally:
        _cleanup_business(biz_b)


def test_owner_can_still_manage_their_own_items(client, owner_headers):
    tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})
    cat = req(client, "POST", "/api/categories", headers=tenant, json={"name": "Own Managed Category"})
    assert cat.status_code == 200, cat.text[:200]
    cat_id = cat.json()["id"]
    assert req(client, "PUT", f"/api/categories/{cat_id}", headers=tenant, json={"name": "Renamed"}).status_code == 200
    assert req(client, "DELETE", f"/api/categories/{cat_id}", headers=tenant).status_code == 200

    mod = req(client, "POST", "/api/modifiers", headers=tenant, json={"name": "Own Modifier"})
    mod_id = mod.json()["id"]
    assert req(client, "PUT", f"/api/modifiers/{mod_id}", headers=tenant, json={"name": "Renamed Mod"}).status_code == 200
    assert req(client, "DELETE", f"/api/modifiers/{mod_id}", headers=tenant).status_code == 200

    disc = req(client, "POST", "/api/discounts", headers=tenant, json={"name": "Own Discount"})
    disc_id = disc.json()["id"]
    assert req(client, "PUT", f"/api/discounts/{disc_id}", headers=tenant, json={"name": "Renamed Disc"}).status_code == 200
    assert req(client, "DELETE", f"/api/discounts/{disc_id}", headers=tenant).status_code == 200


def test_discount_and_payment_link_mutations_refuse_a_doc_with_no_businessId(client, owner_headers):
    """update_discount/delete_discount/delete_payment_link have no shared-
    demo-data creation path the way categories/modifiers do (create_discount
    and create_payment_link always stamp a real businessId — verified by
    reading every insert site for these two collections), so these three
    were upgraded to tenant_owns_strict(): an untagged document is refused
    for a mutation (quarantined) rather than auto-owned by whoever asks."""
    from database import db
    tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})

    untagged_disc_id = "DISC-UNTAGGED-TEST-1"
    _run(db.discounts.insert_one({"id": untagged_disc_id, "name": "Untagged Discount", "businessId": None}))
    try:
        r1 = req(client, "PUT", f"/api/discounts/{untagged_disc_id}", headers=tenant, json={"name": "Hijacked"})
        assert r1.status_code == 404, r1.text
        r2 = req(client, "DELETE", f"/api/discounts/{untagged_disc_id}", headers=tenant)
        assert r2.status_code == 404, r2.text
        still_there = _run(db.discounts.find_one({"id": untagged_disc_id}))
        assert still_there is not None and still_there["name"] == "Untagged Discount"
    finally:
        _run(db.discounts.delete_many({"id": untagged_disc_id}))

    untagged_link_id = "PLINK-UNTAGGED-TEST-1"
    _run(db.payment_links.insert_one({"id": untagged_link_id, "productName": "Untagged Link", "businessId": None}))
    try:
        r3 = req(client, "DELETE", f"/api/payment-links/{untagged_link_id}", headers=tenant)
        assert r3.status_code == 404, r3.text
        still_there = _run(db.payment_links.find_one({"id": untagged_link_id}))
        assert still_there is not None
    finally:
        _run(db.payment_links.delete_many({"id": untagged_link_id}))
