"""Indexes for the collections every shift actually hits.

Before this, the whole backend had four indexes: one unique index on login
email, and three TTL indexes added alongside the coursing and 2FA work. Every
other query — the transaction history, the customer list, the kitchen board,
the product catalogue — was a full collection scan. That's invisible on a demo
database with a few hundred rows and it stays invisible right up until a real
venue has a year of trading behind it, at which point the P&L takes seconds
and the floor tablets start to lag mid-service.

This is additive only: creating an index that already exists is a no-op, so
this can run on every startup without special-casing "first run" vs
"upgrading an existing venue". mongomock (used by the test suite) accepts the
same calls, so nothing here is production-only code that never gets exercised.
"""
import logging

from database import db

log = logging.getLogger(__name__)


async def ensure_indexes() -> None:
    try:
        # Transactions: the busiest collection in the system. timestamp backs
        # every dashboard's date filter; customerId backs the profile/wallet
        # lookups; tableNumber backs the running-tab-per-table screens.
        await db.transactions.create_index("timestamp")
        await db.transactions.create_index("customerId")
        await db.transactions.create_index("tableNumber")

        # Kitchen board: filtered by status constantly (KDS polling/SSE), and
        # sorted by createdAt within a status.
        await db.kitchen_orders.create_index([("status", 1), ("createdAt", 1)])
        await db.kitchen_orders.create_index("tableNumber")
        await db.kitchen_orders.create_index("transactionId")

        # Customers: search is a case-insensitive regex over these three
        # fields (routes/customers.py), and lookups by id happen everywhere
        # wallets, vouchers and loyalty touch a customer.
        await db.customers.create_index("email")
        await db.customers.create_index("phone")
        await db.customers.create_index("id", unique=True)

        # Products: category is the single most common filter (POS category
        # bar, storefront, kiosk); id is looked up constantly for pricing.
        await db.products.create_index("category")
        await db.products.create_index("id", unique=True)

        # Expenses and suppliers feed the accounting reports, filtered by
        # date range and category.
        await db.expenses.create_index("date")
        await db.expenses.create_index("category")

        # Reservations: looked up by date for the pre-shift dashboard and
        # by table for the floor plan.
        await db.reservations.create_index("date")
        await db.reservations.create_index("tableNumber")
    except Exception as e:
        # mongomock supports create_index, but an unusual server version or a
        # transient connection hiccup shouldn't take the whole app down over
        # what is purely a performance optimisation.
        log.warning("Index creation failed (non-fatal): %s", e)
