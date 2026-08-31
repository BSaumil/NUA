# NUA POS — Features, Capabilities & Competitive Positioning

*A current, code-verified inventory of what NUA POS does, and how it compares to the five most widely used POS platforms — Square, Toast, Clover, Lightspeed Restaurant, and TouchBistro.*

> Note: two older documents in this repo (`FEATURE_COMPARISON.md`, `INTEGRATIONS_AND_FEATURES.md`) are dated January 2025 and describe an earlier, much smaller build with several "framework ready" placeholder claims. This document replaces them with an accurate picture of what's actually implemented in the codebase today. Where something is a working mock (clearly marked as such in the code, pending a third-party business-verification step) rather than a live integration, it's called out explicitly below instead of being counted as shipped.

---

## 1. Core Point of Sale

- **Server-side pricing on every sale** — the checkout API re-prices every line from the live product catalog at the moment of sale; a tampered client-side price is never trusted.
- Touch-optimized terminal with category-grouped product grid, barcode/search entry, and configurable tile size/layout per venue.
- Product **variants** (size/color with their own SKUs), **modifiers** (add-ons, cooking level, extras with surcharges), bundles, and translations per product.
- Order types: retail, dine-in, takeaway, delivery — each with its own totals/receipt handling.
- Discounts & promotions (percentage, fixed, tiered membership discount, voucher codes), **surcharge rules** (weekend/public-holiday auto-surcharge), and configurable **auto-gratuity**.
- Split payments (multiple tenders on one sale), tipping, refunds/exchanges, store credit, gift cards, voucher/coupon engine.
- **Held/parked sales**: manual Hold-and-Recall tabs, plus an **automatic hold** created right before a hosted checkout redirect (Stripe/crypto) — if a guest backs out without paying, the sale is resumed or explicitly cancelled instead of silently lost. (See §12 for why this matters.)
- Offline-first sale queue: transactions taken with no connectivity are saved locally and synced automatically once the connection returns, with a visible "queued offline" indicator.
- Receipt printing via ESC/POS network thermal printers, kitchen printers with category-based routing, browser-print fallback, and a configurable cash-drawer trigger.
- **EFTPOS terminal integration** with real provider implementations for Linkly (PC-EFTPOS), Tyro, Smartpay, and Windcave — not just a settings page.
- Self-checkout **kiosk mode** and a customer-facing display.

## 2. Payments

