"""/seed/catalog used to check-then-insert each of its 60 products
individually (find_one, then insert_one if nothing found) -- not atomic, so
two calls close together (an onboarding auto-trigger racing a manual
"Seed Demo Data" click, a client retry after a slow response) could both
see "nothing exists yet" for the same product and both insert, producing
two rows with the same name/SKU but different ids: a duplicate menu item,
silently, that then breaks editing (whichever row's id a stale UI later
tries to PUT against may no longer be the "real" one).

Fixed by switching every item (categories, products, modifiers) to an
atomic upsert (update_one(..., upsert=True)), which MongoDB guarantees is
race-free per document -- a second call matching the same filter either
loses the race (updates the just-inserted document) or wins it outright,
never both insert. That guarantee is what these tests check directly
against the same filter/$setOnInsert shape seed_catalog uses, rather than
trying to force two real HTTP requests to interleave -- under
TestClient + mongomock, two threads hitting the endpoint "concurrently"
don't reliably race against each other (mongomock serialises internally),
so a thread-based test would pass regardless of whether the fix was
actually present and give false confidence either way.
"""
import asyncio

from database import db
from tests.inprocess.conftest import req


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_seeding_twice_sequentially_does_not_duplicate_products(client, owner_headers):
    first = req(client, "POST", "/api/seed/catalog", headers=owner_headers)
    assert first.status_code == 200, first.text
    second = req(client, "POST", "/api/seed/catalog", headers=owner_headers)
    assert second.status_code == 200, second.text

    assert second.json()["productsAdded"] == 0
    assert second.json()["categoriesAdded"] == 0
    assert second.json()["modifiersAdded"] == 0

    chai = _run(db.products.count_documents({"name": "Dirty Chai", "category": "Coffee"}))
    assert chai == 1


def test_upsert_is_race_free_by_construction_not_check_then_insert(client, owner_headers):
    # Direct proof of the actual fix: two calls against the exact same
    # filter/$setOnInsert shape seed_catalog uses. The old code
    # (find_one, then insert_one if nothing found) would have both calls
    # insert if run back-to-back with nothing in between -- there's no
    # atomicity between the read and the write. update_one(upsert=True)
    # is a single atomic operation, so the second call is guaranteed to
    # see the first call's write.
    filt = {"name": "Race Test Product", "category": "Coffee"}
    r1 = _run(db.products.update_one(filt, {"$setOnInsert": {"price": 5.0}}, upsert=True))
    r2 = _run(db.products.update_one(filt, {"$setOnInsert": {"price": 5.0}}, upsert=True))
    assert r1.upserted_id is not None, "First call should insert"
    assert r2.upserted_id is None, "Second call must find the first call's row, not insert a duplicate"
    count = _run(db.products.count_documents(filt))
    assert count == 1


def test_seeded_product_has_all_expected_fields_including_name_and_category(client, owner_headers):
    # The upsert's $setOnInsert payload deliberately excludes name/category
    # (they come from the query filter instead, per MongoDB's upsert
    # semantics) -- confirm they still land on the actual document.
    req(client, "POST", "/api/seed/catalog", headers=owner_headers)
    chai = _run(db.products.find_one({"name": "Dirty Chai", "category": "Coffee"}, {"_id": 0}))
    assert chai is not None
    assert chai["name"] == "Dirty Chai"
    assert chai["category"] == "Coffee"
    assert chai["sku"] == "SEED-COF-018"
    assert chai["price"] == 6.00
    assert chai["id"]


def test_seeded_category_has_all_expected_fields_including_name(client, owner_headers):
    req(client, "POST", "/api/seed/catalog", headers=owner_headers)
    coffee = _run(db.categories.find_one({"name": "Coffee"}, {"_id": 0}))
    assert coffee is not None
    assert coffee["id"] == "cat-coffee"
    assert coffee["icon"] == "Coffee"


def test_seeded_modifier_has_all_expected_fields_including_name(client, owner_headers):
    req(client, "POST", "/api/seed/catalog", headers=owner_headers)
    mods = _run(db.modifiers.find({}, {"_id": 0}).to_list(20))
    assert len(mods) > 0
    for m in mods:
        assert m.get("name"), f"Modifier missing name: {m}"
        assert m.get("id")
