"""nua_trust.py shipped the "climb" half of graduated trust (streak ->
eligible -> promote) but explicitly documented that it had no way to walk
back a bad auto-execution — an owner who promoted a tool was relying on
noticing and reverting it manually. This closes that gap: every auto-tier
execution already writes an audit_service entry, so the review feed just
replays that trail, and flagging one demotes the tool back to
approval-gated immediately (not just a dent in the streak) and, where the
tool supports it, undoes the change.
"""
from conftest import req


def test_an_auto_executed_action_shows_up_in_the_review_feed(client, owner_headers):
    # req() stamps a fresh synthetic X-Tenant-Id per call to dodge the rate
    # limiter; Customer (unlike Product) has no businessId field on its
    # model, so _stamp_new's setdefault picks that header up as the new
    # customer's businessId — but GET /customers filters by the *JWT's*
    # businessId ("default" for owner_headers), not by header. Pin the
    # create-side header to "default" so the two agree.
    headers = {**owner_headers, "X-Tenant-Id": "default"}
    created = req(client, "POST", "/api/customers", headers=headers, json={
        "name": "Trust Feed Customer", "email": "trust.feed@example.com", "phone": "0400000001"})
    assert created.status_code == 200, created.text[:200]
    customer_id = created.json()["id"]

    # add_customer_note defaults to permission=auto, so this executes
    # immediately rather than landing in the approval queue.
    r = req(client, "POST", "/api/nua/tools/add_customer_note/execute", headers=headers,
            json={"args": {"customerId": customer_id, "note": "VIP: prefers window table"}})
    assert r.status_code == 200, r.text[:200]
    outcome = r.json()
    assert outcome["status"] == "executed"
    # execute_tool() reports status="executed" even when the tool itself
    # raised (outcome={"error": ...}) — checking status alone would have
    # missed notes.$push failing against notes' actual string schema, so
    # assert the outcome is actually clean, not just that a response came back.
    assert "error" not in (outcome.get("outcome") or {}), outcome

    note_written = req(client, "GET", "/api/customers", headers=headers).json()
    customer = next(c for c in note_written if c["id"] == customer_id)
    assert "VIP: prefers window table" in (customer.get("notes") or "")

    feed = req(client, "GET", "/api/nua/tools/auto-executions", headers=headers)
    assert feed.status_code == 200, feed.text[:200]
    rows = feed.json()
    match = next((e for e in rows if e["toolName"] == "add_customer_note"
                  and (e.get("args") or {}).get("customerId") == customer_id), None)
    assert match is not None, "the execution that just ran must appear in the shadow-audit feed"
    assert match["flagged"] is False


def test_flagging_an_execution_instantly_demotes_the_tool_to_approval(client, owner_headers):
    created = req(client, "POST", "/api/customers", headers=owner_headers, json={
        "name": "Demotion Test Customer", "email": "demotion.test@example.com", "phone": "0400000002"})
    customer_id = created.json()["id"]

    exec_r = req(client, "POST", "/api/nua/tools/add_customer_note/execute", headers=owner_headers,
                 json={"args": {"customerId": customer_id, "note": "wrong note, flag me"}})
    assert exec_r.status_code == 200, exec_r.text[:200]

    feed = req(client, "GET", "/api/nua/tools/auto-executions", headers=owner_headers).json()
    match = next(e for e in feed if e["toolName"] == "add_customer_note"
                 and (e.get("args") or {}).get("customerId") == customer_id)

    flag_r = req(client, "POST", f"/api/nua/tools/executions/{match['auditId']}/flag",
                 headers=owner_headers, json={"reason": "note was wrong"})
    assert flag_r.status_code == 200, flag_r.text[:200]
    body = flag_r.json()
    assert body["permission"] == "approval"
    assert body["demoted"] is True

    # The tool's owner-facing permission must actually reflect the demotion,
    # not just the flag endpoint's own response.
    catalog = req(client, "GET", "/api/nua/tools", headers=owner_headers).json()
    tool = next(t for t in catalog if t["name"] == "add_customer_note")
    assert tool["effectivePermission"] == "approval"

    # A second execute call must now queue for approval instead of running.
    second = req(client, "POST", "/api/nua/tools/add_customer_note/execute", headers=owner_headers,
                 json={"args": {"customerId": customer_id, "note": "should be gated now"}})
    assert second.status_code == 200, second.text[:200]
    assert second.json()["status"] == "pending_approval"

    # And the flagged row itself must be marked so the feed doesn't offer
    # the same flag/undo buttons on it twice.
    feed_after = req(client, "GET", "/api/nua/tools/auto-executions", headers=owner_headers).json()
    flagged_row = next(e for e in feed_after if e["auditId"] == match["auditId"])
    assert flagged_row["flagged"] is True


def test_flag_with_undo_rolls_back_a_tool_that_supports_rollback(client, owner_headers):
    product = req(client, "POST", "/api/products", headers=owner_headers, json={
        "name": "Trust Rollback Widget", "price": 20, "cost": 8, "category": "Test",
        "stock": 5, "sku": "TRUST-ROLLBACK-1"})
    assert product.status_code == 200, product.text[:200]
    product_id = product.json()["id"]

    # adjust_menu_price defaults to permission=approval — force it to auto
    # so this test can exercise the auto-execution + flag/undo path directly.
    perm = req(client, "PUT", "/api/nua/tools/adjust_menu_price/permission", headers=owner_headers,
               json={"permission": "auto"})
    assert perm.status_code == 200, perm.text[:200]

    exec_r = req(client, "POST", "/api/nua/tools/adjust_menu_price/execute", headers=owner_headers,
                 json={"args": {"productId": product_id, "newPrice": 999, "reason": "test"}})
    assert exec_r.status_code == 200, exec_r.text[:200]
    assert exec_r.json()["status"] == "executed"

    def _price():
        rows = req(client, "GET", "/api/products", headers=owner_headers).json()
        return next(p["price"] for p in rows if p["id"] == product_id)

    assert _price() == 999

    feed = req(client, "GET", "/api/nua/tools/auto-executions", headers=owner_headers).json()
    match = next(e for e in feed if e["toolName"] == "adjust_menu_price"
                 and (e.get("args") or {}).get("productId") == product_id)
    assert match["rollbackAvailable"] is True

    flag_r = req(client, "POST", f"/api/nua/tools/executions/{match['auditId']}/flag",
                 headers=owner_headers, json={"reason": "wrong price", "undo": True})
    assert flag_r.status_code == 200, flag_r.text[:200]
    body = flag_r.json()
    assert body["permission"] == "approval"
    assert body["undo"]["undone"] is True

    assert _price() == 20, "flagging with undo=true must restore the pre-execution price"
