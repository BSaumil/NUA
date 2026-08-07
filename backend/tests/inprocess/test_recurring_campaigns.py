"""Campaign targeting gained a segment builder earlier this round, but
every campaign was still a one-off manual send — there was no way to say
"email newly-inactive customers every week" without recreating the
campaign by hand each time. Recurring campaigns re-resolve their segment
fresh on every run (that's the point — who's "inactive" changes) instead
of sending a snapshot once.
"""
import asyncio

from conftest import req


def _seed_customer(name, email, *, tenant_headers, client):
    r = req(client, "POST", "/api/customers", headers=tenant_headers, json={
        "name": name, "email": email, "phone": "0400000000"})
    assert r.status_code == 200, r.text[:200]
    return r.json()["id"]


def test_a_recurring_campaign_starts_due_and_run_now_advances_its_schedule(client, owner_headers, monkeypatch):
    tenant = dict(owner_headers, **{"X-Tenant-Id": "recurring-campaign-test"})
    _seed_customer("Recurring Recipient", "recurringrecipient@nua.com", tenant_headers=tenant, client=client)

    sent_to = []

    async def fake_send_email(to, subject, body):
        sent_to.append(to)
        return {"channel": "email", "delivered": True, "to": to}

    import utils.notifications
    monkeypatch.setattr(utils.notifications, "send_email", fake_send_email)

    created = req(client, "POST", "/api/marketing/campaigns", headers=tenant, json={
        "name": "Weekly win-back", "subject": "We miss you", "body": "Hi {first_name}",
        "recurring": {"enabled": True, "intervalDays": 7}})
    assert created.status_code == 200, created.text[:200]
    campaign = created.json()
    assert campaign["status"] == "recurring"
    assert campaign["runCount"] == 0
    assert campaign["nextRunAt"] is not None

    # A recurring campaign never goes through the one-off Send button.
    blocked = req(client, "POST", f"/api/marketing/campaigns/{campaign['id']}/send", headers=tenant)
    assert blocked.status_code == 400

    run = req(client, "POST", f"/api/marketing/campaigns/{campaign['id']}/run-now", headers=tenant)
    assert run.status_code == 200, run.text[:200]
    assert "recurringrecipient@nua.com" in sent_to

    listed = req(client, "GET", "/api/marketing/campaigns", headers=tenant).json()
    updated = next(c for c in listed if c["id"] == campaign["id"])
    assert updated["runCount"] == 1
    assert updated["lastRunAt"] is not None
    assert updated["status"] == "recurring", "must stay recurring, never flip to a terminal 'sent' state"


def test_run_due_only_picks_up_campaigns_whose_schedule_has_actually_arrived(client, owner_headers, monkeypatch):
    tenant = dict(owner_headers, **{"X-Tenant-Id": "run-due-test"})
    _seed_customer("Due Test Recipient", "duetestrecipient@nua.com", tenant_headers=tenant, client=client)

    sent_subjects = []

    async def fake_send_email(to, subject, body):
        sent_subjects.append(subject)
        return {"channel": "email", "delivered": True, "to": to}

    import utils.notifications
    monkeypatch.setattr(utils.notifications, "send_email", fake_send_email)

    due_now = req(client, "POST", "/api/marketing/campaigns", headers=tenant, json={
        "name": "Due now", "subject": "SUBJECT-DUE-NOW", "body": "Hi",
        "recurring": {"enabled": True, "intervalDays": 7}}).json()

    not_due_yet = req(client, "POST", "/api/marketing/campaigns", headers=tenant, json={
        "name": "Not due yet", "subject": "SUBJECT-NOT-DUE", "body": "Hi",
        "recurring": {"enabled": True, "intervalDays": 7}}).json()
    # Push its schedule into the future so run-due must skip it.
    loop = asyncio.get_event_loop()
    from database import db
    from datetime import datetime, timezone, timedelta
    loop.run_until_complete(db.campaigns.update_one(
        {"id": not_due_yet["id"]},
        {"$set": {"nextRunAt": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()}}))

    result = req(client, "POST", "/api/marketing/campaigns/run-due", headers=tenant)
    assert result.status_code == 200, result.text[:200]
    ran_ids = {c["campaignId"] for c in result.json()["campaigns"]}
    assert due_now["id"] in ran_ids
    assert not_due_yet["id"] not in ran_ids
    assert "SUBJECT-DUE-NOW" in sent_subjects
    assert "SUBJECT-NOT-DUE" not in sent_subjects


def test_recurring_requires_owner_or_manager(client, owner_headers):
    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Campaign Cashier", "email": "campaign.cashier@nua.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={
        "email": "campaign.cashier@nua.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    cashier_headers = {"Authorization": f"Bearer {tok['token']}"}

    assert req(client, "POST", "/api/marketing/campaigns/run-due", headers=cashier_headers).status_code == 403
