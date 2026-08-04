"""EFTPOS: a real driver abstraction existed (Linkly/Tyro/Smartpay/Windcave)
but every one of them called blocking sockets directly inside an async
method — a real terminal timeout would have frozen the entire backend for
every till in the venue, not just the one taking payment — and there was no
way to exercise a purchase, decline, refund, cancel or settlement without
either real hardware or a live vendor account.

These tests exercise the new SimulatorProvider, which is configured through
the exact same EFTPOSConfig/`provider` field a real terminal would use, and
pin the route-level authorization that was previously missing entirely (any
logged-in cashier could read another provider's API secret or delete a
terminal outright).
"""
from conftest import OWNER, req


def _make_terminal(client, headers, **overrides):
    body = {
        "provider": "simulator", "terminalId": "SIM-1", "merchantId": "M-1",
        "name": "Test Simulator", "location": "Counter 1",
        "connectionType": "cloud", "timeout": 30, "autoSettlement": True,
        **overrides,
    }
    r = req(client, "POST", "/api/eftpos/terminals", headers=headers, json=body)
    assert r.status_code == 200, r.text[:200]
    return r.json()["id"]


def test_a_normal_purchase_is_approved(client, owner_headers):
    tid = _make_terminal(client, owner_headers)
    r = req(client, "POST", "/api/eftpos/transaction", headers=owner_headers, json={
        "terminalId": tid, "transactionType": "purchase", "amount": 42.50,
        "reference": "REF-OK", "posTransactionId": "TXN-1"})
    assert r.status_code == 200
    body = r.json()
    assert body["approved"] is True
    assert body["responseCode"] == "00"
    assert body["rrn"]


def test_the_test_amount_conventions_produce_the_documented_declines(client, owner_headers):
    tid = _make_terminal(client, owner_headers, terminalId="SIM-DECLINE")
    cases = [(1.00, "51"), (2.00, "54"), (4.00, "05")]
    for amount, expected_code in cases:
        r = req(client, "POST", "/api/eftpos/transaction", headers=owner_headers, json={
            "terminalId": tid, "transactionType": "purchase", "amount": amount,
            "reference": f"REF-{expected_code}", "posTransactionId": "TXN-decline"})
        body = r.json()
        assert body["approved"] is False, f"${amount} should decline: {body}"
        assert body["responseCode"] == expected_code


def test_the_timeout_amount_simulates_no_response(client, owner_headers):
    tid = _make_terminal(client, owner_headers, terminalId="SIM-TIMEOUT")
    r = req(client, "POST", "/api/eftpos/transaction", headers=owner_headers, json={
        "terminalId": tid, "transactionType": "purchase", "amount": 3.00,
        "reference": "REF-TIMEOUT", "posTransactionId": "TXN-timeout"})
    body = r.json()
    assert body["approved"] is False
    assert body["responseCode"] == "68"


def test_a_refund_reverses_its_own_purchase(client, owner_headers):
    tid = _make_terminal(client, owner_headers, terminalId="SIM-REFUND")
    purchase = req(client, "POST", "/api/eftpos/transaction", headers=owner_headers, json={
        "terminalId": tid, "transactionType": "purchase", "amount": 25.00,
        "reference": "REF-TO-REFUND", "posTransactionId": "TXN-2"}).json()
    assert purchase["approved"] is True

    refund = req(client, "POST", "/api/eftpos/transaction", headers=owner_headers, json={
        "terminalId": tid, "transactionType": "refund", "amount": 25.00,
        "reference": "REF-TO-REFUND", "posTransactionId": "TXN-2-refund"}).json()
    assert refund["approved"] is True, refund


def test_a_refund_against_an_unknown_reference_is_refused(client, owner_headers):
    tid = _make_terminal(client, owner_headers, terminalId="SIM-REFUND-BAD")
    r = req(client, "POST", "/api/eftpos/transaction", headers=owner_headers, json={
        "terminalId": tid, "transactionType": "refund", "amount": 10.00,
        "reference": "NEVER-CHARGED", "posTransactionId": "TXN-bad-refund"})
    body = r.json()
    assert body["approved"] is False
    assert "no matching" in body["responseText"].lower()


