"""Walk-in AI Seat and reservation table-allocation now write to the real
floor-plan tables (db.floor_plans[].tables[]) instead of the always-empty
db.floor_tables collection that nothing ever populated.
"""
from tests.inprocess.conftest import req


def _create_plan(client, owner_headers, tables):
    r = req(client, "POST", "/api/floor-plans", headers=owner_headers, json={
        "name": "Main Floor", "locationId": "loc-1", "tables": tables, "sections": [],
    })
    assert r.status_code == 200, r.text
    return r.json()


def _table(id_, number, capacity, status="available", section=None):
    return {
        "id": id_, "number": number, "capacity": capacity, "maxCovers": capacity,
        "shape": "square", "x": 0, "y": 0, "width": 60, "height": 60, "rotation": 0,
        "section": section, "status": status, "isActive": True,
    }


def test_walkin_ai_assign_with_no_tables_configured_returns_a_setup_error_not_a_500(client, owner_headers):
    r = req(client, "POST", "/api/walkins/ai-assign", headers=owner_headers, json={"partySize": 2})
    assert r.status_code == 404
    assert r.json()["detail"] == "No tables are configured yet"


def test_walkin_ai_assign_recommends_a_real_configured_table(client, owner_headers):
    # Capacities in the 80s — see the note above about session-scoped state.
    _create_plan(client, owner_headers, [
        _table("TBL-1", "1", 80, section="Patio"),
        _table("TBL-2", "2", 84, section="Main"),
        _table("TBL-3", "3", 86, section="Main"),
    ])
    r = req(client, "POST", "/api/walkins/ai-assign", headers=owner_headers, json={"partySize": 84})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["assigned"] is True
    # Smallest table that still fits the party wins.
    assert body["recommended"]["tableId"] == "TBL-2"
    assert body["recommended"]["capacity"] == 84
    assert body["recommended"]["floor"] == "Main Floor"
    assert any(a["tableId"] == "TBL-3" for a in body["alternatives"])
    # Nothing has been seated yet — recommending is not committing.
    plans = req(client, "GET", "/api/floor-plans", headers=owner_headers).json()
    tables = {t["id"]: t for p in plans for t in p["tables"]}
    assert tables["TBL-2"]["status"] == "available"


def test_walkin_seat_commits_and_updates_the_real_floor_plan(client, owner_headers):
    plan = _create_plan(client, owner_headers, [_table("TBL-10", "10", 4)])
    r = req(client, "POST", "/api/walkins/seat", headers=owner_headers, json={"tableId": "TBL-10", "partySize": 3})
    assert r.status_code == 200, r.text
    assert r.json()["assigned"] is True

    plans = req(client, "GET", "/api/floor-plans", headers=owner_headers).json()
    tbl = next(t for p in plans for t in p["tables"] if t["id"] == "TBL-10")
    assert tbl["status"] == "occupied"
    assert tbl["currentReservationId"].startswith("WALK-")


def test_walkin_seat_prevents_double_allocation(client, owner_headers):
    _create_plan(client, owner_headers, [_table("TBL-20", "20", 4)])
    first = req(client, "POST", "/api/walkins/seat", headers=owner_headers, json={"tableId": "TBL-20"})
    assert first.status_code == 200

    second = req(client, "POST", "/api/walkins/seat", headers=owner_headers, json={"tableId": "TBL-20"})
    assert second.status_code == 409
    assert "already occupied" in second.json()["detail"]


# These three tests use large, mutually-exclusive capacity/partySize values
# (90+) deliberately not used by any other test in this file — the test
# client/database is session-scoped (see conftest.py), so floor plans
# created by earlier tests are still present, and a party size that any
# earlier test's tables could also satisfy would make the ranking
# assertions flaky depending on test order.
def test_walkin_ai_assign_respects_capacity_and_skips_occupied_tables(client, owner_headers):
    _create_plan(client, owner_headers, [
        _table("TBL-30", "30", 91, status="occupied"),
        _table("TBL-31", "31", 91, status="available"),
    ])
    r = req(client, "POST", "/api/walkins/ai-assign", headers=owner_headers, json={"partySize": 91})
    assert r.status_code == 200
    body = r.json()
    assert body["recommended"]["tableId"] == "TBL-31"


def test_walkin_ai_assign_reports_no_suitable_table_when_all_occupied(client, owner_headers):
    _create_plan(client, owner_headers, [_table("TBL-40", "40", 92, status="occupied")])
    r = req(client, "POST", "/api/walkins/ai-assign", headers=owner_headers, json={"partySize": 92})
    assert r.status_code == 200
    body = r.json()
    assert body["assigned"] is False
    assert body["reason"] == "No suitable table free right now"


def test_walkin_ai_assign_surfaces_recognised_guest_profile(client, owner_headers):
    _create_plan(client, owner_headers, [_table("TBL-50", "50", 93)])
    cust = req(client, "POST", "/api/customers", headers=owner_headers, json={
        "name": "Priya Sharma", "email": "priya.walkin@example.com", "phone": "0400000111",
        "isVip": True,
    })
    assert cust.status_code == 200, cust.text
    customer_id = cust.json()["id"]

    r = req(client, "POST", "/api/walkins/ai-assign", headers=owner_headers,
            json={"partySize": 93, "customerId": customer_id})
    assert r.status_code == 200
    guest = r.json()["guest"]
    assert guest["name"] == "Priya Sharma"
    assert guest["isVip"] is True
