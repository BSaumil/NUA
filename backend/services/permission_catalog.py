"""Central permission catalog — single source of truth for RBAC.

Everything the Owner can access is enumerated here, grouped by section. The
frontend renders one collapsible pane per section with per-feature checkboxes,
and per-role defaults are stored in `db.role_permissions`. Individual staff can
override with `customPermissions` on the user document.

Sections stay ordered — the order below is the render order in Settings.
"""
from __future__ import annotations
from typing import Any, Dict, List

# Ordered sections. Each `features` entry is (id, label).
PERMISSION_CATALOG: List[Dict[str, Any]] = [
    {"section": "Sales", "icon": "ShoppingCart", "features": [
        ("pos", "POS Terminal"),
        ("tables", "Table Sales"),
        ("comp-void", "Comp / Void"),
        ("payment-links", "Payment Links"),
        ("tip-management", "Tip Management"),
        ("cash-drawer", "Open Cash Drawer (no-sale)"),
    ]},
    {"section": "Bookings", "icon": "CalendarDays", "features": [
        ("reservations", "Reservations"),
        ("bookings-inbox", "Bookings Inbox"),
        ("waitlist", "Waitlist"),
        ("floor-plan", "Floor Plan"),
        ("table-layout", "Table Layout"),
        ("booking-settings", "Booking Settings"),
        ("booking-analytics", "Booking Analytics"),
        ("booking-heatmap", "Booking Heatmap"),
    ]},
    {"section": "Kitchen", "icon": "ChefHat", "features": [
        ("kitchen", "KDS (Kitchen Display)"),
        ("pre-shift", "Pre-Shift Brief"),
        ("temperature", "HACCP Temperature"),
        ("kitchen-load", "Kitchen Load"),
        ("fire-course", "Fire / Hold Courses"),
        ("voice-recipe", "Voice Recipe"),
    ]},
    {"section": "Menu & Products", "icon": "Utensils", "features": [
        ("products", "Products"),
        ("categories", "Categories"),
        ("modifiers", "Modifiers"),
        ("menu-engineering", "Menu Engineering"),
        ("what-if", "What-If Simulator"),
        ("ab-tests", "Menu A/B Tests"),
        ("channel-menus", "Channel Menus"),
        ("price-tune", "Price Tune"),
        ("surge-pricing", "Surge Pricing"),
    ]},
    {"section": "Inventory", "icon": "Package", "features": [
        ("inventory", "Inventory"),
        ("ai-pantry", "AI Pantry"),
        ("measured-stock", "Measured / Pour Stock"),
        ("forecasting", "Forecasting"),
        ("inventory-accounting", "Inventory Accounting"),
        ("anomalies", "Anomalies"),
        ("purchase-orders", "Purchase Orders"),
        ("disputes", "Disputes / Chargebacks"),
    ]},
    {"section": "Customers & Loyalty", "icon": "Users", "features": [
        ("customers", "Customers"),
        ("loyalty", "Loyalty"),
        ("loyalty-config", "Loyalty Config"),
        ("loyalty-progress", "Loyalty Progress"),
        ("marketing", "Marketing"),
        ("email-marketing", "Email Marketing"),
        ("vouchers", "Vouchers / Gift Cards"),
        ("leaderboard", "Staff Leaderboard"),
    ]},
    {"section": "Analytics & Insights", "icon": "BarChart3", "features": [
        ("today", "Today (Home)"),
        ("dashboard", "Dashboard"),
        ("command-center", "Command Center"),
        ("hq", "HQ Dashboard"),
        ("live-sales", "Live Sales"),
        ("cohort-retention", "Cohort Retention"),
        ("ai-cost-coach", "AI Cost Coach"),
    ]},
    {"section": "Finance", "icon": "DollarSign", "features": [
        ("accounting", "Accounting"),
        ("finance", "Finance Ledger"),
        ("bas-gst", "BAS / GST"),
        ("end-of-day", "End of Day"),
        ("super", "Superannuation"),
        ("payroll", "Payroll"),
    ]},
    {"section": "Staff & Rosters", "icon": "UserCog", "features": [
        ("staff", "Staff Management"),
        ("staff-roster", "Rosters"),
        ("shift-swaps", "Shift Swaps"),
        ("shift-manager", "Shift Manager"),
        ("labor-forecast", "Labor Forecast"),
        ("quarterly-review", "Quarterly Review"),
        ("staff-availability", "Staff Availability"),
    ]},
    {"section": "Automation & AI", "icon": "Sparkles", "features": [
        ("automation", "Automations"),
        ("automation-triggers", "Automation Triggers"),
        ("ash", "NUA Agent"),
        ("ash-hq", "NUA HQ"),
        ("ash-plans", "NUA Plans"),
        ("ash-permissions", "NUA Tool Permissions"),
        ("ash-memory", "NUA Memory"),
        ("nua-pro", "NUA Pro"),
        ("agent", "Agent Dashboard"),
        ("agent-autonomy", "Agent Autonomy"),
        ("phone-agent", "Phone Agent"),
        ("profit-guardian", "Profit Guardian"),
        ("digital-twin", "Digital Twin"),
        ("auto-marketing", "Auto Marketing"),
    ]},
    {"section": "Approvals & Audit", "icon": "ShieldCheck", "features": [
        ("approvals", "Approval Queue"),
        ("audit", "Audit Trail"),
        ("audit-log", "Audit Log"),
        ("exceptions", "Exceptions"),
        ("security", "Security & Compliance"),
    ]},
    {"section": "Enterprise", "icon": "Building2", "features": [
        ("enterprise", "Enterprise Command Center"),
        ("hardware-health", "Hardware Health"),
        ("integrations", "Integrations"),
    ]},
    {"section": "Settings", "icon": "Settings", "features": [
        ("settings", "Settings & Configuration"),
    ]},
]