- **Stripe Checkout** — hosted card checkout, webhook + polling confirmation, refunds via the Stripe API, idempotent server-side finalization (a webhook and a status-poll racing each other can't double-ring the same sale).
- **Crypto payments** (Bitcoin on-chain/Lightning, USDC) via Coinbase Commerce — same finalize pipeline as Stripe, so a crypto sale gets identical loyalty/stock/GST treatment for free.
- Gift cards and a universal **voucher engine** (single codes, bulk/corporate issuance, source-typed vouchers) with a validate-and-apply endpoint.
- Store credit issuance and redemption as a tender.
- Payment links for remote/phone orders.
- QR/UPI payment code generation.

## 3. Restaurant & Hospitality

- **Floor plan editor** with drag-placed tables, sections, shapes, and live status coloring.
- **Kitchen Display System (KDS)** — dockets flow from the POS the moment an order is sent, not just printed; hold/fire per course, per-course dwell timing, colour-coded table status on the floor plan by course + how long a table's been sitting.
- **Table course management**: courses assigned on the POS become real, trackable kitchen tickets.
- **Table combinations** for large parties spanning multiple physical tables.
- **Guest-facing bill splitting** — a QR/link a guest scans at the table to pick "by item" or "equal split," claim their own items (race-safe against two guests claiming the same line), and pay their own share via Stripe or crypto — verified by phone OTP, with real-time WebSocket sync so claims update live across every guest's phone and the staff dashboard. Supports **custom uneven splits**, tipping, itemized digital receipts, partial-payment tabs, and group-coordination invites.
- **Booking capacity & large-party rules engine** — a single, server-enforced rules service (not just client-side validation) covering booking-window limits (advance notice, same-day, booking hours, blocked weekdays), configurable **party-size tiers** (e.g. 1–6 à la carte, 7–12 requires a Set Menu, 13+ requires Private Dining + manager approval), opt-in hard capacity enforcement per time slot, and deposit/pre-order/approval workflows for large bookings — enforced identically whether the booking comes from the public booking widget or a staff member on the phone.
- Reservation management: guest lookup with booking-desk intel (last visit, allergies, standing requests), blackout dates, waitlist with live position tracking, AI-assisted table auto-assignment, no-show tracking.
- **AI Concierge — inbound voice reservations**: a customer calls the venue's own number, and an AI agent gathers party size/date/time/name across a real phone conversation and creates the reservation, no human needed.
- **AI outbound voice calls** — the AI agent can call a guest to confirm a booking or chase a no-show risk, not just text/email.
- Booking analytics (channel mix, revenue attribution, party-size distribution) as a real reporting layer, not vanity counters.
- Age-verification workflow for alcohol/restricted items, allergen and dietary tagging.

## 4. Guest-Facing / Online Channels

- Public booking portal, online ordering storefront, QR table ordering (scan-to-order-and-pay at the table with no app download).
- **Guest identity via phone OTP** (passwordless) shared across booking, waitlist, loyalty and bill-splitting — one verified identity, not five separate logins.
- Order tracking pages, waitlist tracking pages, guest loyalty self-service portal.
- Per-channel menu overrides (price, availability, prep time) for website, delivery apps, kiosk, and QR ordering without touching the master catalog.

## 5. Inventory & Supply Chain

- Real-time stock, multi-location stock, low-stock alerts, purchase orders, supplier management.
- **Recipe-costed inventory**: ingredients (raw materials in canonical units) separate from sellable products, with recipes driving automatic cost roll-up and stock deduction on every sale — not just a flat per-product stock count.
- **Measured/fractional stock** for items sold by weight or partial units.
- Stock transfers between locations (two-step in-transit → received, opt-in and additive — a single-location business never has to think about it).
- Stock takes with variance logging, waste/wastage tracking.
- Inventory anomaly detection.

## 6. CRM & Loyalty

- Full customer profiles, purchase history, VIP tagging, allergy/dietary notes surfaced automatically to booking and kitchen staff.
- **Loyalty 2.0**: membership tiers, category-weighted points multipliers (e.g. 2x on coffee), points-and-pay redemption, badges, milestones, and seasonal challenges.
- Gift cards and store credit as first-class loyalty tenders.
- A shared, phone-verified guest identity layer used by every guest-facing surface (not a separate "loyalty database" bolted on afterward).

## 7. Marketing

- Email marketing campaigns, club/member offers, social media post scheduling with **AI-generated content** from products/promos/specials.
- Autonomous marketing **daily digest** — an owner reviews and approves a day's worth of drafted campaigns in one pass instead of composing each individually.
- *Honesty note:* social platform publishing is intentionally mocked at the OAuth boundary in this build (real cross-posting needs per-platform business verification) — content generation, scheduling and preview are real; the final "post to Instagram" hop is a stub pending that verification.

## 8. Staff & Workforce

- Role-based access control (owner/manager/cashier/kitchen + granular permission overrides), PIN login for shared terminals, two-factor authentication.
- Clock in/out, break tracking, shift rostering, shift swaps, auto-rostering suggestions.
- Commission tracking, sales targets, staff performance leaderboard.
- **Australian payroll engine**: award-aware pay calculation, PAYG withholding, tiered Superannuation Guarantee contributions, Fair Work-compliant payslip PDFs, STP2-shaped pay-run events — sourced from and reconciled against the actual roster/timesheets, not a separate spreadsheet.

## 9. Accounting & Compliance

- Full **double-entry accounting**: chart of accounts, journals, ledger.
- **Automated BAS/GST quarterly filing** (10% GST) with mock and real ATO submission paths.
- Expense tracking, financial summaries, P&L statements.
- **Enterprise licensing**: ABN-bound tenant licenses verified against the Australian Business Register, Stripe-billing-driven subscription state machine, and **progressive lockout** (warn → restrict → block over days, never an instant shutdown) if a subscription lapses — a deliberate design choice so a billing hiccup never bricks a live venue mid-service.
- Universal audit log with before/after diffs and restore, across every entity type in the system (not just financial records).

## 10. Analytics, Forecasting & "AI GM" Features

- Real-time dashboard, sales/product/staff/customer analytics, custom report builder with CSV/PDF export.
- **Profit Guardian** — a nightly job comparing each product's trailing margin and unit velocity week-over-week, flagging thin-margin items with a suggested price move and calling out ones that are *also* losing volume (a different, worse problem than margin alone).
- **Digital twin forecasting**, labor demand forecasting, dynamic/surge pricing recommendations, menu A/B testing, cost coaching.
- Cohort retention analysis, "what-if" scenario simulator.

## 11. Multi-Location, Franchise & Enterprise

- Multi-business/multi-tenant architecture with per-request tenant scoping (`X-Business-Id`/`X-Location-Id`), not a bolted-on filter.
- **HQ/franchise roll-ups** across a brand's locations, multi-site command (publish/rollback config across sites), cross-store benchmarking.
- Location-scoped roles, consolidated and per-location reporting.

## 12. Ash — The Autonomous AI Operating Layer

This is the largest single differentiator from every mainstream POS, so it gets its own section.

Ash is not a chatbot bolted onto reports. It's a **typed tool-calling agent** with:
- A registry of every business action it's allowed to take (POS, inventory, customers, reservations, staff, marketing, finance), each tagged with a **risk level** (low/medium/high/critical) and a default permission (auto-execute / needs approval / disabled) that the *owner* configures per tool.
- An **approval queue** — anything above the owner's comfort threshold is proposed, not executed, and shows up for a human to approve or reject before anything happens.
- Sixteen-plus **deterministic insight generators** (not LLM guesses) that run continuously and surface actionable findings — stockouts, margin decline, staffing gaps, booking risk — with the LLM used only for the narrated weekly summary on top, not for the underlying math.
- A full **audit trail of every autonomous decision**, reversible where the action supports it (rollback functions are part of the tool contract, not an afterthought).
- Extends into voice: the same reasoning layer answers inbound booking calls and can place outbound confirmation/no-show-recovery calls.

## 13. Reliability & Offline

- Offline transaction queue with automatic sync-on-reconnect, visible to staff as a small "N sales queued" banner rather than a silent risk.
- Held-sale protection around hosted checkout redirects (§1) — a class of data-loss bug that exists in most POS systems using redirect-based card processors and is fixed here specifically.
- Device/hardware health monitoring, structured backend error logging with a recent-errors view for owners (not just server logs nobody reads).

## 14. Integrations

**Live and code-verified in this build:**
Stripe (checkout, webhooks, refunds), Coinbase Commerce (crypto), Twilio (SMS + voice, inbound and outbound), SendGrid (email), Linkly/Tyro/Smartpay/Windcave (EFTPOS terminals), fairwork.gov.au award-rate sync (with an offline seed fallback).

**Plugin-architected, ready to wire up a credential for:** Xero/QuickBooks/MYOB (accounting sync), Shopify/WooCommerce (e-commerce), Uber Eats/DoorDash (delivery), MailChimp (email).

Being explicit about the difference matters — a feature list that doesn't distinguish "shipped" from "stubbed" isn't one you can trust when it matters (payroll, GST, a live payment).

---

## How NUA Is Different From the Top 5 POS Providers

The "top 5" compared here — **Square, Toast, Clover, Lightspeed Restaurant, and TouchBistro** — are the platforms most hospitality and retail venues actually shortlist. All five are mature, well-built, capable systems. NUA doesn't try to out-feature them at the checkout screen (that's table stakes and NUA matches it); the real difference is in three areas none of them meaningfully address:

