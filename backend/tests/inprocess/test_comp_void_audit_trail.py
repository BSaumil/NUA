"""POST /comp-void used to write only to db.comp_voids, visible solely
through the now-retired standalone Audit Log page (a narrower duplicate of
the universal one, and — unlike it — unreachable from any nav link).
Recording a comp/void now also writes through the real audit trail, same
as every other sensitive action, so it shows up on /audit alongside
everything else instead of being the one thing that page couldn't see.
"""
from conftest import req


def test_recording_a_comp_void_appears_in_the_universal_audit_log(client, owner_headers):
    tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})

    created = req(client, "POST", "/api/comp-void", headers=tenant, json={
        "type": "void", "reason": "Wrong order rung up", "amount": 12.5, "printVoid": True})
    assert created.status_code == 200, created.text[:200]
    cv_id = created.json()["id"]

    events = req(client, "GET", "/api/audit/events", headers=tenant,
                 params={"entity_type": "comp_void", "entity_id": cv_id}).json()
    assert any(e["action"] == "created" and e["entityId"] == cv_id for e in events)
