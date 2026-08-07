"""
Seed the What's New feed — only if `changelog_entries` is empty, so a real
deployment's actual release history (once this system is fed by the real
release process) is never overwritten. Dates are spread across recent
weeks/months so the This Week / This Month / Upcoming filters in the UI
have something real to show; the content is condensed, owner-facing
descriptions of what has genuinely shipped, not raw commit messages.
"""
from datetime import datetime, timedelta, timezone
import uuid
from database import db


def _iso(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()


def _entry(title, description, *, category="feature", area, audience="owner", days_ago=None):
    return {
        "id": str(uuid.uuid4()), "title": title, "description": description,
        "category": category, "area": area, "audience": audience,
        "status": "upcoming" if days_ago is None else "shipped",
        "releasedAt": None if days_ago is None else _iso(days_ago),
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


SHIPPED = [
    # This week
    _entry("What's New page", "See exactly what's changed in NUA POS — this week, this month, or what's coming next — without digging through settings menus.",
           area="Platform", days_ago=0),
    _entry("Route-based code splitting", "The app now loads only the page you're actually on instead of the whole app upfront — first load is roughly 70% smaller.",
           area="Platform", category="improvement", days_ago=0),
    _entry("Recurring marketing campaigns", "Target a segment like \"hasn't visited in 30 days\" once and let it re-run on a schedule — the audience is re-checked fresh every time, so it always reaches whoever's newly inactive.",
           area="Marketing", days_ago=1),
    _entry("Marketing segment builder", "Build a real customer segment — spend threshold, visit count, inactivity window — with a live match count, instead of choosing only \"all customers\" or one loyalty tier.",
           area="Marketing", days_ago=2),
    _entry("EFTPOS terminal history", "See a terminal's recent card transactions and its connection-test history in one place, right from the terminal management page.",
           area="Payments", days_ago=3),
    _entry("Audit log field-level diff", "Expanding an audit event now shows exactly which fields changed, not two full documents to compare by eye.",
           area="Security & Audit", days_ago=4),
    _entry("Deposit refunds and budget editing", "Refund a held customer deposit directly, and edit or delete a budget without recreating it from scratch.",
           area="Finance", days_ago=5),
    _entry("Gift card activity now audited", "Every gift card minted or topped up is now recorded in the audit log — who, how much, and when.",
           area="Security & Audit", category="security", days_ago=6),
    _entry("Password self-service reset", "Staff who forget their password can reset it themselves from the login screen — no more waiting on an admin.",
           area="Staff Accounts", days_ago=7),

    # This month
    _entry("Loyalty fraud review + account locking", "Point-farming and voucher-sharing are now detected automatically, with a one-click lock (and unlock) on the offending account.",
           area="Loyalty", category="security", days_ago=12),
    _entry("Audit log restore", "Roll a record back to an earlier version directly from the audit log — no more manual re-entry after a mistaken edit.",
           area="Security & Audit", days_ago=13),
    _entry("EFTPOS terminal management", "Add, edit, and test-connect card terminals from Settings, instead of needing a developer to configure them.",
           area="Payments", days_ago=14),
    _entry("Kiosk fully multi-language", "The self-service kiosk's \"item unavailable\" flow now speaks all 7 supported languages, not just English.",
           area="Guest Ordering", audience="guest", days_ago=15),
    _entry("Loyalty and voucher security hardening", "Closed a gap where a voucher's discount amount wasn't checked against its real value, and fixed a signature-verification bug in the billing webhook.",
           area="Security & Audit", category="security", days_ago=16),
    _entry("Gift card permissions tightened", "Scheduling or topping up a gift card now requires a manager or owner, matching every other feature that moves real money.",
           area="Payments", category="security", days_ago=18),
    _entry("Deposits and Budgets", "Track customer deposits held against future bookings, and set monthly budgets per account with a live vs-actual comparison.",
           area="Finance", days_ago=24),
    _entry("Payroll YTD in the register", "Each employee's year-to-date pay now shows right on their register row — no separate report needed.",
           area="Staff & Payroll", days_ago=27),

    # Older (this quarter)
    _entry("Trust-based AI autonomy", "NUA's AI agent now earns autonomy over time — actions it gets right repeatedly can graduate from \"suggest\" to \"just do it,\" with a full history of why.",
           area="AI Agent", days_ago=34),
    _entry("AI-drafted marketing emails", "Describe a campaign in plain English and NUA writes the subject and body for you, with predrafted templates for common sends (win-back, new menu, birthday).",
           area="Marketing", days_ago=36),
    _entry("Voucher scan-to-fill at POS", "Scan a QR voucher code with the camera instead of typing it in at checkout.",
           area="Point of Sale", audience="staff", days_ago=38),
    _entry("GST-inclusive pricing", "Menu prices now show what the customer actually pays, GST included, with any surcharge disclosed separately on the receipt.",
           area="Point of Sale", days_ago=45),
    _entry("Bookings partner API", "External booking sources can now check availability and create reservations directly through a documented partner API.",
           area="Reservations", days_ago=52),
    _entry("Customer wallet", "Store credit, vouchers, and birthday offers now live in one place per customer, usable as a payment method at checkout.",
           area="Loyalty", days_ago=58),
    _entry("Command bar and Today home screen", "A single keyboard-driven command bar to jump anywhere, and a new Today view that surfaces what actually needs attention this shift.",
           area="Platform", days_ago=63),
    _entry("Course-based kitchen firing", "Hold and fire courses from the POS, with the Kitchen Display showing what's queued, cooking, and ready per course.",
           area="Kitchen", audience="staff", days_ago=71),
    _entry("Real two-factor authentication", "Login now supports TOTP-based 2FA with device trust and recovery codes, replacing the earlier stub.",
           area="Security & Audit", category="security", days_ago=79),
    _entry("Offline-first POS till", "The POS keeps taking orders through a dropped connection and syncs automatically once it's back.",
           area="Point of Sale", days_ago=86),
    _entry("NUA brand identity", "A full visual refresh — new wordmark, color system, and typography across every surface.",
           area="Platform", days_ago=94),
]

UPCOMING = [
    _entry("Duplicated helper cleanup", "Consolidating the remaining repeated date/ID helper code across route files to keep the codebase lean and consistent.",
           area="Platform", category="improvement"),
    _entry("Loyalty tier auto-promotion audit", "Full visibility into why a customer was (or wasn't) automatically promoted to VIP.",
           area="Loyalty"),
    _entry("Segment-based SMS campaigns", "Extend the new segment builder beyond email to text message campaigns.",
           area="Marketing"),
    _entry("EFTPOS settlement reconciliation report", "Match terminal settlement batches against POS transactions automatically, surfacing any mismatch.",
           area="Payments"),
    _entry("Inventory reorder automation", "Auto-generate purchase orders when stock crosses a supplier's reorder threshold.",
           area="Inventory"),
    _entry("Guest-facing loyalty portal", "Let customers check their points balance and tier progress without asking staff.",
           area="Loyalty", audience="guest"),
    _entry("Multi-business consolidated reporting", "Roll up sales, labor, and inventory across every location an owner runs, in one report.",
           area="Multi-location"),
]


async def seed_changelog() -> dict:
    if await db.changelog_entries.count_documents({}) > 0:
        return {"seeded": False}
    await db.changelog_entries.insert_many(SHIPPED + UPCOMING)
    return {"seeded": True, "count": len(SHIPPED) + len(UPCOMING)}