| Capability | Square | Toast | Clover | Lightspeed Restaurant | TouchBistro | **NUA POS** |
|---|---|---|---|---|---|---|
| Core checkout, modifiers, tabs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Kitchen Display System | ✅ (add-on) | ✅ | ✅ (add-on) | ✅ | ✅ | ✅ |
| Floor plan + course timing | Partial | ✅ | Partial | ✅ | ✅ | ✅ |
| **Guest self-service bill splitting (per-item, phone-verified, real-time)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Booking-size tiers / large-party rules enforced server-side across every channel** | ❌ | ❌ | ❌ | Partial (basic party caps) | ❌ | ✅ |
| **Auto-held sale if a card redirect is abandoned** | N/A (in-app tap) | N/A (in-app tap) | N/A (in-app tap) | N/A (in-app tap) | N/A (in-app tap) | ✅ (needed because NUA also supports redirect-based/crypto checkout) |
| **AI phone agent — answers and places real calls** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Autonomous agent with owner-configurable risk/approval per action** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Crypto payments** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Built-in payroll with award/Super compliance (AU) | ❌ (Square Payroll is US-only) | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Built-in GST/BAS filing (AU)** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Double-entry accounting ledger built in | ❌ (exports to accounting software) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Open, self-hosted / source-available architecture | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Franchise/HQ multi-brand roll-up | Enterprise tier only | Enterprise tier only | Limited | ✅ | Limited | ✅ |
| Recipe-costed inventory (ingredient-level, not just product stock) | Add-on | Partial | ❌ | ✅ | Partial | ✅ |

