"""Several best-effort `except Exception: pass` blocks after audit-log
writes were converted to log a warning via the new shared
utils.errors.log_and_continue — the write itself still can't block the
real mutation that already succeeded (a sale, a journal entry, a fraud
flag resolution), but a failure there is no longer completely invisible.
This pins the highest-value one: the POS sale audit log, whose own
comment claims "always logged".
"""
import logging

from conftest import req


def test_a_failed_pos_sale_audit_log_write_is_logged_not_silent(client, owner_headers, monkeypatch, caplog):
    async def failing_log_event(*args, **kwargs):
        raise RuntimeError("audit db unreachable")

    import services.audit_service as audit_service
    monkeypatch.setattr(audit_service, "log_event", failing_log_event)

    with caplog.at_level(logging.WARNING, logger="routes.transactions"):
        r = req(client, "POST", "/api/transactions", headers=owner_headers, json={
            "items": [{"productId": "no-such-product", "productName": "Custom item", "quantity": 1, "price": 10}],
            "paymentMethod": "cash", "location": "Main", "cashier": "Test Cashier"})

    # The sale itself must still succeed — a broken audit write is a
    # best-effort side effect, never a reason to fail the sale.
    assert r.status_code == 200, r.text[:200]
    assert any("audit log write failed" in rec.message for rec in caplog.records), \
        "the failure must be logged, not silently swallowed"
