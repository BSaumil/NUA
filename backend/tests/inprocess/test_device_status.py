"""GET /api/ops/device-status — the login screen's peripheral-readiness
signal. Public (no token yet at that point) and deliberately thin: only
counts/booleans, never terminal IDs, IPs, or API keys."""
from conftest import req


def test_device_status_is_public_and_thin(anon, client, owner_headers):
    # Delta-based, not an absolute count: the test DB is shared across this
    # whole pytest session, so other suites may have already created active
    # terminals (same reasoning as test_reporting_aggregation.py).
    before = req(anon, "GET", "/api/ops/device-status")
    assert before.status_code == 200, before.text
    assert "apiKey" not in before.json() and "ipAddress" not in before.json()
    before_count = before.json()["cardReaderCount"]

    req(client, "POST", "/api/eftpos/terminals", headers=owner_headers, json={
        "provider": "tyro", "terminalId": "T1", "merchantId": "M1",
        "name": "ZZZ Test Terminal", "location": "Bar", "connectionType": "tcp",
    })
    after = req(anon, "GET", "/api/ops/device-status").json()
    assert after["cardReaderConnected"] is True
    assert after["cardReaderCount"] == before_count + 1
