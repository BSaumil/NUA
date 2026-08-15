"""create_refund used to fetch the original transaction by id with no
ownership check, unlike its sibling get_transaction_detail which already
uses tenant_owns() — a manager/owner from one business could refund a
transaction belonging to a different one just by knowing/guessing its id."""
import uuid

from conftest import req


def _insert_transaction(business_id, total=50.0):
    from database import db
    import asyncio

    txn_id = f"TXN-{str(uuid.uuid4())[:8].upper()}"

    async def run():
        await db.transactions.insert_one({
            "id": txn_id, "businessId": business_id, "total": total,
            "items": [], "subtotal": total, "gst": 0, "paymentMethod": "cash",
        })
    asyncio.get_event_loop().run_until_complete(run())
    return txn_id


def test_cannot_refund_a_transaction_belonging_to_another_business(client, owner_headers):
    other_txn_id = _insert_transaction("BIZ-OTHER-TXN-OWNER")
    r = req(client, "POST", "/api/refunds", headers=owner_headers, json={
        "originalTransactionId": other_txn_id, "amount": 10.0, "reason": "test",
        "refundMethod": "original_payment", "processedBy": "Owner",
    })
    assert r.status_code == 404, r.text


def test_can_refund_a_transaction_belonging_to_own_business(client, owner_headers):
    own_txn_id = _insert_transaction("default", total=50.0)
    r = req(client, "POST", "/api/refunds", headers=owner_headers, json={
        "originalTransactionId": own_txn_id, "amount": 10.0, "reason": "test",
        "refundMethod": "original_payment", "processedBy": "Owner",
    })
    assert r.status_code == 200, r.text
