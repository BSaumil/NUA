"""Iteration 19: Items System (Categories, Modifiers, Discounts, Comp/Void, Payment Links) + Roster DnD (PUT)"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def owner_token():
    r = requests.post(f"{API}/auth/login", json={"email": "owner@nuva.com", "password": "NuvaOwner2026!"}, timeout=20)
    assert r.status_code == 200, f"Owner login failed: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, r.text
    return tok


@pytest.fixture
def owner_client(owner_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"})
    return s


# ============ CATEGORIES ============
class TestCategories:
    def test_list_categories(self, owner_client):
        r = owner_client.get(f"{API}/categories", timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_update_delete_category(self, owner_client):
        r = owner_client.post(f"{API}/categories", json={"name": "TEST_CatXYZ", "sortOrder": 10})
        assert r.status_code == 200, r.text
        cat = r.json()
        assert cat["name"] == "TEST_CatXYZ"
        cid = cat["id"]
        # update
        r = owner_client.put(f"{API}/categories/{cid}", json={"name": "TEST_CatXYZ_upd"})
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_CatXYZ_upd"
        # persisted?
        lst = owner_client.get(f"{API}/categories").json()
        assert any(c["id"] == cid and c["name"] == "TEST_CatXYZ_upd" for c in lst)
        # delete
        r = owner_client.delete(f"{API}/categories/{cid}")
        assert r.status_code == 200


# ============ MODIFIERS ============
class TestModifiers:
    def test_list_modifiers(self, owner_client):
        r = owner_client.get(f"{API}/modifiers")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_update_delete_modifier(self, owner_client):
        payload = {
            "name": "TEST_MilkType", "type": "list", "mandatory": True,
            "multiSelect": False, "maxSelections": 1,
            "options": [{"name": "Whole", "price": 0}, {"name": "Almond", "price": 0.5}],
        }
        r = owner_client.post(f"{API}/modifiers", json=payload)
        assert r.status_code == 200, r.text
        m = r.json()
        assert m["name"] == "TEST_MilkType"
        assert m["mandatory"] is True
        assert len(m["options"]) == 2
        mid = m["id"]
        r = owner_client.put(f"{API}/modifiers/{mid}", json={"multiSelect": True, "maxSelections": 3})
        assert r.status_code == 200
        assert r.json()["multiSelect"] is True
        assert r.json()["maxSelections"] == 3
        r = owner_client.delete(f"{API}/modifiers/{mid}")
        assert r.status_code == 200


# ============ DISCOUNTS ============
class TestDiscounts:
    def test_create_list_delete_discount(self, owner_client):
        r = owner_client.post(f"{API}/discounts", json={"name": "TEST_10off", "type": "percentage", "value": 10})
        assert r.status_code == 200, r.text
        d = r.json()
        did = d["id"]
        lst = owner_client.get(f"{API}/discounts").json()
        assert any(x["id"] == did for x in lst)
        r = owner_client.put(f"{API}/discounts/{did}", json={"value": 15})
        assert r.status_code == 200
        assert r.json()["value"] == 15
        r = owner_client.delete(f"{API}/discounts/{did}")
        assert r.status_code == 200


# ============ COMP / VOID ============
class TestCompVoid:
    def test_create_and_list_comp_void(self, owner_client):
        r = owner_client.post(f"{API}/comp-void", json={"type": "comp", "reason": "TEST_manager_comp", "amount": 12.5})
        assert r.status_code == 200, r.text
        rec = r.json()
        assert rec["type"] == "comp"
        assert rec["amount"] == 12.5
        lst = owner_client.get(f"{API}/comp-void").json()
        assert any(x["id"] == rec["id"] for x in lst)


# ============ PAYMENT LINKS ============
class TestPaymentLinks:
    def test_create_list_delete_link(self, owner_client):
        r = owner_client.post(f"{API}/payment-links", json={"productId": "p1", "productName": "TEST_Coffee", "price": 4.5})
        assert r.status_code == 200, r.text
        link = r.json()
        assert link["url"].startswith("https://pay.nua.pos/")
        lst = owner_client.get(f"{API}/payment-links").json()
        assert any(x["id"] == link["id"] for x in lst)
        r = owner_client.delete(f"{API}/payment-links/{link['id']}")
        assert r.status_code == 200


# ============ ROSTER PUT (DnD) ============
class TestRosterPut:
    def test_create_update_roster_shift(self, owner_client):
        # Create shift on Monday
        r = owner_client.post(f"{API}/staff/roster", json={
            "staffId": "test-staff", "staffName": "TEST_Tina",
            "date": "Monday", "weekStart": "2026-01-05",
            "startTime": "09:00", "endTime": "17:00", "role": "kitchen",
        })
        assert r.status_code == 200, r.text
        shift = r.json()
        sid = shift["id"]
        # Move to Wednesday via PUT
        r = owner_client.put(f"{API}/staff/roster/{sid}", json={"date": "Wednesday"})
        assert r.status_code == 200, r.text
        assert r.json()["date"] == "Wednesday"
        # Verify persistence via GET
        lst = owner_client.get(f"{API}/staff/roster").json()
        moved = [s for s in lst if s["id"] == sid]
        assert len(moved) == 1 and moved[0]["date"] == "Wednesday"
        # Cleanup
        owner_client.delete(f"{API}/staff/roster/{sid}")

    def test_put_non_existent_shift_returns_404(self, owner_client):
        r = owner_client.put(f"{API}/staff/roster/SHIFT-DOESNOTEXIST", json={"date": "Friday"})
        assert r.status_code == 404
