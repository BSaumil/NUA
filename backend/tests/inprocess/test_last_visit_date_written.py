"""Checkout only ever wrote customers.lastVisit (a bare ISO string) — never
customers.lastVisitDate, the field the Customer model actually declares
(models/customer.py) and the one loyalty_engine's segmentation and the
marketing segment builder's "inactive for N days" rule both read. Every
real customer's lastVisitDate stayed permanently null forever, making
those two features silently see every customer as having never visited —
regardless of how many real transactions they'd made.
"""
import asyncio

from conftest import req


def test_checkout_writes_lastvisitdate_not_just_lastvisit(client, owner_headers):
    created = req(client, "POST", "/api/customers", headers=owner_headers, json={
        "name": "Frequent Diner", "email": "frequent@nua.com", "phone": "0400111222"})
    assert created.status_code == 200, created.text[:200]
    customer_id = created.json()["id"]

    sale = req(client, "POST", "/api/transactions", headers=owner_headers, json={
        "items": [{"productId": "no-such-product", "productName": "Custom item", "quantity": 1, "price": 20}],
        "paymentMethod": "cash", "location": "Main", "cashier": "Test Cashier",
        "customerId": customer_id})
    assert sale.status_code == 200, sale.text[:200]

    loop = asyncio.get_event_loop()
    from database import db
    doc = loop.run_until_complete(db.customers.find_one({"id": customer_id}, {"_id": 0}))
    assert doc.get("lastVisit"), "lastVisit must still be set — other readers (nua_intelligence, v25_suite) depend on it"
    assert doc.get("lastVisitDate"), "lastVisitDate must now also be set — this is what segmentation reads"


def test_a_customer_who_just_visited_is_not_flagged_inactive(client, owner_headers):
    created = req(client, "POST", "/api/customers", headers=owner_headers, json={
        "name": "Just Visited", "email": "justvisited@nua.com", "phone": "0400333444"})
    customer_id = created.json()["id"]

    sale = req(client, "POST", "/api/transactions", headers=owner_headers, json={
        "items": [{"productId": "no-such-product", "productName": "Custom item", "quantity": 1, "price": 15}],
        "paymentMethod": "cash", "location": "Main", "cashier": "Test Cashier",
        "customerId": customer_id})
    assert sale.status_code == 200, sale.text[:200]

    preview = req(client, "POST", "/api/marketing/segments/preview", headers=owner_headers,
                  json={"rules": {"inactiveForDays": 30}})
    inactive_emails = {c["email"] for c in preview.json()["sample"]}
    assert "justvisited@nua.com" not in inactive_emails
