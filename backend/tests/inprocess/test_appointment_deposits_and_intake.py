"""Beauty/services Phase 5: deposits, no-show fees, and client intake /
consultation notes on top of Phase 4's appointment booking.
"""
from conftest import req


def _get_owner_id(client, headers):
    return req(client, "GET", "/api/auth/me", headers=headers).json()["id"]


def _create_service(client, headers, **overrides):
    payload = {"name": "Deposit Test Service", "category": "Hair", "durationMinutes": 45, "price": 65.0}
    payload.update(overrides)
    return req(client, "POST", "/api/services", json=payload, headers=headers).json()


def _create_customer(client, headers, **overrides):
    payload = {"name": "Fee Test Client", "email": "feetest@example.com", "phone": "+61400900900"}
    payload.update(overrides)
    r = req(client, "POST", "/api/customers", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_a_deposit_can_be_required_at_booking_and_marked_paid(client, owner_headers):
    staff_id = _get_owner_id(client, owner_headers)
    svc = _create_service(client, owner_headers)
    appt = req(client, "POST", "/api/appointments", json={
        "customerName": "Deposit Client", "staffId": staff_id, "serviceId": svc["id"],
        "date": "2026-10-01", "time": "10:00", "depositRequired": 20.0,
    }, headers=owner_headers).json()
    assert appt["depositRequired"] == 20.0
    assert appt["depositPaid"] is False

    r = req(client, "PUT", f"/api/appointments/{appt['id']}", json={"depositPaid": True}, headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["depositPaid"] is True


def test_marking_no_show_records_the_fee_and_tallies_the_customer(client, owner_headers):
    staff_id = _get_owner_id(client, owner_headers)
    svc = _create_service(client, owner_headers, name="No-Show Fee Service")
    customer = _create_customer(client, owner_headers, email="noshowtally@example.com", phone="+61400900901")
    appt = req(client, "POST", "/api/appointments", json={
        "customerName": customer["name"], "customerId": customer["id"],
        "staffId": staff_id, "serviceId": svc["id"], "date": "2026-10-02", "time": "11:00",
    }, headers=owner_headers).json()

    r = req(client, "POST", f"/api/appointments/{appt['id']}/no-show", params={"fee": 25}, headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "no_show"
    assert body["noShowFee"] == 25.0

    updated = req(client, "GET", f"/api/customers/{customer['id']}/profile", headers=owner_headers)
    assert updated.status_code == 200
    assert updated.json().get("noShowCount", 0) == 1


def test_intake_note_history_accumulates_per_client_and_is_retrievable_by_phone(client, owner_headers):
    phone = "+61400900902"
    r1 = req(client, "POST", "/api/client-intake", json={
        "customerName": "Intake Client", "customerPhone": phone,
        "allergies": "PPD (hair dye)", "skinType": "Sensitive", "notes": "First visit — patch test done, clear.",
    }, headers=owner_headers)
    assert r1.status_code == 200, r1.text

    r2 = req(client, "POST", "/api/client-intake", json={
        "customerName": "Intake Client", "customerPhone": phone,
        "allergies": "PPD (hair dye)", "skinType": "Sensitive", "notes": "Colour touch-up, no reaction.",
    }, headers=owner_headers)
    assert r2.status_code == 200

    r3 = req(client, "GET", "/api/client-intake", params={"customerPhone": phone}, headers=owner_headers)
    assert r3.status_code == 200
    notes = r3.json()
    assert len(notes) == 2
    # Most recent first.
    assert notes[0]["notes"] == "Colour touch-up, no reaction."
    assert all(n["allergies"] == "PPD (hair dye)" for n in notes)


def test_listing_intake_notes_requires_a_customer_identifier(client, owner_headers):
    r = req(client, "GET", "/api/client-intake", headers=owner_headers)
    assert r.status_code == 400
