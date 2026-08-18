"""Cancelling a booking no longer hard-deletes it, and a cancelled/no-show
booking can be brought back to confirmed without losing anything — table
allocation aside, which is deliberately not auto-restored (see the route's
own docstring).
"""
from tests.inprocess.conftest import req


def _create_reservation(client, owner_headers, **overrides):
    body = {
        "guestName": "Jamie Lee", "partySize": 4, "date": "2026-09-01", "time": "19:00",
        "source": "phone", "notes": "Window seat if possible",
    }
    body.update(overrides)
    r = req(client, "POST", "/api/reservations", headers=owner_headers, json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_cancel_does_not_delete_the_booking(client, owner_headers):
    res = _create_reservation(client, owner_headers)
    r = req(client, "POST", f"/api/reservations/{res['id']}/cancel", headers=owner_headers,
            json={"reason": "Guest called to cancel"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "cancelled"
    assert body["cancellationReason"] == "Guest called to cancel"
    # Every other field survives untouched.
    assert body["id"] == res["id"]
    assert body["guestName"] == "Jamie Lee"
    assert body["partySize"] == 4
    assert body["date"] == "2026-09-01"
    assert body["notes"] == "Window seat if possible"

    still_there = req(client, "GET", f"/api/reservations/{res['id']}", headers=owner_headers)
    assert still_there.status_code == 200
    assert still_there.json()["status"] == "cancelled"


def test_restore_brings_a_cancelled_booking_back_to_confirmed(client, owner_headers):
    res = _create_reservation(client, owner_headers, guestName="Priya Patel")
    req(client, "POST", f"/api/reservations/{res['id']}/cancel", headers=owner_headers, json={})

    r = req(client, "POST", f"/api/reservations/{res['id']}/restore", headers=owner_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "confirmed"
    assert body["cancellationReason"] is None
    assert body["guestName"] == "Priya Patel"


def test_restore_brings_a_no_show_booking_back_and_reverses_the_count(client, owner_headers):
    # No X-Tenant-Id override here (unlike the audit-trail test below) —
    # POST /customers stamps businessId from the request's actor context
    # (header-priority), but GET /customers filters by the JWT's businessId
    # only. Adding any custom tenant header on the create call would make
    # the customer invisible to the list call that owner_headers alone can
    # see, so every call in this test deliberately uses the plain,
    # unmodified owner_headers token — bypassing req()'s per-call
    # X-Tenant-Id injection instead of fighting it.
    cust = client.post("/api/customers", headers=owner_headers, json={
        "name": "Sam Torres", "email": "sam.torres@example.com", "phone": "0400000222",
    })
    assert cust.status_code == 200, cust.text
    customer_id = cust.json()["id"]

    def _no_show_count():
        rows = client.get("/api/customers", headers=owner_headers, params={"search": "Sam Torres"}).json()
        return next(c for c in rows if c["id"] == customer_id)["noShowCount"]

    res = client.post("/api/reservations", headers=owner_headers, json={
        "guestName": "Jamie Lee", "partySize": 4, "date": "2026-09-01", "time": "19:00",
        "source": "phone", "customerId": customer_id,
    }).json()
    no_show = client.post(f"/api/reservations/{res['id']}/no-show", headers=owner_headers)
    assert no_show.status_code == 200
    assert _no_show_count() == 1

    r = client.post(f"/api/reservations/{res['id']}/restore", headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"
    assert _no_show_count() == 0


def test_cannot_restore_a_booking_that_was_never_cancelled_or_no_show(client, owner_headers):
    res = _create_reservation(client, owner_headers)
    r = req(client, "POST", f"/api/reservations/{res['id']}/restore", headers=owner_headers)
    assert r.status_code == 400
    assert "cancelled or no-show" in r.json()["detail"]


def test_cannot_cancel_an_already_completed_booking(client, owner_headers):
    res = _create_reservation(client, owner_headers)
    req(client, "POST", f"/api/reservations/{res['id']}/seat", headers=owner_headers)
    req(client, "POST", f"/api/reservations/{res['id']}/complete", headers=owner_headers)

    r = req(client, "POST", f"/api/reservations/{res['id']}/cancel", headers=owner_headers, json={})
    assert r.status_code == 400
    assert "already completed" in r.json()["detail"]


def test_cancel_and_restore_are_recorded_in_the_audit_trail(client, owner_headers):
    # audit_service's write path (log_event, via get_actor_context()) and
    # GET /audit/events' read path (user.get("businessId"), JWT-only) don't
    # resolve businessId the same way — a custom X-Tenant-Id header would
    # make the written event invisible to the read. Every call here
    # deliberately uses the plain, unmodified owner_headers token, bypassing
    # req()'s per-call X-Tenant-Id injection instead of fighting it (see the
    # no-show/restore test above for the same issue with /customers).
    res = client.post("/api/reservations", headers=owner_headers, json={
        "guestName": "Audit Test Guest", "partySize": 2, "date": "2026-09-01", "time": "19:00",
    }).json()
    client.post(f"/api/reservations/{res['id']}/cancel", headers=owner_headers, json={"reason": "Double-booked"})
    client.post(f"/api/reservations/{res['id']}/restore", headers=owner_headers)

    history = client.get(f"/api/audit/history/reservation/{res['id']}", headers=owner_headers)
    assert history.status_code == 200
    events = client.get("/api/audit/events", headers=owner_headers,
                        params={"entity_type": "reservation", "entity_id": res["id"]})
    assert events.status_code == 200
    actions = [e["action"] for e in events.json()]
    assert "restored" in actions


def test_restoring_a_booking_does_not_re_occupy_its_old_table(client, owner_headers):
    plan = req(client, "POST", "/api/floor-plans", headers=owner_headers, json={
        "name": "Restore Test Floor", "locationId": "loc-1",
        "tables": [{
            "id": "TBL-RESTORE-1", "number": "99", "capacity": 4, "maxCovers": 4,
            "shape": "square", "x": 0, "y": 0, "width": 60, "height": 60, "rotation": 0,
            "section": None, "status": "available", "isActive": True,
        }],
    })
    assert plan.status_code == 200, plan.text

    res = _create_reservation(client, owner_headers, tableId="TBL-RESTORE-1")
    req(client, "POST", f"/api/reservations/{res['id']}/no-show", headers=owner_headers)

    # The table was freed by the no-show.
    plans = req(client, "GET", "/api/floor-plans", headers=owner_headers).json()
    tbl = next(t for p in plans for t in p["tables"] if t["id"] == "TBL-RESTORE-1")
    assert tbl["status"] == "available"

    req(client, "POST", f"/api/reservations/{res['id']}/restore", headers=owner_headers)

    # Restoring the booking doesn't blindly re-occupy the table — it may
    # have been given to someone else in the meantime.
    plans_after = req(client, "GET", "/api/floor-plans", headers=owner_headers).json()
    tbl_after = next(t for p in plans_after for t in p["tables"] if t["id"] == "TBL-RESTORE-1")
    assert tbl_after["status"] == "available"
