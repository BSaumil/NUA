"""The provider registry — the single source of truth for what NUA Connect
honestly supports today, replacing routes/integrations.py's old hardcoded
list where every provider could be flipped to "connected" by anyone who
typed any string into the API-key box.

Status semantics (never fudged):
  not_implemented       — no connector code exists yet. Cannot connect.
  needs_credentials      — connector code exists; this venue hasn't supplied
                            credentials yet.
  connected               — connector code exists, credentials are saved, and
                            the last test_connection/sync call succeeded.
  error                   — credentials saved but the last call failed.
  pending_accreditation  — real CDR client code exists, but Consumer Data
                            Right accreditation is a regulatory process, not
                            a config step. Australian banks under CDR are
                            ALWAYS this status, regardless of what
                            credentials are on file — never "connected".
  preconfigured           — wired via a deploy-time secret, not a per-venue
                            credential (Stripe today, via STRIPE_API_KEY).
"""
from dataclasses import dataclass, field
from typing import Optional

from services.connect.base import BaseConnector


@dataclass
class ProviderMeta:
    slug: str
    name: str
    category: str
    description: str
    website: str = ""
    key_label: str = "API Key"
    credential_fields: list = field(default_factory=lambda: ["apiKey"])
    connector: Optional[BaseConnector] = None
    is_cdr_bank: bool = False
    preconfigured: bool = False


def _connectors():
    # Imported lazily so importing the registry never requires every
    # connector module's own imports (e.g. httpx) to succeed first.
    from services.connect.connectors.square import SquareConnector
    from services.connect.connectors.cdr_bank import make_cdr_connector
    return SquareConnector, make_cdr_connector


