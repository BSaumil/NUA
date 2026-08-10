"""Critical Pulse alerts (stockouts) fan out through the in-app notification
bell, deduped per day so a dashboard polled every ~60s doesn't spam it."""
from conftest import req


def test_critical_alert_notifies_owner_once_per_day(client, owner_headers):
    # Force a stockout: an active product with stock <= 0.
    prod = req(client, "POST", "/api/products", headers=owner_headers, json={
        "name": "ZZZ Stockout Test Item", "category": "Test", "price": 5.0,
        "cost": 2.0, "stock": 0, "sku": "ZZZ-STOCKOUT",
    }).json()
    assert prod["stock"] <= 0

    r1 = req(client, "GET", "/api/analytics/today-pulse", headers=owner_headers)
    assert r1.status_code == 200
    assert any(a["kind"] == "stockout" for a in r1.json()["alerts"])

    notifs = req(client, "GET", "/api/notifications", headers=owner_headers).json()
    stockout_notifs = [n for n in notifs if "out of stock" in n.get("body", "")]
    assert len(stockout_notifs) >= 1

    # Poll again — must not double-notify for the same day.
    req(client, "GET", "/api/analytics/today-pulse", headers=owner_headers)
    notifs2 = req(client, "GET", "/api/notifications", headers=owner_headers).json()
    stockout_notifs2 = [n for n in notifs2 if "out of stock" in n.get("body", "")]
    assert len(stockout_notifs2) == len(stockout_notifs)
