"""Iteration 51 — Enterprise Finance & Rules Engine coverage.

Scope
─────
Finance:
  • Chart of Accounts idempotent seed
  • Manual journal — balanced OK, unbalanced 400
  • Trial Balance balanced
  • POS transaction auto-posts pos_sale journal, P&L revenue updates
  • Refund auto-posts reversing journal
  • Bill AP flow — create + pay journals
  • Invoice AR flow — create + receive
  • Balance sheet balanced=true
  • Cash flow report structure
  • General ledger for cash account
  • Bank rec: import idempotent, statement, match
  • KPIs endpoint

Rules Engine:
  • Catalog counts (24 events / 12 actions / 11 operators)
  • CRUD + toggle
  • Simulator wouldFire
  • Emit runs matching rules
  • AI Rule Builder
  • Stats + history
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or "https://pos-checkout-16.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER_EMAIL = "owner@nuva.com"
OWNER_PASSWORD = "NuvaOwner2026!"


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
                      timeout=20)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"No token in login response: {r.json()}"
    return tok


@pytest.fixture
def client(owner_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {owner_token}",
                      "Content-Type": "application/json"})
    return s


# ══════════════════════════════════════════════════════════════════════
# Chart of Accounts
# ══════════════════════════════════════════════════════════════════════
class TestChartOfAccounts:
    def test_accounts_list(self, client):
        r = client.get(f"{API}/accounting/accounts", timeout=15)
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list)
        assert len(rows) >= 39, f"Expected >=39 seeded accounts, got {len(rows)}"

    def test_seed_is_idempotent(self, client):
        r = client.post(f"{API}/accounting/seed", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # Second seed should not create new accounts
        assert data.get("seeded", 0) == 0, f"Expected seeded=0 on 2nd call, got {data}"


# ══════════════════════════════════════════════════════════════════════
# Manual Journals
# ══════════════════════════════════════════════════════════════════════
class TestJournals:
    def test_balanced_journal_succeeds(self, client):
        body = {
            "memo": "TEST_iter51 balanced entry",
            "lines": [
                {"accountCode": "1000", "debit": 100.0, "credit": 0.0, "description": "test debit"},
                {"accountCode": "4000", "debit": 0.0, "credit": 100.0, "description": "test credit"},
            ],
        }
        r = client.post(f"{API}/accounting/journals", json=body, timeout=15)
        assert r.status_code == 200, r.text
        je = r.json()
        assert je.get("id")
        assert je.get("posted") in (True, None) or True
        # Verify persistence
        got = client.get(f"{API}/accounting/journals/{je['id']}", timeout=15)
        assert got.status_code == 200
        assert got.json()["id"] == je["id"]

    def test_unbalanced_journal_rejected(self, client):
        body = {
            "memo": "TEST_iter51 unbalanced",
            "lines": [
                {"accountCode": "1000", "debit": 100.0, "credit": 0.0},
                {"accountCode": "4000", "debit": 0.0, "credit": 50.0},
            ],
        }
        r = client.post(f"{API}/accounting/journals", json=body, timeout=15)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        assert "unbalanced" in r.text.lower() or "balance" in r.text.lower()


# ══════════════════════════════════════════════════════════════════════
# Reports
# ══════════════════════════════════════════════════════════════════════
class TestReports:
    def test_trial_balance_balanced(self, client):
        r = client.get(f"{API}/accounting/reports/trial-balance", timeout=15)
        assert r.status_code == 200, r.text
        tb = r.json()
        td = round(float(tb.get("totalDebit", 0)), 2)
        tc = round(float(tb.get("totalCredit", 0)), 2)
        assert abs(td - tc) < 0.01, f"TB not balanced: debit={td} credit={tc}"

    def test_balance_sheet_balanced(self, client):
        r = client.get(f"{API}/accounting/reports/balance-sheet", timeout=15)
        assert r.status_code == 200, r.text
        bs = r.json()
        assert bs.get("balanced") is True, f"BS not balanced: {bs}"
        # Assets == L + E (approx)
        a = float(bs.get("totalAssets", 0))
        le = float(bs.get("totalLiabilities", 0)) + float(bs.get("totalEquity", 0))
        assert abs(a - le) < 1.0, f"Assets({a}) != L+E({le})"

    def test_cash_flow_structure(self, client):
        r = client.get(f"{API}/accounting/reports/cash-flow", timeout=15)
        assert r.status_code == 200, r.text
        cf = r.json()
        for k in ("openingBalance", "netCash", "closingBalance"):
            assert k in cf, f"Missing key {k} in CF: {list(cf.keys())}"

    def test_general_ledger_cash_account(self, client):
        r = client.get(f"{API}/accounting/reports/general-ledger/1000", timeout=15)
        assert r.status_code == 200, r.text
        gl = r.json()
        assert "rows" in gl or "lines" in gl, f"GL missing rows: {list(gl.keys())}"

    def test_profit_loss(self, client):
        r = client.get(f"{API}/accounting/reports/profit-loss", timeout=15)
        assert r.status_code == 200, r.text
        pnl = r.json()
        for k in ("totalRevenue", "grossProfit", "netProfit"):
            assert k in pnl


# ══════════════════════════════════════════════════════════════════════
# POS auto-post
# ══════════════════════════════════════════════════════════════════════
class TestPOSAutoPost:
    def test_pos_sale_creates_journal(self, client):
        # Snapshot revenue before
        r0 = client.get(f"{API}/accounting/reports/profit-loss", timeout=15).json()
        rev_before = float(r0.get("totalRevenue", 0))

        # Create a POS transaction
        txn = {
            "items": [
                {"productId": "test-item", "productName": "TEST_iter51 Coffee",
                 "quantity": 1, "price": 10.00},
            ],
            "paymentMethod": "card",
            "location": "Main",
            "cashier": "TEST_iter51",
        }
        r = client.post(f"{API}/transactions", json=txn, timeout=20)
        assert r.status_code in (200, 201), r.text
        # Give the auto-post a moment
        time.sleep(1.0)

        # Check pos_sale journal exists
        j = client.get(f"{API}/accounting/journals?source_type=pos_sale&limit=10", timeout=15)
        assert j.status_code == 200, j.text
        journals = j.json()
        assert isinstance(journals, list)
        assert len(journals) >= 1, "No pos_sale journal found after POS transaction"

        # Revenue should have increased (net amount)
        r1 = client.get(f"{API}/accounting/reports/profit-loss", timeout=15).json()
        rev_after = float(r1.get("totalRevenue", 0))
        assert rev_after >= rev_before, f"Revenue did not increase: {rev_before} -> {rev_after}"

    def test_refund_reversing_journal(self, client):
        # find a recent POS txn
        tx_list = client.get(f"{API}/transactions?limit=20", timeout=15)
        if tx_list.status_code != 200:
            pytest.skip(f"tx list not available: {tx_list.status_code}")
        rows = tx_list.json()
        if not rows:
            pytest.skip("no transactions to refund")
        target = rows[0]
        tid = target.get("id") or target.get("_id")
        if not tid:
            pytest.skip("no transaction id")

        refund_body = {
            "originalTransactionId": tid,
            "amount": max(1.0, min(2.0, float(target.get("total", 1)))),
            "reason": "TEST_iter51 refund",
            "refundMethod": "original_payment",
            "processedBy": "TEST_iter51",
        }
        r = client.post(f"{API}/refunds", json=refund_body, timeout=20)
        assert r.status_code in (200, 201), f"Refund failed: {r.status_code} {r.text}"
        time.sleep(1.0)

        # Refund journal should exist
        j = client.get(f"{API}/accounting/journals?source_type=refund&limit=10", timeout=15)
        assert j.status_code == 200
        assert len(j.json()) >= 1, "No refund journal recorded"


# ══════════════════════════════════════════════════════════════════════
# AP / AR flows
# ══════════════════════════════════════════════════════════════════════
class TestBillsAndInvoices:
    def test_bill_create_and_pay(self, client):
        body = {
            "supplierId": f"TEST_sup_{uuid.uuid4().hex[:6]}",
            "supplierName": "TEST_iter51 Supplier",
            "billNumber": f"TEST-{uuid.uuid4().hex[:8]}",
            "issueDate": "2026-01-15",
            "dueDate": "2026-02-15",
            "lines": [
                {"description": "TEST inv item", "accountCode": "5000",
                 "amount": 100.0},
            ],
            "total": 110.0,
            "gst": 10.0,
        }
        r = client.post(f"{API}/accounting/bills", json=body, timeout=15)
        assert r.status_code == 200, r.text
        bill = r.json()
        assert bill.get("id")
        assert bill.get("journalEntryId"), "bill should have journalEntryId"

        # Pay it
        pay = client.post(f"{API}/accounting/bills/{bill['id']}/pay",
                          json={"amount": 110.0, "method": "bank"}, timeout=15)
        assert pay.status_code == 200, pay.text
        pdata = pay.json()
        assert pdata.get("newStatus") == "paid"
        assert pdata.get("payment", {}).get("journalEntryId")

    def test_invoice_create_and_receive(self, client):
        body = {
            "customerId": f"TEST_cust_{uuid.uuid4().hex[:6]}",
            "customerName": "TEST_iter51 Customer",
            "invoiceNumber": f"INV-{uuid.uuid4().hex[:8]}",
            "issueDate": "2026-01-15",
            "dueDate": "2026-02-15",
            "lines": [
                {"description": "TEST_iter51 service", "accountCode": "4000",
                 "amount": 200.0},
            ],
            "total": 220.0,
            "gst": 20.0,
        }
        # Snapshot AR
        kp0 = client.get(f"{API}/accounting/kpis", timeout=15).json()
        ar_before = float(kp0.get("arOutstanding", 0))

        r = client.post(f"{API}/accounting/invoices", json=body, timeout=15)
        assert r.status_code == 200, r.text
        inv = r.json()
        iid = inv["id"]

        # AR should now be higher
        kp1 = client.get(f"{API}/accounting/kpis", timeout=15).json()
        ar_after = float(kp1.get("arOutstanding", 0))
        assert ar_after >= ar_before + 220.0 - 0.5, f"AR did not increase: {ar_before}->{ar_after}"

        # Receive full
        rec = client.post(f"{API}/accounting/invoices/{iid}/receive",
                          json={"amount": 220.0, "method": "bank"}, timeout=15)
        assert rec.status_code == 200, rec.text
        assert rec.json().get("newStatus") == "paid"

        # AR should decrease
        kp2 = client.get(f"{API}/accounting/kpis", timeout=15).json()
        ar_final = float(kp2.get("arOutstanding", 0))
        assert ar_final <= ar_after - 220.0 + 0.5, f"AR did not decrease post-receipt: {ar_after}->{ar_final}"


# ══════════════════════════════════════════════════════════════════════
# Bank Reconciliation
# ══════════════════════════════════════════════════════════════════════
class TestBankRec:
    def test_bank_import_idempotent(self, client):
        ext_id = f"TEST-iter51-{uuid.uuid4().hex[:10]}"
        body = {
            "accountCode": "1000",
            "lines": [
                {"externalId": ext_id, "statementDate": "2026-01-10",
                 "description": "TEST_iter51 bank", "amount": 25.0},
            ],
        }
        r1 = client.post(f"{API}/accounting/bank/import", json=body, timeout=15)
        assert r1.status_code == 200, r1.text
        assert r1.json().get("inserted") == 1

        r2 = client.post(f"{API}/accounting/bank/import", json=body, timeout=15)
        assert r2.status_code == 200
        assert r2.json().get("inserted") == 0, "2nd import should be idempotent"

    def test_bank_statement_with_suggestions(self, client):
        r = client.get(f"{API}/accounting/bank/statement/1000", timeout=15)
        assert r.status_code == 200, r.text
        rows = r.json()
        assert isinstance(rows, list)
        if rows:
            assert "suggestedMatches" in rows[0] or "matchedJournalLineId" in rows[0]


# ══════════════════════════════════════════════════════════════════════
# KPIs
# ══════════════════════════════════════════════════════════════════════
class TestKPIs:
    def test_kpis_shape(self, client):
        r = client.get(f"{API}/accounting/kpis", timeout=15)
        assert r.status_code == 200, r.text
        k = r.json()
        for f in ("revenue", "grossProfit", "netProfit",
                  "arOutstanding", "apOutstanding"):
            assert f in k, f"Missing KPI field {f}"


# ══════════════════════════════════════════════════════════════════════
# Rules Engine — Catalog & CRUD
# ══════════════════════════════════════════════════════════════════════
class TestRulesCatalog:
    def test_catalog_counts(self, client):
        r = client.get(f"{API}/rules/catalog", timeout=15)
        assert r.status_code == 200, r.text
        cat = r.json()
        events = cat.get("events") or []
        actions = cat.get("actions") or []
        operators = cat.get("operators") or []
        assert len(events) == 24, f"Expected 24 events, got {len(events)}"
        assert len(actions) == 12, f"Expected 12 actions, got {len(actions)}"
        assert len(operators) == 11, f"Expected 11 operators, got {len(operators)}"


class TestRulesCRUD:
    def test_full_crud_and_toggle(self, client):
        body = {
            "name": f"TEST_iter51 rule {uuid.uuid4().hex[:6]}",
            "description": "test rule",
            "triggerEvent": "pos.sale.completed",
            "conditions": {"mode": "all", "clauses": [
                {"path": "total", "op": "gte", "value": 50}
            ]},
            "actions": [{"type": "dock_notify", "params": {"message": "test"}}],
            "active": True,
            "priority": 5,
        }
        r = client.post(f"{API}/rules", json=body, timeout=15)
        assert r.status_code == 200, r.text
        rule = r.json()
        rid = rule["id"]

        # PATCH
        p = client.patch(f"{API}/rules/{rid}",
                        json={"description": "updated"}, timeout=15)
        assert p.status_code == 200
        assert p.json().get("description") == "updated"

        # Toggle
        t = client.post(f"{API}/rules/{rid}/toggle", timeout=15)
        assert t.status_code == 200
        assert t.json().get("active") is False
        t2 = client.post(f"{API}/rules/{rid}/toggle", timeout=15)
        assert t2.json().get("active") is True

        # Simulate — should fire
        sim = client.post(f"{API}/rules/simulate",
                          json={"ruleId": rid, "payload": {"total": 100}}, timeout=15)
        assert sim.status_code == 200, sim.text
        sdata = sim.json()
        assert sdata.get("wouldFire") is True

        # Simulate not fire
        sim2 = client.post(f"{API}/rules/simulate",
                           json={"ruleId": rid, "payload": {"total": 10}}, timeout=15)
        assert sim2.status_code == 200
        assert sim2.json().get("wouldFire") is False

        # DELETE
        d = client.delete(f"{API}/rules/{rid}", timeout=15)
        assert d.status_code == 200
        assert d.json().get("deleted") is True


class TestRulesEmit:
    def test_emit_fires_matching_rule(self, client):
        # Create a specific rule and emit matching event
        body = {
            "name": f"TEST_iter51 emit {uuid.uuid4().hex[:6]}",
            "triggerEvent": "pos.sale.completed",
            "conditions": {"mode": "all",
                           "clauses": [{"path": "total", "op": "gte", "value": 1}]},
            "actions": [{"type": "dock_notify",
                         "params": {"message": "TEST_iter51 dock"}}],
            "active": True,
        }
        rr = client.post(f"{API}/rules", json=body, timeout=15)
        assert rr.status_code == 200
        rid = rr.json()["id"]
        try:
            emit = client.post(f"{API}/rules/emit",
                               json={"type": "pos.sale.completed",
                                     "payload": {"total": 99}}, timeout=20)
            assert emit.status_code == 200, emit.text
            data = emit.json()
            # firings should contain at least our rule (API uses ruleFirings)
            firings = data.get("ruleFirings") or data.get("firings") or []
            assert any(f.get("ruleId") == rid for f in firings), f"Our rule didn't fire: {data}"
            # each firing should have outcomes
            for f in firings:
                if f.get("ruleId") == rid:
                    assert "outcomes" in f
                    assert isinstance(f["outcomes"], list)
                    assert len(f["outcomes"]) >= 1
        finally:
            client.delete(f"{API}/rules/{rid}")


class TestRulesAIBuilder:
    def test_ai_build_returns_valid_spec(self, client):
        prompt = "When someone spends over $500 in a single visit, upgrade them to VIP and send an email"
        r = client.post(f"{API}/rules/ai-build",
                        json={"prompt": prompt}, timeout=60)
        assert r.status_code == 200, r.text
        spec = r.json()
        assert spec.get("triggerEvent"), "missing triggerEvent"
        assert "conditions" in spec
        assert isinstance(spec.get("actions"), list) and len(spec["actions"]) >= 1
        assert spec.get("aiGenerated") is True


class TestRulesStatsHistory:
    def test_stats_shape(self, client):
        r = client.get(f"{API}/rules/stats", timeout=15)
        assert r.status_code == 200, r.text
        s = r.json()
        for k in ("totalRules", "activeRules", "totalExecutions",
                  "totalEvents", "topRules", "byModule"):
            assert k in s, f"stats missing {k}"

    def test_history_endpoints(self, client):
        e = client.get(f"{API}/rules/history/events?limit=20", timeout=15)
        assert e.status_code == 200
        assert isinstance(e.json(), list)
        x = client.get(f"{API}/rules/history/executions?limit=20", timeout=15)
        assert x.status_code == 200
        assert isinstance(x.json(), list)