def _build_registry() -> list:
    SquareConnector, make_cdr_connector = _connectors()
    square = SquareConnector()

    providers = [
        # ============ FULLY BUILT — flagship Connect connector ============
        ProviderMeta(
            slug="square", name="Square", category="Payments",
            description="Full two-way sync: catalog, sales, and customers flow into NUA in real time via webhooks.",
            website="https://developer.squareup.com",
            key_label="Access Token",
            credential_fields=["accessToken", "locationId", "environment", "webhookSignatureKey", "webhookNotificationUrl"],
            connector=square,
        ),

        # ============ Delivery ============
        ProviderMeta("uber-eats", "Uber Eats", "Delivery", "Receive and manage Uber Eats orders directly in your POS", "https://merchants.ubereats.com", "API Key"),
        ProviderMeta("doordash", "DoorDash", "Delivery", "Sync DoorDash orders into your kitchen display", "https://merchants.doordash.com", "API Key"),
        ProviderMeta("menulog", "Menulog", "Delivery", "Manage Menulog orders and menu sync", "https://www.menulog.com.au/restaurants", "API Key"),

        # ============ Middleware ============
        ProviderMeta("doshii", "Doshii", "Middleware", "Connect 20+ hospitality apps via one integration. Powers Uber Eats, DoorDash, Deputy, and more.", "https://doshii.com", "Location Token"),

        # ============ Payments ============
        ProviderMeta("stripe", "Stripe", "Payments", "Accept card payments with Stripe Checkout", "https://stripe.com", preconfigured=True),
        ProviderMeta("commbank", "CommBank Smart", "Payments", "CommBank EFTPOS and pay-at-table via Doshii", "https://www.commbank.com.au/business/payments/hospitality.html", "Merchant ID"),

        # ============ Accounting ============
        ProviderMeta("xero", "Xero", "Accounting", "Auto-sync daily sales, expenses, and GST to Xero", "https://www.xero.com/au/", "OAuth Client ID"),
        ProviderMeta("myob", "MYOB", "Accounting", "Push transactions and BAS data to MYOB", "https://www.myob.com/au", "API Key"),
        ProviderMeta("quickbooks", "QuickBooks", "Accounting", "Sync sales data with QuickBooks Online", "https://quickbooks.intuit.com/au/", "Client ID"),

        # ============ Rostering ============
        ProviderMeta("deputy", "Deputy", "Rostering", "Auto-sync sales data for smart rostering and compliance", "https://www.deputy.com", "API Token"),
        ProviderMeta("tanda", "Tanda", "Rostering", "Workforce management with live POS data", "https://www.tanda.co", "API Token"),

        # ============ Reservations ============
        ProviderMeta("opentable", "OpenTable", "Reservations", "Sync OpenTable bookings with your floor plan", "https://restaurant.opentable.com", "Restaurant ID"),
        ProviderMeta("resdiary", "ResDiary", "Reservations", "Manage ResDiary reservations in NUA", "https://www.resdiary.com", "API Key"),

        # ============ In-Venue Ordering ============
        ProviderMeta("mryum", "Mr Yum", "In-Venue Ordering", "In-venue mobile ordering synced to kitchen", "https://www.mryum.com", "Venue Token"),
        ProviderMeta("hungryhungry", "HungryHungry", "In-Venue Ordering", "Order & pay at table integration", "https://www.hungryhungry.com", "API Key"),

        # ============ Loyalty & Marketing ============
        ProviderMeta("marsello", "Marsello", "Loyalty & Marketing", "Loyalty program and email marketing automation", "https://www.marsello.com", "API Key"),
        ProviderMeta("stampme", "Stamp Me", "Loyalty & Marketing", "Digital stamp cards and rewards", "https://stampme.com", "API Key"),

        # ============ Payment Terminals ============
        ProviderMeta("tyro", "Tyro EFTPOS", "Payment Terminals", "Tyro integrated EFTPOS — auto-print receipt + tip prompt + surcharging.", "https://www.tyro.com", "Merchant ID"),
        ProviderMeta("smartpay", "Smartpay", "Payment Terminals", "Smartpay integrated EFTPOS terminals + cloud reporting.", "https://www.smartpay.com.au", "Merchant ID"),
        ProviderMeta("qiki", "QIKI", "Payment Terminals", "QIKI BYO terminal + surcharging across all card schemes.", "https://qiki.com.au", "Merchant ID"),
        ProviderMeta("westpac-eftpos", "Westpac EFTPOS Air", "Payment Terminals", "Westpac Air all-in-one Android terminal.", "https://www.westpac.com.au/business-banking/merchant-services/", "Merchant ID"),
        ProviderMeta("anz-worldline", "ANZ Worldline", "Payment Terminals", "ANZ Worldline integrated payments + reporting.", "https://www.anzworldline.com.au", "Merchant ID"),
        ProviderMeta("nab-easytap", "NAB Easy Tap (Tap to Pay)", "Payment Terminals", "NAB tap-on-iPhone — no terminal needed.", "https://www.nab.com.au/business/payments-and-merchants/easy-tap", "Merchant ID"),
        ProviderMeta("square-terminal", "Square Terminal", "Payment Terminals", "Square's all-in-one card reader + register.", "https://squareup.com/au/en/hardware/terminal", "Access Token"),
        ProviderMeta("zeller", "Zeller", "Payment Terminals", "Zeller smart terminal + business banking.", "https://www.myzeller.com", "API Key"),
        ProviderMeta("mx51", "mx51 / Linkly", "Payment Terminals", "Multi-bank EFTPOS broker — connect any major AU terminal.", "https://mx51.io", "Merchant ID"),
        ProviderMeta("verifone", "Verifone", "Payment Terminals", "Verifone V200c / V400m terminals (global).", "https://www.verifone.com", "Terminal ID"),
        ProviderMeta("ingenico", "Ingenico", "Payment Terminals", "Ingenico Lane and Move series terminals.", "https://www.ingenico.com", "Terminal ID"),
        ProviderMeta("pax", "PAX Technology", "Payment Terminals", "PAX A920 / A77 Android smart terminals.", "https://www.pax.com", "Terminal ID"),
        ProviderMeta("adyen", "Adyen", "Payment Terminals", "Adyen omnichannel terminals — global enterprise.", "https://www.adyen.com", "API Key"),
        ProviderMeta("razorpay", "Razorpay", "Payment Terminals", "Razorpay POS terminals + payment links (IN / SE Asia).", "https://razorpay.com", "API Key"),
        ProviderMeta("paypal-zettle", "PayPal Zettle", "Payment Terminals", "PayPal Zettle card readers + business accounts.", "https://www.zettle.com", "API Key"),
    ]

    # ============ AUSTRALIAN BANKS — real CDR client, always pending_accreditation ============
    banks = [
        ("cba", "Commonwealth Bank (CBA)", "https://www.commbank.com.au/business.html"),
        ("westpac", "Westpac", "https://www.westpac.com.au/business-banking/"),
        ("anz", "ANZ", "https://www.anz.com.au/business/"),
        ("nab", "NAB", "https://www.nab.com.au/business"),
        ("macquarie", "Macquarie Bank", "https://www.macquarie.com.au/business-banking.html"),
        ("bendigo", "Bendigo Bank", "https://www.bendigobank.com.au/business/"),
        ("bankwest", "Bankwest", "https://www.bankwest.com.au/business"),
        ("suncorp", "Suncorp Bank", "https://www.suncorpbank.com.au/business"),
        ("hsbc-au", "HSBC Australia", "https://www.business.hsbc.com.au/"),
        ("ing-au", "ING Direct", "https://www.ing.com.au/business.html"),
        ("boq", "Bank of Queensland", "https://www.boq.com.au/business"),
    ]
    for slug, name, website in banks:
        providers.append(ProviderMeta(
            slug=slug, name=name, category="Banks (AU)",
            description=f"Reconcile NUA sales with {name} business accounts via Open Banking (CDR).",
            website=website, key_label="CDR Client Token",
            credential_fields=["cdrClientId", "cdrClientSecret"],
            connector=make_cdr_connector(slug, name),
            is_cdr_bank=True,
        ))

    return providers


_REGISTRY: Optional[list] = None


def all_providers() -> list:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def get_provider(slug: str) -> Optional[ProviderMeta]:
    for p in all_providers():
        if p.slug == slug:
            return p
    return None
