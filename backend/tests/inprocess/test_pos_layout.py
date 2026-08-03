"""Structured POS layout customization.

Deliberately not free-form drag-and-drop: a POS is touch/speed-critical, so
what's configurable is a small, whitelisted set of options within three
fixed regions (cart side, tile density, which quick actions show) rather
than arbitrary positioning that could produce an unusable arrangement mid-
service.
"""
from conftest import req


def test_defaults_before_anything_is_saved(client, owner_headers):
    r = req(client, "GET", "/api/pos/layout", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["cartPosition"] == "right"
    assert body["tileSize"] == "comfortable"
    assert body["quickActions"] == {"hold": True, "tabs": True}


def test_save_and_read_back(client, owner_headers):
    r = req(client, "POST", "/api/pos/layout", headers=owner_headers, json={
        "cartPosition": "left", "tileSize": "large",
        "quickActions": {"hold": False, "tabs": True}})
    assert r.status_code == 200
    assert r.json() == {"cartPosition": "left", "tileSize": "large",
                        "quickActions": {"hold": False, "tabs": True}}

    r = req(client, "GET", "/api/pos/layout", headers=owner_headers)
    assert r.json()["cartPosition"] == "left"
    assert r.json()["tileSize"] == "large"
    assert r.json()["quickActions"]["hold"] is False


def test_invalid_values_fall_back_to_defaults_rather_than_erroring(client, owner_headers):
    r = req(client, "POST", "/api/pos/layout", headers=owner_headers, json={
        "cartPosition": "sideways", "tileSize": "gigantic", "quickActions": {}})
    assert r.status_code == 200
    body = r.json()
    assert body["cartPosition"] == "right"
    assert body["tileSize"] == "comfortable"
    assert body["quickActions"] == {"hold": True, "tabs": True}


def test_a_partial_quick_actions_update_does_not_drop_the_other_key(client, owner_headers):
    req(client, "POST", "/api/pos/layout", headers=owner_headers, json={
        "quickActions": {"hold": False}})
    r = req(client, "GET", "/api/pos/layout", headers=owner_headers)
    assert r.json()["quickActions"] == {"hold": False, "tabs": True}


def test_saving_requires_owner_or_manager(client, owner_headers):
    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Layout Cashier", "email": "layout.cashier@nuva.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login",
              json={"email": "layout.cashier@nuva.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    ch = {"Authorization": f"Bearer {tok['token']}"}

    assert req(client, "POST", "/api/pos/layout", headers=ch,
               json={"cartPosition": "left"}).status_code == 403
    # But any signed-in staff can still read it — the POS terminal needs to.
    assert req(client, "GET", "/api/pos/layout", headers=ch).status_code == 200


def test_reading_refuses_an_anonymous_caller(anon):
    assert req(anon, "GET", "/api/pos/layout").status_code == 401
