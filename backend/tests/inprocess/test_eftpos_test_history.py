"""Test Connection just flipped a terminal's `status` with no record of
when it was tested or how many times it had failed — a terminal that's
flaky (working, then erroring, then working again) looked identical to
one that's never had a problem. Added a persisted test-history log
alongside the existing status flip.
"""
from conftest import req


def _make_terminal(client, headers, **overrides):
    body = {
        "provider": "simulator", "terminalId": "SIM-HIST-1", "merchantId": "M-HIST-1",
        "name": "History Test Simulator", "location": "Counter 1",
        "connectionType": "cloud", "timeout": 30, "autoSettlement": True,
        **overrides,
    }
    r = req(client, "POST", "/api/eftpos/terminals", headers=headers, json=body)
    assert r.status_code == 200, r.text[:200]
    return r.json()["id"]


def test_each_connection_test_is_logged_to_history(client, owner_headers):
    tid = _make_terminal(client, owner_headers)

    first = req(client, "POST", f"/api/eftpos/terminals/{tid}/test", headers=owner_headers)
    assert first.status_code == 200, first.text[:200]
    second = req(client, "POST", f"/api/eftpos/terminals/{tid}/test", headers=owner_headers)
    assert second.status_code == 200, second.text[:200]

    history = req(client, "GET", f"/api/eftpos/terminals/{tid}/test-history", headers=owner_headers)
    assert history.status_code == 200, history.text[:200]
    rows = history.json()
    assert len(rows) >= 2
    assert all(r["terminalId"] == tid for r in rows)
    assert all("success" in r and "testedAt" in r and "message" in r for r in rows)


def test_test_history_requires_owner_or_manager(client, owner_headers):
    tid = _make_terminal(client, owner_headers, terminalId="SIM-HIST-2", merchantId="M-HIST-2")
    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "EFTPOS Cashier", "email": "eftpos.cashier@nua.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login", json={
        "email": "eftpos.cashier@nua.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    cashier_headers = {"Authorization": f"Bearer {tok['token']}"}

    r = req(client, "GET", f"/api/eftpos/terminals/{tid}/test-history", headers=cashier_headers)
    assert r.status_code == 403
