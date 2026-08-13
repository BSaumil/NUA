"""Beauty/services Phase 4: staff-as-resource appointment booking + a
service catalog with durations, kept separate from the restaurant
reservations system.
"""
from conftest import req


def _get_owner_id(client, headers):
    r = req(client, "GET", "/api/auth/me", headers=headers)
    return r.json()["id"]


def _create_service(client, headers, **overrides):
    payload = {"name": "Haircut", "category": "Hair", "durationMinutes": 45, "price": 65.0, "staffIds": []}
    payload.update(overrides)
    r = req(client, "POST", "/api/services", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_creating_a_service_and_listing_it(client, owner_headers):
    svc = _create_service(client, owner_headers, name="Colour", durationMinutes=120, price=180.0)
    assert svc["durationMinutes"] == 120
    r = req(client, "GET", "/api/services", headers=owner_headers)
    names = [s["name"] for s in r.json()]
    assert "Colour" in names


def test_booking_an_appointment_snapshots_service_price_and_duration(client, owner_headers):
    staff_id = _get_owner_id(client, owner_headers)
    svc = _create_service(client, owner_headers, name="Manicure", durationMinutes=30, price=40.0)
    r = req(client, "POST", "/api/appointments", json={
        "customerName": "Jane Doe", "customerPhone": "+61400000001",
        "staffId": staff_id, "serviceId": svc["id"], "date": "2026-09-01", "time": "10:00",
    }, headers=owner_headers)
    assert r.status_code == 200, r.text
    appt = r.json()
    assert appt["durationMinutes"] == 30
    assert appt["price"] == 40.0
    assert appt["staffName"]  # snapshotted from the real staff record, not blank
    assert appt["status"] == "confirmed"


def test_a_second_overlapping_appointment_for_the_same_staff_is_rejected(client, owner_headers):
    staff_id = _get_owner_id(client, owner_headers)
    svc = _create_service(client, owner_headers, name="Overlap Test Cut", durationMinutes=60, price=50.0)
    r1 = req(client, "POST", "/api/appointments", json={
        "customerName": "First Client", "staffId": staff_id, "serviceId": svc["id"],
        "date": "2026-09-02", "time": "11:00",
    }, headers=owner_headers)
    assert r1.status_code == 200

    # Overlaps 11:00-12:00 (starts mid-way through)
    r2 = req(client, "POST", "/api/appointments", json={
        "customerName": "Second Client", "staffId": staff_id, "serviceId": svc["id"],
        "date": "2026-09-02", "time": "11:30",
    }, headers=owner_headers)
    assert r2.status_code == 409

    # Right after the first one ends is fine.
    r3 = req(client, "POST", "/api/appointments", json={
        "customerName": "Third Client", "staffId": staff_id, "serviceId": svc["id"],
        "date": "2026-09-02", "time": "12:00",
    }, headers=owner_headers)
    assert r3.status_code == 200


def test_availability_excludes_slots_that_would_overlap_an_existing_booking(client, owner_headers):
    staff_id = _get_owner_id(client, owner_headers)
    svc = _create_service(client, owner_headers, name="Beard Trim", durationMinutes=30, price=25.0)
    req(client, "POST", "/api/appointments", json={
        "customerName": "Booked Client", "staffId": staff_id, "serviceId": svc["id"],
        "date": "2026-09-03", "time": "14:00",
    }, headers=owner_headers)

    r = req(client, "GET", "/api/appointments/availability",
            params={"staffId": staff_id, "serviceId": svc["id"], "date": "2026-09-03"}, headers=owner_headers)
    assert r.status_code == 200
    slots = r.json()["slots"]
    assert "14:00" not in slots       # the booked slot itself
    assert "13:45" not in slots       # a 30-min slot here would run into the 14:00 booking
    assert "09:00" in slots           # well clear of the booking


def test_cancelling_an_appointment_frees_the_slot_again(client, owner_headers):
    staff_id = _get_owner_id(client, owner_headers)
    svc = _create_service(client, owner_headers, name="Cancel Test Service", durationMinutes=30, price=30.0)
    appt = req(client, "POST", "/api/appointments", json={
        "customerName": "Cancels", "staffId": staff_id, "serviceId": svc["id"],
        "date": "2026-09-04", "time": "15:00",
    }, headers=owner_headers).json()

    r = req(client, "POST", f"/api/appointments/{appt['id']}/cancel", headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"

    # Same slot is bookable again now that it's cancelled.
    r2 = req(client, "POST", "/api/appointments", json={
        "customerName": "Rebooks", "staffId": staff_id, "serviceId": svc["id"],
        "date": "2026-09-04", "time": "15:00",
    }, headers=owner_headers)
    assert r2.status_code == 200


def test_completing_and_marking_no_show_transitions_status(client, owner_headers):
    staff_id = _get_owner_id(client, owner_headers)
    svc = _create_service(client, owner_headers, name="Status Test Service", durationMinutes=20, price=20.0)
    appt = req(client, "POST", "/api/appointments", json={
        "customerName": "Status Client", "staffId": staff_id, "serviceId": svc["id"],
        "date": "2026-09-05", "time": "16:00",
    }, headers=owner_headers).json()

    r = req(client, "POST", f"/api/appointments/{appt['id']}/complete", headers=owner_headers)
    assert r.json()["status"] == "completed"

    appt2 = req(client, "POST", "/api/appointments", json={
        "customerName": "No Show Client", "staffId": staff_id, "serviceId": svc["id"],
        "date": "2026-09-05", "time": "17:00",
    }, headers=owner_headers).json()
    r2 = req(client, "POST", f"/api/appointments/{appt2['id']}/no-show", headers=owner_headers)
    assert r2.json()["status"] == "no_show"
