# NUA — Mission & Product Vision

**One-line pitch**: NUA is an *AI-powered Hospitality Operating System*, not a POS.

---

## Product Principles

1. **Single Source of Truth** — every module (POS, Reservations, Kitchen, Payroll, Accounting, Inventory, CRM, Marketing) reads and writes to one shared customer, product, ingredient, staff, and financial database.
2. **Total Traceability** — every action (human or AI) writes an immutable audit event: who, when, from what device, from what IP, at what location, on which business. Every entity has full version history and can be restored to any prior state.
3. **AI Recommends → Owner Approves → System Automates** — Ash never performs high-risk actions (large POs, refunds, tier downgrades, mass discounts) without an owner's explicit approval. Low-risk actions (dock notifications, notifications, minor stock updates) can be fully automated.
4. **Multi-site by design** — every record is tagged with `businessId` + `locationId`. Franchises (brand → franchisee → location) are first-class citizens. HQ dashboards roll up across the network.
5. **Right to be forgotten** — soft-delete first; hard-delete is an owner action that also purges audit/version history for GDPR compliance.

---

## Universal Entity Model

Every top-level entity in NUA extends `BaseEntity`:

| Field | Purpose |
|-------|---------|
| `id` | UUID v4 |
| `businessId` | Tenant / brand |
| `locationId` | Physical outlet (nullable for HQ-level entities) |
| `createdBy` | User email or `system:<subsystem>` |
| `createdAt` | ISO-8601 UTC |
| `updatedBy` | User email or `system:<subsystem>` |
| `updatedAt` | ISO-8601 UTC |
| `deletedAt` | Soft-delete tombstone |
| `deletedBy` | Who soft-deleted |
| `device` | Client User-Agent snapshot |
| `ip` | Request IP |
| `version` | Monotonic counter — bumped on every update |

Tracked entity kinds:
`customer, product, ingredient, recipe, supplier, purchase_order, booking, table, employee, device, kitchen_ticket, voucher, wallet, loyalty_transaction, payment, refund, journal_entry, bill, invoice, rule, audit_event`

---

## Ash — the Autonomous Operating Layer

Ash is NUA's onboard intelligence. It is **always-on, read-first, action-second**, and consists of sixteen continuous jobs:

| # | Responsibility | Signal source |
|---|----------------|---------------|
| 1 | Predict staffing shortages | Roster vs. forecasted covers |
| 2 | Detect theft | Comp/void patterns, refund anomalies |
| 3 | Detect fraud | Card mismatches, refund velocity |
| 4 | Recommend pricing | Margin decay, competitor price feeds |
| 5 | Suggest promotions | Slow-moving inventory, weather |
| 6 | Predict food waste | Recipe pull rate vs. stock aging |
| 7 | Detect unusual labour costs | Wages ÷ revenue by shift |
| 8 | Detect menu underperformance | Menu Engineering matrix drift |
| 9 | Forecast weather impact | Weather API × historical cover swings |
| 10 | Forecast public holiday demand | Calendar × 3-year same-day baseline |
| 11 | Recommend purchasing | Par levels, lead time, forecast |
| 12 | Recommend roster changes | Sales forecast vs. rostered hours |
| 13 | Predict staff burnout | Overtime streaks, clock-in trends |
| 14 | Predict customer churn | Days-since-visit vs. tier norm |
| 15 | Recommend menu engineering | Star / Puzzle / Plow-Horse / Dog quadrants |
| 16 | Auto-write weekly business summary | LLM narrative over the week's KPIs |

Every Ash insight lands in `db.ash_insights` with a `severity`, `recommendedActions[]` and (if applicable) a link into the Approval Queue.

---

## Approval Queue

- Any action Ash or a rule wants to take that meets a policy threshold is enqueued in `db.approvals` instead of firing directly.
- Default thresholds (env-configurable):
  - `AI_APPROVE_PO_ABOVE=500` — POs over $500
  - `AI_APPROVE_REFUND_ABOVE=100` — refunds over $100
  - `AI_APPROVE_TIER_DOWNGRADES=1` — any downgrade
  - `AI_APPROVAL_MODE=thresholds|strict|off` — strict = approve everything AI does
- Owners see pending approvals at `/approvals`.

---

## Multi-site / Franchise

- `businesses` collection gains `parentBrandId`.
- HQ dashboard at `/hq` — cross-location KPIs, rankings, benchmarks.
- Every mutation carries `X-Business-Id` + `X-Location-Id` headers.
- Location-scoped queries filter by `locationId` automatically.

---

*Last updated: 9 Feb 2026*
