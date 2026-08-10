"""Every autonomous or approval-gated decision this app makes already lands
somewhere — db.approvals, db.rule_executions, db.ash_trust_events — but
never assembled into one thing an operator could hand to an auditor or a
franchisor. services/compliance_export.py builds that: one chronological
timeline across all three sources, reading only what already exists.
"""
import asyncio
import uuid
from datetime import datetime, timezone

from conftest import req
from database import db
from services import compliance_export


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_timeline_combines_all_three_sources_chronologically():
    now = datetime.now(timezone.utc).isoformat()
    approval_id = str(uuid.uuid4())
    _run(db.approvals.insert_one({
        "id": approval_id, "actionType": "issue_voucher", "params": {}, "requestedBy": "ash-agent",
        "source": "ash_agent", "sourceRef": None, "context": {}, "status": "approved",
        "createdAt": now, "resolvedAt": now, "resolvedBy": "owner@nua.com",
        "resolution": None, "outcome": {"voucherId": "V1"},
    }))
    exec_id = str(uuid.uuid4())
    _run(db.rule_executions.insert_one({
        "id": exec_id, "eventId": str(uuid.uuid4()), "eventType": "pos.sale.completed",
        "payload": {}, "ts": now,
        "firings": [{"ruleId": "r1", "name": "Compliance Test Rule", "matched": True,
                     "outcomes": [{"type": "dock_notify", "result": {}}]}],
    }))
    trust_id = str(uuid.uuid4())
    _run(db.ash_trust_events.insert_one({
        "id": trust_id, "toolName": "issue_voucher", "kind": "promoted",
        "reason": "6/6 approved", "statsSnapshot": {}, "actor": "owner@nua.com", "at": now,
    }))

    timeline = _run(compliance_export.build_timeline(business_id=None, start_date=None, end_date=None))
    refs = {row["reference"] for row in timeline}
    assert {approval_id, exec_id, trust_id} <= refs

    ats = [row["at"] for row in timeline]
    assert ats == sorted(ats), "the combined timeline must be in chronological order"

    approval_row = next(r for r in timeline if r["reference"] == approval_id)
    assert approval_row["kind"] == "approval"
    assert "approved by owner@nua.com" in approval_row["summary"]

    rule_row = next(r for r in timeline if r["reference"] == exec_id)
    assert rule_row["kind"] == "rule_execution"
    assert "Compliance Test Rule" in rule_row["summary"]
    assert "dock_notify" in rule_row["summary"]

    trust_row = next(r for r in timeline if r["reference"] == trust_id)
    assert trust_row["kind"] == "trust_change"
    assert trust_row["status"] == "promoted"


def test_unmatched_rule_firings_are_not_included():
    """A rule that was evaluated but didn't match is not a decision anyone
    made — only actual firings belong in a compliance trail."""
    now = datetime.now(timezone.utc).isoformat()
    exec_id = str(uuid.uuid4())
    _run(db.rule_executions.insert_one({
        "id": exec_id, "eventId": str(uuid.uuid4()), "eventType": "pos.sale.completed",
        "payload": {}, "ts": now,
        "firings": [{"ruleId": "r2", "name": "Never Fires", "matched": False, "condition": {}}],
    }))
    timeline = _run(compliance_export.build_timeline(business_id=None, start_date=None, end_date=None))
    assert all(row["reference"] != exec_id for row in timeline)


def test_date_range_excludes_events_outside_the_window():
    old_id = str(uuid.uuid4())
    _run(db.ash_trust_events.insert_one({
        "id": old_id, "toolName": "old_tool", "kind": "demoted",
        "reason": "old event", "statsSnapshot": {}, "actor": "owner@nua.com",
        "at": "2020-01-01T00:00:00+00:00",
    }))
    timeline = _run(compliance_export.build_timeline(
        business_id=None, start_date="2025-01-01", end_date="2030-01-01"))
    assert all(row["reference"] != old_id for row in timeline)


def test_report_counts_events_by_kind():
    now = datetime.now(timezone.utc).isoformat()
    trust_id = str(uuid.uuid4())
    _run(db.ash_trust_events.insert_one({
        "id": trust_id, "toolName": "count_test_tool", "kind": "promoted",
        "reason": "test", "statsSnapshot": {}, "actor": "owner@nua.com", "at": now,
    }))
    report = _run(compliance_export.build_report(business_id=None))
    assert report["totalEvents"] == len(report["timeline"])
    assert report["counts"]["trust_change"] >= 1
    assert sum(report["counts"].values()) == report["totalEvents"]


def test_compliance_report_endpoint_is_owner_only(client, owner_headers):
    ok = req(client, "GET", "/api/audit/compliance-report", headers=owner_headers)
    assert ok.status_code == 200, ok.text[:200]
    assert "timeline" in ok.json()

    email = f"compliance-cashier-{uuid.uuid4()}@nua.com"
    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "Compliance Cashier", "email": email, "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={"email": email, "password": "CashierPass1!"}).json()
    client.cookies.clear()
    denied = req(client, "GET", "/api/audit/compliance-report", headers={"Authorization": f"Bearer {tok['token']}"})
    assert denied.status_code == 403


def test_compliance_csv_export_returns_real_csv_with_a_header_row(client, owner_headers):
    r = req(client, "GET", "/api/audit/compliance-export.csv", headers=owner_headers)
    assert r.status_code == 200, r.text[:200]
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    first_line = r.text.splitlines()[0]
    assert first_line == "At,Kind,Source,Summary,Actor,Decided By,Status,Reference"
