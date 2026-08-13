"""Retail Phase 2: a product can carry a barcode searchable from POS, and
can be grouped into variants (e.g. size/color) that are each their own
sellable Product row linked back to a non-sellable parent via parentId.
"""
from conftest import req


def _create_product(client, headers, **overrides):
    payload = {
        "name": "Test Tee", "category": "Apparel", "categoryId": None,
        "price": 25.0, "cost": 10.0, "stock": 0, "sku": "TEE-BASE",
        "image": "", "gstRate": 10.0,
    }
    payload.update(overrides)
    r = req(client, "POST", "/api/products", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_a_product_can_be_found_by_exact_barcode(client, owner_headers):
    p = _create_product(client, owner_headers, name="Barcoded Widget", sku="WID-1", barcode="0123456789012")
    r = req(client, "GET", "/api/products", params={"search": "0123456789012"}, headers=owner_headers)
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert p["id"] in ids


def test_a_product_can_be_found_by_sku_search(client, owner_headers):
    p = _create_product(client, owner_headers, name="Skew Product", sku="SKU-UNIQUE-42")
    r = req(client, "GET", "/api/products", params={"search": "SKU-UNIQUE-42"}, headers=owner_headers)
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert p["id"] in ids


def test_creating_a_variant_links_it_to_its_parent_and_lists_under_it(client, owner_headers):
    parent = _create_product(client, owner_headers, name="Variant Parent Tee", sku="TEE-PARENT")
    variant = _create_product(
        client, owner_headers, name="Variant Parent Tee — Medium / Red", sku="TEE-M-RED",
        barcode="9999999999999", parentId=parent["id"], variantAttributes={"label": "Medium / Red"},
    )
    assert variant["parentId"] == parent["id"]
    assert variant["variantAttributes"] == {"label": "Medium / Red"}

    r = req(client, "GET", f"/api/products/{parent['id']}/variants", headers=owner_headers)
    assert r.status_code == 200
    ids = [v["id"] for v in r.json()]
    assert variant["id"] in ids
    assert parent["id"] not in ids  # the parent never lists itself


def test_a_grouping_parent_flagged_hasvariants_is_still_a_real_product_row(client, owner_headers):
    parent = _create_product(client, owner_headers, name="Grouping Only Tee", sku="TEE-GROUP")
    r = req(client, "PUT", f"/api/products/{parent['id']}", json={"hasVariants": True}, headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["hasVariants"] is True

    r2 = req(client, "GET", "/api/products", headers=owner_headers)
    matched = [p for p in r2.json() if p["id"] == parent["id"]]
    assert len(matched) == 1
    assert matched[0]["hasVariants"] is True
