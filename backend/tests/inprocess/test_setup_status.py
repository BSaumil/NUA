"""GET /api/business/{id}/setup-status — the Foundation Day runbook steps
(backfill, demo-data purge, menu, staff) surfaced as a live checklist."""
from conftest import req


def test_setup_status_reflects_real_state(client, owner_headers):
    from database import db
    import asyncio

    r = req(client, "GET", "/api/business/default/setup-status", headers=owner_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    for key in ("backfillComplete", "demoDataPurged", "hasMenu", "hasStaff", "ready"):
        assert key in body

    # Purging demo data should flip demoDataPurged to true (deterministically,
    # regardless of what other tests have already inserted).
    req(client, "POST", "/api/business/purge-demo-data", json={"confirm": "PURGE"}, headers=owner_headers)
    r2 = req(client, "GET", "/api/business/default/setup-status", headers=owner_headers)
    assert r2.json()["demoDataPurged"] is True
    assert r2.json()["demoRowsRemaining"] == 0