def test_a_refund_larger_than_the_original_is_refused(client, owner_headers):
    tid = _make_terminal(client, owner_headers, terminalId="SIM-REFUND-OVER")
    req(client, "POST", "/api/eftpos/transaction", headers=owner_headers, json={
        "terminalId": tid, "transactionType": "purchase", "amount": 10.00,
        "reference": "REF-SMALL", "posTransactionId": "TXN-3"})
    r = req(client, "POST", "/api/eftpos/transaction", headers=owner_headers, json={
        "terminalId": tid, "transactionType": "refund", "amount": 50.00,
        "reference": "REF-SMALL", "posTransactionId": "TXN-3-refund"})
    body = r.json()
    assert body["approved"] is False
    assert "exceeds" in body["responseText"].lower()


def test_settlement_totals_only_the_approved_purchases(client, owner_headers):
    tid = _make_terminal(client, owner_headers, terminalId="SIM-SETTLE")
    for amount in (10.00, 20.00, 1.00):   # last one declines (insufficient funds)
        req(client, "POST", "/api/eftpos/transaction", headers=owner_headers, json={
            "terminalId": tid, "transactionType": "purchase", "amount": amount,
            "reference": f"REF-{amount}", "posTransactionId": f"TXN-settle-{amount}"})

    r = req(client, "POST", f"/api/eftpos/terminals/{tid}/settlement", headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_a_purchase_is_recorded_in_transaction_history(client, owner_headers):
    tid = _make_terminal(client, owner_headers, terminalId="SIM-HISTORY")
    req(client, "POST", "/api/eftpos/transaction", headers=owner_headers, json={
        "terminalId": tid, "transactionType": "purchase", "amount": 15.00,
        "reference": "REF-HISTORY", "posTransactionId": "TXN-hist"})
    r = req(client, "GET", "/api/eftpos/transactions", headers=owner_headers,
            params={"terminal_id": tid})
    assert r.status_code == 200
    refs = [t["reference"] for t in r.json()]
    assert "REF-HISTORY" in refs


# ── Authorization: terminal config carries API secrets ─────────────────────

def test_creating_a_terminal_requires_owner_or_manager(client, owner_headers):
    req(client, "POST", "/api/auth/staff/add", headers=owner_headers, json={
        "name": "EFTPOS Cashier", "email": "eftpos.cashier@nuva.com",
        "password": "CashierPass1!", "role": "cashier"})
    tok = req(client, "POST", "/api/auth/login",
              json={"email": "eftpos.cashier@nuva.com", "password": "CashierPass1!"}).json()
    client.cookies.clear()
    ch = {"Authorization": f"Bearer {tok['token']}"}

    r = req(client, "POST", "/api/eftpos/terminals", headers=ch, json={
        "provider": "simulator", "terminalId": "SIM-X", "merchantId": "M-X",
        "name": "X", "location": "X", "connectionType": "cloud"})
    assert r.status_code == 403

    tid = _make_terminal(client, owner_headers, terminalId="SIM-CASHIER-CHECK")
    assert req(client, "DELETE", f"/api/eftpos/terminals/{tid}", headers=ch).status_code == 403
    assert req(client, "GET", "/api/eftpos/transactions", headers=ch).status_code == 403

    # But a cashier can still read the terminal list and take a payment —
    # that's the normal checkout path.
    assert req(client, "GET", "/api/eftpos/terminals", headers=ch).status_code == 200
    r = req(client, "POST", "/api/eftpos/transaction", headers=ch, json={
        "terminalId": tid, "transactionType": "purchase", "amount": 5.00,
        "reference": "REF-CASHIER", "posTransactionId": "TXN-cashier"})
    assert r.status_code == 200


def test_eftpos_endpoints_refuse_an_anonymous_caller(anon):
    assert req(anon, "GET", "/api/eftpos/terminals").status_code == 401
    assert req(anon, "POST", "/api/eftpos/transaction", json={}).status_code == 401