def all_permission_ids() -> List[str]:
    return [fid for s in PERMISSION_CATALOG for (fid, _) in s["features"]]


def catalog_for_ui() -> List[Dict[str, Any]]:
    """Same shape as PERMISSION_CATALOG but with dict `features` for JSON."""
    return [
        {"section": s["section"], "icon": s["icon"], "features": [{"id": fid, "label": label} for fid, label in s["features"]]}
        for s in PERMISSION_CATALOG
    ]


# Sensible role defaults. Owner has "*" (all). Others are OWNER-editable via
# /api/permissions/roles/{role}.
DEFAULT_ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "owner": ["*"],
    "manager": [
        "today",
        "pos", "tables", "comp-void", "payment-links", "tip-management",
        "reservations", "bookings-inbox", "waitlist", "floor-plan", "table-layout",
        "booking-settings", "booking-analytics", "booking-heatmap",
        "kitchen", "pre-shift", "temperature", "kitchen-load", "fire-course",
        "products", "categories", "modifiers", "menu-engineering", "what-if",
        "ab-tests", "channel-menus",
        "inventory", "ai-pantry", "measured-stock", "forecasting",
        "inventory-accounting", "anomalies", "purchase-orders",
        "customers", "loyalty", "loyalty-config", "loyalty-progress",
        "marketing", "email-marketing", "vouchers", "leaderboard",
        "dashboard", "command-center", "live-sales", "cohort-retention",
        "end-of-day",
        "staff", "staff-roster", "shift-swaps", "shift-manager", "labor-forecast",
        "automation", "automation-triggers",
        # "ash" (Ask NUA / the agent chat) is deliberately NOT a manager
        # default — it's owner-only until the owner explicitly grants it via
        # Settings > Permissions, either for the manager role or a specific
        # staff member. ash-plans/ash-memory (viewing plan + memory history)
        # stay on since those are read-only, not "ask NUA anything".
        "ash-plans", "ash-memory",
        "approvals", "audit", "audit-log", "exceptions",
        "hardware-health", "integrations",
    ],
    "cashier": [
        "pos", "tables", "comp-void", "payment-links",
        # Servers fire and hold courses from the POS cart during service.
        "fire-course",
        "reservations", "waitlist", "floor-plan",
        "customers", "loyalty-progress", "vouchers",
        "products",
    ],
    "kitchen": [
        "kitchen", "pre-shift", "temperature", "kitchen-load", "voice-recipe",
        "fire-course",
        "products",
    ],
}
