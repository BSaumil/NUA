"""P&L and accounting summary scoped transaction revenue to the caller's
business but left expenses completely unscoped, mixing one business's real
revenue with every business's combined expenses. Expenses are now stamped
with businessId on create and the P&L/summary queries scope them the same
way transactions already are."""
from conftest import req


def test_created_expense_is_stamped_with_the_creators_business(client, owner_headers):
    r = req(client, "POST", "/api/expenses", headers=owner_headers, json={
        "category": "Ingredients", "amount": 42.0, "description": "ZZZ test expense",
        "paymentMethod": "card", "location": "Main", "createdBy": "Owner",
    })
    assert r.status_code == 200, r.text
    assert r.json()["businessId"] == "default"


def test_p_and_l_does_not_mix_in_another_businesss_expenses(client, owner_headers):
    from database import db
    import asyncio

    async def seed():
        await db.expenses.insert_one({
            "id": "EXP-ZZZ-OTHER", "category": "Ingredients", "amount": 999999.0,
            "description": "ZZZ other business expense", "paymentMethod": "card",
            "location": "Main", "createdBy": "Someone Else", "businessId": "BIZ-UNRELATED-EXPENSE",
        })
    asyncio.get_event_loop().run_until_complete(seed())

    r = req(client, "GET", "/api/accounting/p-and-l", headers=owner_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["costOfGoods"] < 999999.0

    r2 = req(client, "GET", "/api/accounting/summary", headers=owner_headers)
    assert r2.json()["expenses"] < 999999.0
