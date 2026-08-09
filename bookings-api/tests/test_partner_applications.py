"""Provisioning a Partner has only ever been possible with the deploy-time
platform admin key (routes_admin.py's require_platform_admin) — there was
no way for an outside integrator to even ask for access without already
holding the one credential meant to be the platform operator's alone.
This covers the other half: a public application, an admin review queue,
and confirms an approved application actually produces a working key —
not just a database row that claims to.
"""


def test_submitting_an_application_requires_no_authentication(client):
    r = client.post("/public/partner-applications", json={
        "company_name": "Acme Reservations", "contact_name": "Jordan",
        "contact_email": "jordan@acme.example", "use_case": "City-wide table discovery",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["id"]


def test_submitting_an_application_never_issues_a_key(client):
    r = client.post("/public/partner-applications", json={
        "company_name": "No Key Co", "contact_name": "Sam", "contact_email": "sam@nokey.example",
    })
    assert r.status_code == 200, r.text
    assert "api_key" not in r.json()
    assert "test_api_key" not in r.json()


def test_missing_required_fields_is_rejected(client):
    r = client.post("/public/partner-applications", json={
        "company_name": "", "contact_name": "Nobody", "contact_email": "",
    })
    assert r.status_code == 400


def test_listing_applications_requires_the_admin_key(client):
    r = client.get("/admin/partner-applications")
    assert r.status_code == 403


def test_full_flow_application_to_approval_to_a_working_key(client, admin_headers):
    submitted = client.post("/public/partner-applications", json={
        "company_name": "City Table Finder", "contact_name": "Priya",
        "contact_email": "priya@citytable.example", "use_case": "Metro-wide availability search",
    })
    assert submitted.status_code == 200, submitted.text
    app_id = submitted.json()["id"]

    listed = client.get("/admin/partner-applications", headers=admin_headers, params={"status": "pending"})
    assert listed.status_code == 200, listed.text
    assert any(a["id"] == app_id for a in listed.json())

    approved = client.post(f"/admin/partner-applications/{app_id}/approve", headers=admin_headers)
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["partnerId"]
    live_key = body["api_key"]
    assert live_key.startswith("nbk_live_")

    # The actual proof: the issued key must work as a real partner
    # credential against the real /v1 surface, not just exist in the
    # application record.
    venues = client.get("/v1/venues", headers={"Authorization": f"Bearer {live_key}"})
    assert venues.status_code == 200, venues.text

    # And the application itself now reflects the resolution.
    refetched = client.get("/admin/partner-applications", headers=admin_headers, params={"status": "approved"})
    resolved = next(a for a in refetched.json() if a["id"] == app_id)
    assert resolved["partner_id"] == body["partnerId"]


def test_approving_an_already_resolved_application_is_rejected(client, admin_headers):
    submitted = client.post("/public/partner-applications", json={
        "company_name": "Double Approve Co", "contact_name": "Lee", "contact_email": "lee@double.example",
    })
    app_id = submitted.json()["id"]
    first = client.post(f"/admin/partner-applications/{app_id}/approve", headers=admin_headers)
    assert first.status_code == 200, first.text

    second = client.post(f"/admin/partner-applications/{app_id}/approve", headers=admin_headers)
    assert second.status_code == 400


def test_rejecting_an_application_issues_no_partner(client, admin_headers):
    submitted = client.post("/public/partner-applications", json={
        "company_name": "Reject Me Co", "contact_name": "Casey", "contact_email": "casey@reject.example",
    })
    app_id = submitted.json()["id"]

    rejected = client.post(f"/admin/partner-applications/{app_id}/reject", headers=admin_headers,
                           params={"reason": "Use case out of scope"})
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"

    listed = client.get("/admin/partner-applications", headers=admin_headers, params={"status": "rejected"})
    row = next(a for a in listed.json() if a["id"] == app_id)
    assert row["rejection_reason"] == "Use case out of scope"
    assert row["partner_id"] is None


def test_rejecting_an_unknown_application_is_a_clean_404(client, admin_headers):
    r = client.post("/admin/partner-applications/APP-DOESNOTEXIST/reject", headers=admin_headers)
    assert r.status_code == 404


def test_application_submission_is_rate_limited_per_ip(client):
    for _ in range(5):
        r = client.post("/public/partner-applications", json={
            "company_name": "Rate Limit Co", "contact_name": "Test", "contact_email": "test@ratelimit.example",
        })
        assert r.status_code == 200, r.text

    over_limit = client.post("/public/partner-applications", json={
        "company_name": "Rate Limit Co", "contact_name": "Test", "contact_email": "test@ratelimit.example",
    })
    assert over_limit.status_code == 429
