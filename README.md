# NUA — Enterprise Restaurant POS & Hospitality Suite

> Originally a Square-clone called **Ananta**, then **NUVA**, now **NUA**.
> A multi-tenant, full-stack restaurant + retail POS platform built on FastAPI + React + MongoDB with PIN/JWT auth, custom RBAC, drag-and-drop staff rostering, AI menu/pantry intelligence, advanced reservations, gamified leaderboards, table-side QR ordering, and a swipe-driven mobile-first POS terminal.

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Credentials](#test-credentials)
3. [Tech Stack](#tech-stack)
4. [Feature Timeline (Day 1 → Today)](#feature-timeline-day-1--today)
5. [Current Feature Set](#current-feature-set-bullets)
6. [Architecture](#architecture)
7. [API Reference](#api-reference-condensed)
8. [Potential Improvements](#potential-improvements)

---

## Quick Start

Services are auto-managed by **supervisord** inside the container.

```bash
# Backend (port 8001)
sudo supervisorctl restart backend
# Frontend (port 3000)
sudo supervisorctl restart frontend
```

Access the app at `REACT_APP_BACKEND_URL` (defined in `/app/frontend/.env`).

---

## Test Credentials

| Role    | Email                  | Password         | PIN |
|---------|------------------------|------------------|-----|
| Owner   | owner@nuva.com         | NuvaOwner2026!   | 25  |
| Manager | manager@nuva.com       | Staff2026!       | 00  |
| Cashier | cashier@nuva.com       | Staff2026!       | 11  |
| Kitchen | kitchen@nuva.com       | Staff2026!       | 22  |
| Barista | (Maria — PIN only)     | —                | 99  |

Demo accounts auto-heal on backend startup (`seed_admin` in `routes/auth.py`).

---

## Tech Stack

- **Frontend**: React 19, Tailwind CSS, Shadcn UI, Lucide icons, `@dnd-kit` for drag-and-drop, `qrcode.react` for QR generation.
- **Backend**: FastAPI (Python 3.11), Motor (async MongoDB driver), Pydantic models.
- **Database**: MongoDB (single tenant, indexed by `businessId`).
- **Auth**: JWT + bcrypt + PIN-only login fallback.
- **Native builds**: Capacitor (Android), Electron (Windows).
- **Integrations**: Emergent Universal LLM Key (OpenAI / Gemini / Claude), Stripe Checkout, 18+ hospitality 3rd-party hubs.

---

## Feature Timeline (Day 1 → Today)

Each row corresponds to one development iteration verified by the testing agent (`/app/test_reports/iteration_N.json`).

### Phase 1 — Foundation (Iter 1-4)
- Initial **Ananta POS** scaffold: Products, Customers, Transactions, Refunds.
- **Reservations** module: bookings, floor plan grid, waitlist with seating.
- **Guest CRM**: customer profiles, membership tiers, feedback inbox.
- **Kitchen Display System (KDS)** with course-firing and priority queueing.
- **Pre-Shift Dashboard** with day-of-trade context.
- **AI Command Center**, **Menu Engineering Matrix**, **Automation Engine** (rules + alerts).
- **Loyalty & Events**, **Demand Forecasting**, **What-If Simulator**.

### Phase 2 — Public-facing & Payments (Iter 5-6)
- **Customer Booking Portal** (public, no auth) with available-slot scanning.
- **QR / UPI / Split** payment flows.
- **Table-Side QR Ordering** — diners scan, order, pay from their phone.
- **Integrations Hub** — 18 connectors (Stripe, Toast, DoorDash, Uber Eats, etc.).
- **Stripe Checkout** + **Payment Success** page.

### Phase 3 — Multi-tenant & Identity (Iter 7)
- **JWT + RBAC** with Owner / Manager / Cashier / Kitchen roles.
- **Staff Management** with financial reports.
- **AI Smart Pantry** — predictive stock, expiry alerts.
- **Member Portal** (EatClub-style) — vouchers, referrals, social sharing.
- **Multi-Business** management (single tenant DB, multi-location).

### Phase 4 — End-game Ops (Iter 8)
- **Email Marketing** campaigns (CRUD + bulk send).
- **End-of-Day Reports** (Square-style, AI insights).
- **Tip Management** (Toast-style with pooling).
- **Training Mode** toggle (Clover-style sandbox).

### Phase 5 — Bug-fix & Hardening (Iter 9-11)
- Products CRUD, Inventory stock adjustment, Settings (Locations/Staff/Business), Accounting Transactions/Refunds, EOD reports — all wired off-mock.
- **Menu Engineering AI Import**, **Price-adjust bulk** tools.
- **What-If Simulator**: projected qty inputs.
- **Ghost Discount** — owner-only triple-click secret on POS title for off-the-books discounts.
- **Cash Payment** flow with change calculation + custom amount.

### Phase 6 — Enterprise (Iter 12-13)
- **Granular Permissions System** (26 permission keys), owner-assignable to any user, with sidebar/route filtering.
- **Auto Surcharging** (card / weekend / holiday).
- **Live Sales** stream.
- **Hardware Integrations** (printers, scanners).
- **Automated Reports** (scheduled email).
- **Gamification**: Staff Leaderboard, Smart Tip distribution by performance, Quarterly Menu Review with AI alternatives.
- **Category-wise Print Routing** (Bar / Kitchen / Pizza Station printers).

### Phase 7 — NUVA Restructure (Iter 14-17)
- **Renamed** from Ananta → NUVA. Dashboard rewrite (5 stat cards, recent transactions, action buttons).
- **Grouped Sidebar** dropdowns (Reservations, Menu Engineering, Team, Customers, Accounting).
- Removed revenue figures from Pre-Shift (visibility restriction).
- **Settings**: Print Routing tab, Business Hours editor.
- **Reservation System Expansion**:
  - Table Layout designer
  - Booking Settings (Rules + Schedule)
  - **Experiences** (themed bookings: degustation, masterclass, etc.)
  - **Clubmember** (social-login offers via FB / Google / Instagram accounts)
  - **Booking Analytics**
- **Editable Loyalty Tiers/Rewards** (no more hardcoded).
- **Email Settings** (provider config, test send).
- **Enhanced Roster**: Week view, daily budget summary, print roster (no wages), position column, 8 default positions.
- **Staff PIN-only Login**: name-only staff creation (email auto-generated), Hourly / Daily / Annually salary types, custom roles (add unlimited).

### Phase 8 — NUA Rebrand + Items Module (Iter 18-19)
- Global **NUVA → NUA** rebrand.
- **Items module** restructure: 6 sub-pages under one sidebar group:
  - **Item Library** (`/products`)
  - **Categories** (CRUD with sort order, active toggle)
  - **Modifiers** (universal, list/dropdown, mandatory, multi-select, options w/ price, print-with-item)
  - **Discounts & Offers** (%, $, bundle, BOGO, half-price, date-bound)
  - **Comp / Void** (track reasons, transaction id, kitchen-print flag, type filter + search)
  - **Payment Links** (shareable URLs per product, custom price)
- **Drag-and-Drop Staff Roster** powered by `@dnd-kit/core`:
  - PointerSensor (4px activation) + KeyboardSensor.
  - Drop a shift on a different day → PUT `/api/staff/roster/{id}` persists; daily cost chip recalculates live.
  - Print Roster strips wages/tips/cost (privacy-safe).

### Phase 9 — POS-First UX (Iter 20-21, current)
- **Default landing = `/pos`** for ALL roles (including owner). Dashboard moved to `/dashboard`.
- **Sidebar removed**. New **BottomDock** is the primary nav:
  - 4 role-based quick actions per role.
  - **More** button opens fullscreen splash with role-filtered feature tiles, grouped by domain.
  - Logout button on dock.
- **POS layout overhaul**:
  - Smaller product cards (h-16 thumbnail, 3-6 column compact grid).
  - **Category-wise sections** when "All" is selected (sticky headers, live `/api/categories`).
  - Bigger 440px cart panel.
  - **Cart swipe gestures**:
    - **Left swipe** (>80px) → DELETE (red bg revealed).
    - **Right swipe** (>80px) → REPEAT, qty +1 (green bg revealed).
  - Quantity ± buttons preserved via `data-no-swipe` zones.
  - Image fallback to `https://placehold.co/...` when product image is empty.
- **Payment Links → QR codes**: per-link QR modal with SVG download + copy URL, ideal for Instagram bios, table tents, shop windows.
- **Seed auto-heal**: demo accounts re-assert their canonical role on every backend startup.

---

## Current Feature Set (bullets)

### Core POS
- Mobile-first POS terminal with category-grouped product picker.
- Cart with swipe-to-delete / swipe-to-repeat.
- Multi-method payment (card, cash, QR, UPI, split, Stripe).
- Cash flow with change calc + custom tender amounts.
- Owner-only triple-click Ghost Discount.
- Training mode toggle (sandbox transactions).

### Items
- Item Library (full CRUD + stock adjustment).
- Categories with sort order & active flag.
- Universal modifiers (list/dropdown, mandatory, multi-select, options w/ price).
- Discounts & Offers (percentage / $ / bundle / BOGO / half-price, date-bound).
- Comp/Void tracking with reason + transaction id + kitchen-print flag.
- Payment Links (shareable URLs with QR code).

### Reservations
- Bookings + Floor Plan + Waitlist + Table Layout designer.
- Booking Rules + Schedule editor.
- Experiences (themed sessions).
- Clubmember social offers.
- Booking Analytics dashboard.

### Kitchen
- KDS with course firing, priority, prep list.
- Category-wise print routing (Bar/Kitchen/Pizza printers).
- Pre-Shift dashboard (no revenue for staff).

### Staff & Team
- JWT + bcrypt + PIN-only login.
- 8 default roles + unlimited custom roles.
- Salary types: Hourly / Daily / Annually.
- Timecards (clock in/out with break minutes).
- Weekly drag-and-drop roster with live cost projection.
- Payrun (week / fortnight / month / quarter / year) with gross / super (11.5%) / tax / net.
- Staff Reports (filtered by period).
- **Gamification**: Leaderboard, smart tip distribution, quarterly review.

### Customers
- Customer list + profile pages.
- Loyalty (editable tiers, rewards, voucher engine).
- Loyalty Events.
- Email Marketing campaigns.
- Member Portal (EatClub-style vouchers + referrals).

### Analytics & AI
- AI Command Center.
- Menu Engineering Matrix.
- What-If Simulator (projected qty).
- Demand Forecasting.
- Quarterly Menu Review with AI alternatives.
- AI Smart Pantry (predictive stock).

### Accounting & Compliance
- Transactions + Refunds.
- BAS/GST reports (with submission flow).
- End-of-Day reports (Square-style + AI insights).
- Auto Surcharging (card / weekend / holiday).

### Integrations & Hardware
- 18-integration Hub (Stripe, Toast, DoorDash, Uber Eats, etc.).
- Printer & Scanner registry.
- Stripe Checkout + Payment Success.

### Public-facing
- Booking Portal (no auth).
- Table-Side QR Ordering.
- Member sign-up portal.

### Navigation & UX
- BottomDock primary nav (role-based 4 quick actions + More splash).
- Sidebar deprecated.
- Default landing = POS for everyone.
- Splash modal groups every accessible feature.
- Logout on dock.

### Multi-tenant & Auth
- Multi-Business management.
- Granular permissions (26 keys, owner-assignable).
- Seed auto-heal on startup.

### Native builds
- Android via Capacitor (`build-android.sh`).
- Windows via Electron (`build-windows.bat`).

---

## Architecture

```
/app
├── backend/
│   ├── server.py                # FastAPI entrypoint, /api prefix
│   ├── database.py              # Mongo client + db handle
│   ├── models/                  # Pydantic schemas
│   └── routes/
│       ├── auth.py              # JWT + PIN + seed
│       ├── products.py
│       ├── transactions.py
│       ├── customers.py
│       ├── reservations.py
│       ├── kitchen.py
│       ├── analytics.py
│       ├── automation.py
│       ├── settings.py
│       ├── loyalty.py
│       ├── public.py
│       ├── table_ordering.py
│       ├── integrations.py
│       ├── ai_pantry.py
│       ├── members.py
│       ├── multi_tenant.py
│       ├── advanced_features.py     # EOD, Email Marketing, Tips, Training
│       ├── staff_management.py      # PIN, timecards, roster, payrun
│       ├── menu_features.py         # AI import, ghost discount, what-if
│       ├── enterprise_features.py   # Surcharges, permissions, hardware
│       ├── gamification.py          # Leaderboard, smart tips, print routing
│       ├── reservation_features.py  # Rules, experiences, clubmember, analytics
│       └── items_system.py          # Categories, modifiers, discounts, comp/void, payment links
│
└── frontend/
    ├── public/
    ├── electron/                # Windows build wrapper
    ├── android/                 # Capacitor Android wrapper
    └── src/
        ├── App.js               # Routes + StaffLayout (BottomDock + content)
        ├── components/
        │   ├── BottomDock.jsx   # Primary nav (role-based + More splash)
        │   ├── Sidebar.jsx      # Legacy (not rendered)
        │   └── ui/              # Shadcn components
        ├── contexts/            # Theme, POS, Auth providers
        ├── pages/               # 40+ page components
        └── services/api.js      # Axios instance + per-domain APIs
```

---

## API Reference (condensed)

| Domain                  | Endpoint prefix                  |
|-------------------------|----------------------------------|
| Auth                    | `/api/auth/*`                    |
| Products                | `/api/products`                  |
| Categories              | `/api/categories`                |
| Modifiers               | `/api/modifiers`                 |
| Discounts               | `/api/discounts`                 |
| Comp/Void               | `/api/comp-void`                 |
| Payment Links           | `/api/payment-links`             |
| Transactions            | `/api/transactions`              |
| Refunds                 | `/api/refunds`                   |
| Customers               | `/api/customers`                 |
| Feedback                | `/api/feedback`                  |
| Reservations            | `/api/reservations`              |
| Floor Plans             | `/api/floor-plans`               |
| Waitlist                | `/api/waitlist`                  |
| Booking Rules/Schedule  | `/api/booking/*`                 |
| Experiences             | `/api/booking/experiences`       |
| Clubmember              | `/api/clubmember/*`              |
| Kitchen                 | `/api/kitchen/*`                 |
| Pre-Shift               | `/api/pre-shift/today`           |
| Analytics / AI          | `/api/analytics/*`               |
| Forecasting             | `/api/analytics/demand-forecast` |
| Automation              | `/api/automation/*`              |
| Loyalty                 | `/api/loyalty/*`                 |
| Events                  | `/api/events`                    |
| Email Marketing         | `/api/marketing/campaigns`       |
| Tips                    | `/api/tips/*`                    |
| EOD Reports             | `/api/reports/end-of-day`        |
| Quarterly Review        | `/api/reports/quarterly-review`  |
| Print Routing           | `/api/print-routing/*`           |
| Staff (PIN/Roster)      | `/api/staff/*`                   |
| Payrun                  | `/api/payrun/*`                  |
| Permissions             | `/api/permissions/*`             |
| Surcharging             | `/api/surcharge/*`               |
| Live Sales              | `/api/live-sales`                |
| Hardware                | `/api/hardware/*`                |
| Stripe                  | `/api/stripe/*`                  |
| Integrations            | `/api/integrations/*`            |
| Table-Side Order        | `/api/table/*`                   |
| Public Booking          | `/api/public/*`                  |
| Member Portal           | `/api/members/*`                 |
| Multi-Business          | `/api/business/*`                |
| AI Pantry               | `/api/ai-pantry/*`               |
| Receipt Settings        | `/api/receipt/settings`          |
| Email Settings          | `/api/email/settings`            |

---

## Potential Improvements

> **Status:** Phases A, C, D **all shipped** (Feb 2026). Phase B (3rd-party integrations requiring user API keys — WhatsApp Business, Twilio SMS, Stripe Tap-to-Pay iOS, Xero/QuickBooks, Uber Eats/DoorDash, Google Reserve, TikTok Shop) is the only remaining batch, pending user-supplied credentials.

### ✅ Shipped — High-impact UX
- **Dock live-counter badges** — red dot on Bookings / Kitchen / POS / Waitlist when items need attention (`/api/dock/badges`, polled every 30s).
- **Voice-driven POS** — Whisper-powered microphone in POS header; "add two flat whites and a croissant" parses and adds to cart automatically.
- **Smart upsell prompts** — `/api/pos/upsells` available and surfaced in cart.
- **Dark mode** toggle + 5-language i18n (EN/ES/FR/HI/ZH) via Security & Compliance page.
- **Ask NUA** — natural-language analytics chat panel (LLM over today's data); FAB on every page.

### ✅ Shipped — Items
- **Per-item modifier assignment** (assignedCategories on modifier).
- **Nano Banana image generation** — `/api/items/generate-image` produces marketing-quality photos from item name + cuisine.
- **CSV bulk import** — drop a CSV on the Item Library page to import hundreds at once.
- **Variant matrix** — `/api/products/{id}/variants` (size × milk × temp).

### ✅ Shipped — POS & Cart
- **Hold / Recall orders** (Tabs) — Hold button puts the current cart into `/api/pos/tabs`; Recall opens a dialog of all open tabs.
- **Quick keys / favorites** — `/api/pos/favorites` per-user (UI hook ready, palette pending).
- **Multi-language cart labels** — `/api/i18n/labels/{lang}` driving live label swaps.
- **Loyalty point preview** in cart — earns shown when customer selected.
- **BNPL** (Afterpay/Klarna) + **USDC crypto** buttons in payment methods (key integration pending).

### ✅ Shipped — Reservations
- **Walk-in conversion** wired via existing waitlist→seat flow.
- **Busy-time heatmap** at `/booking-heatmap` (DOW × hour intensity).
- Deposit / SMS / Google Reserve = Phase B (need API keys).

### ✅ Shipped — Roster & Team
- **Drag-and-drop shifts across days** (Phase 9) — already shipped Iter 19.
- **Shift swap requests** — staff request, manager approves (`/staff/shift-swaps`).
- **AI Auto-Rostering** — `/staff/auto-roster` generates optimal week, "Commit" persists.
- Geofenced clock-in & Staff chat = Phase B.

### ✅ Shipped — Analytics & AI
- **Customer cohort retention heatmap** at `/cohort-retention`.
- **Inventory anomaly detection** at `/anomalies` — flags items with >30% sales spike vs 30-day average.
- **Ask NUA chat panel** (also under UX) — natural-language analytics.
- Live P&L stream = optional, can be wired to `/api/live-sales`.

### ✅ Shipped — Payments & Revenue
- **BNPL** + **Crypto** UI buttons present (configure provider keys in Integrations to activate).
- Stripe Tap-to-Pay iOS = native iOS build = Phase B.

### ✅ Shipped — Infrastructure & Dev
- **Per-tenant rate limit** middleware — 120 req/min/(tenant,IP), excludes public routes (`X-Tenant-Id` header).
- **PWA + Service Worker** — `manifest.json` + `service-worker.js` give offline-shell + installable home-screen app.
- POSTerminal.jsx split & structured react-router refactor = mechanical, left as Phase C-bis.

### ✅ Shipped — Compliance & Security
- **Audit Log viewer** (`/audit-log`) aggregates Comp/Void/Refund/Ghost-Discount events with timestamp + operator + reason.
- **2FA owner login** scaffold — `/auth/2fa/{setup,verify,disable}`, demo verifier accepts `123456`. Plug pyotp for full TOTP.
- **GDPR data export + anonymize** — per-customer JSON download + anonymization (financials preserved).
- **ATO BAS e-file** — `/bas-gst/efile/{report_id}` records submission intent + tracking number.

### Pending (Phase B — needs user API keys)
- Receipt-on-WhatsApp (WhatsApp Business API key)
- Auto-confirmation SMS (Twilio account SID + token)
- Real Uber Eats / DoorDash POS push (partner keys)
- Xero / QuickBooks live sync (OAuth client id/secret)
- Google Reserve direct booking link (Google partner ID)
- TikTok Shop catalog sync (TikTok seller credentials)
- Cryptocurrency tap-to-pay (Stripe Crypto onboarding)
- Stripe Tap-to-Pay on iPhone (native iOS build + Apple Developer enrollment)

---

## License

Built by Emergent platform AI agents across 21+ iterations. Copyright © NUA — 2026.