**In plain terms:**

- **Square, Clover, Toast, TouchBistro, and Lightspeed are transaction-first platforms** with reporting, loyalty and marketing layered on top and third-party apps for the rest. They're excellent at what they were built for: fast, reliable in-person checkout with a broad hardware and payments ecosystem. NUA matches that layer feature-for-feature.
- **None of them let a table full of guests split and pay their own share from their own phones without staff mediation** — the closest any come is a staff-driven "split by number of ways" at the register. NUA's bill-split is guest-initiated, per-item, phone-verified, and settles in real time.
- **None of them enforce a booking-size policy as a real rule** ("parties of 7+ need our set menu, and can't get past the booking form without it") server-side, identically for the website and the phone desk. At best it's a manual note a host has to remember.
- **None of them ship an autonomous operating agent** with a typed, risk-tiered tool catalog and an approval queue. Their "AI" features (where they exist at all) are analytics summarization, not an agent that can *act* — order stock, adjust a price, draft a campaign — within owner-set guardrails.
- **None of them are built for Australian statutory compliance** (BAS/GST, Fair Work awards, Superannuation Guarantee) as a native, first-party feature — Australian venues on those platforms export to Xero/MYOB and do compliance there. NUA does it in the same system that took the sale.
- **NUA accepts crypto out of the box.** None of the five do.
- **NUA is source-available and self-hostable.** The other five are closed SaaS platforms — you rent the software and your data lives in their cloud on their terms. A venue running NUA can inspect, modify, and host it themselves.

**Where the top 5 still lead today:** hardware ecosystem breadth and physical retail footprint (Square's card readers are everywhere; Clover has the widest third-party app marketplace), multi-year production hardening at very large scale, and — for now — live, OAuth-verified social media publishing and a wider roster of live BNPL/buy-now-pay-later processors, which in NUA are plugin-ready but not yet wired to real merchant credentials in this build.

---

*Generated from a direct audit of the codebase — every capability listed above corresponds to real, running code, not a roadmap intention. Where a feature is a deliberate stub (e.g. social-post publishing, BNPL providers), that's stated explicitly rather than counted as shipped.*
