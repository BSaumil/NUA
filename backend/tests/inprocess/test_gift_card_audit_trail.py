"""Gift cards mint real spendable value with no purchase transaction
backing them (unlike a POS sale), which made them invisible to the
universal audit log entirely — owner/manager gating alone doesn't answer
"who minted how much, and when" after the fact.
"""
from conftest import req


def test_scheduling_a_gift_card_is_recorded_in_the_audit_log(client, owner_headers):
    # Pinned to X-Tenant-Id "default" on every call: the audit-events GET
    # route resolves businessId from the decoded JWT (="default" for the
    # OWNER fixture), while stamped writes resolve it from the actor-context
    # middleware, which prefers the X-Tenant-Id header when present. The
    # shared req() helper stamps a fresh per-call tenant to dodge rate
    # limiting across the whole suite, which would desync the two here.
    tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})

    created = req(client, "POST", "/api/gift-cards/schedule", headers=tenant, json={
        "amount": 75, "deliverAt": "2026-12-25", "recipientEmail": "giftrecipient@nua.com"})
    assert created.status_code == 200, created.text[:200]
    voucher_id = created.json()["id"]

    events = req(client, "GET", "/api/audit/events", headers=tenant,
                 params={"entity_type": "gift_card", "entity_id": voucher_id}).json()
    assert any(e["action"] == "created" for e in events)
    assert any("75" in (e.get("memo") or "") for e in events)


def test_reloading_a_gift_card_is_recorded_in_the_audit_log(client, owner_headers):
    tenant = dict(owner_headers, **{"X-Tenant-Id": "default"})

    created = req(client, "POST", "/api/gift-cards/schedule", headers=tenant, json={
        "amount": 20, "deliverAt": "2026-12-25", "recipientEmail": "reloadrecipient@nua.com"})
    voucher_id = created.json()["id"]

    reloaded = req(client, "POST", f"/api/gift-cards/{voucher_id}/reload", headers=tenant, json={"amount": 15})
    assert reloaded.status_code == 200, reloaded.text[:200]

    events = req(client, "GET", "/api/audit/events", headers=tenant,
                 params={"entity_type": "gift_card", "entity_id": voucher_id}).json()
    reload_event = next(e for e in events if e["action"] == "updated")
    assert reload_event["before"]["residualValue"] == 20
    assert reload_event["after"]["residualValue"] == 35
