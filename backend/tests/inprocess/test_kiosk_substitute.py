"""POST /v25/substitute is what the kiosk calls when a guest taps an 86'd
item, to suggest an in-stock alternative instead of the item just not
being orderable. The kiosk itself never carries a staff credential — it's
an unattended, unauthenticated guest surface, the same as /api/products
or the online storefront — so this needs to actually be reachable without
one (it previously required Depends(get_user), which no guest session
could ever satisfy, which is presumably why nothing had ever wired it up).
It also must never leak cost/stock/sku the way the public product list
doesn't, since a guest can see this response.
"""
import asyncio

from conftest import anon, req


def test_substitute_works_without_a_credential(anon):
    loop = asyncio.get_event_loop()
    from database import db

    loop.run_until_complete(db.products.insert_many([
        {"id": "SUB-TARGET", "name": "Sold Out Burger", "category": "Kiosk Mains",
         "price": 15.0, "cost": 6.0, "stock": 0, "sku": "SKU-TARGET", "active": True, "eightySixed": True},
        {"id": "SUB-ALT", "name": "Available Burger", "category": "Kiosk Mains",
         "price": 15.5, "cost": 6.5, "stock": 20, "sku": "SKU-ALT", "active": True},
    ]))
    try:
        r = req(anon, "POST", "/api/v25/substitute", json={"productId": "SUB-TARGET"})
        assert r.status_code == 200, r.text[:200]
        body = r.json()
        assert body["original"]["id"] == "SUB-TARGET"
        alt_ids = [s["id"] for s in body["substitutes"]]
        assert "SUB-ALT" in alt_ids

        # Trade fields must never reach a guest caller.
        for doc in [body["original"], *body["substitutes"]]:
            assert "cost" not in doc
            assert "stock" not in doc
            assert "sku" not in doc
    finally:
        loop.run_until_complete(db.products.delete_many({"id": {"$in": ["SUB-TARGET", "SUB-ALT"]}}))


def test_substitute_requires_a_product_id(anon):
    r = req(anon, "POST", "/api/v25/substitute", json={})
    assert r.status_code == 400
