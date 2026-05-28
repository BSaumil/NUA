# NUA — Enterprise Restaurant POS & Hospitality Suite

> Originally **Ananta** → **NUVA** → **NUA**. Multi-tenant FastAPI + React + MongoDB POS platform with PIN/JWT auth, custom RBAC, drag-and-drop rostering, autonomous AI agent (Ash), Whisper voice POS, swipe-based mobile cart, category-multiplied loyalty, AI menu/pantry intelligence, advanced reservations, gamified leaderboards, table-side QR ordering, BNPL/crypto payments, GDPR-grade compliance, PWA-offline, multi-language.

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Credentials](#credentials)
3. [Tech Stack](#tech-stack)
4. [Feature Timeline (Day 1 → v17)](#feature-timeline-day-1--v17)
5. [Current Feature Set](#current-feature-set)
6. [Loyalty Engine](#loyalty-engine)
7. [Ash — Autonomous AI Agent](#ash--autonomous-ai-agent)
8. [Voice Commands](#voice-commands-everywhere)
9. [Architecture](#architecture)
10. [API Reference](#api-reference-condensed)
11. [Potential Improvements](#potential-improvements)

---

## Quick Start
```bash
sudo supervisorctl restart backend    # port 8001
sudo supervisorctl restart frontend   # port 3000
```
Access at `REACT_APP_BACKEND_URL` (in `/app/frontend/.env`).

## Credentials

| Role    | Email                | Password         | PIN | 2FA demo |
|---------|----------------------|------------------|-----|----------|
| Owner   | owner@nuva.com       | NuvaOwner2026!   | 25  | 123456   |
| Manager | manager@nuva.com     | Staff2026!       | 00  | —        |
| Cashier | cashier@nuva.com     | Staff2026!       | 11  | —        |
| Kitchen | kitchen@nuva.com     | Staff2026!       | 22  | —        |
| Barista | Maria (PIN only)     | —                | 99  | —        |

Seed roles auto-heal on every backend startup.

---

## Tech Stack
- React 19, Tailwind, Shadcn UI, Lucide, `@dnd-kit`, `qrcode.react`
- FastAPI (Python 3.11), Motor async MongoDB driver
- MongoDB
- JWT + bcrypt + PIN + (scaffolded) TOTP 2FA
- Capacitor (Android) + Electron (Windows) + PWA (browser/iOS)
- **Emergent Universal LLM Key** → GPT-5.2 (Ask NUA, voice intent), Whisper (voice POS), Nano Banana (item image gen)
- Stripe Checkout · 18-integration hub

---

## Feature Timeline (Day 1 → v17)

### Phase 1 — Foundation (Iter 1-4)
- POS scaffold: Products, Customers, Transactions, Refunds
- Reservations, Floor Plan, Waitlist
- Guest CRM, Feedback inbox
- Kitchen Display System
- Pre-Shift Dashboard
- AI Command Center, Menu Engineering Matrix, Automation
- Loyalty/Events, Demand Forecasting, What-If Simulator

### Phase 2 — Public + Payments (Iter 5-6)
- Public booking portal, Table-side QR ordering
- 18-integration hub (Stripe/Toast/DoorDash/Uber Eats...)
- Stripe Checkout + Payment Success

### Phase 3 — Multi-tenant + Identity (Iter 7)
- JWT + RBAC (owner/manager/cashier/kitchen)
- Staff Management + Financial Reports
- AI Smart Pantry
- Member Portal (EatClub-style)
- Multi-Business

### Phase 4 — Endgame Ops (Iter 8)
- Email Marketing campaigns
- End-of-Day reports (AI insights)
- Tip Management (Toast-style pooling)
- Training Mode (Clover-style sandbox)

### Phase 5 — Bug-fix + Hardening (Iter 9-11)
- All mocked pages wired live (Products/Settings/Accounting/EOD)
- Menu Engineering AI import, Bulk price adjust
- What-If projected qty inputs
- Ghost Discount (owner triple-click secret)
- Cash payment with change calc

### Phase 6 — Enterprise (Iter 12-13)
- 26-key granular Permissions system
- Auto Surcharging (card/weekend/holiday)
- Live Sales stream
- Hardware integrations (printers/scanners)
- Scheduled report email
- Gamification: Leaderboard, Smart Tip distribution, Quarterly review
- Category-wise print routing (Bar/Kitchen/Pizza)

### Phase 7 — NUVA Restructure (Iter 14-17)
- Ananta → NUVA rebrand; dashboard rewrite
- Grouped sidebar dropdowns
- Pre-Shift revenue restriction for staff
- Print Routing + Business Hours editor
- Reservation expansion: Table Layout · Settings · **Experiences** · **Clubmember** · **Booking Analytics**
- Editable Loyalty Tiers/Rewards
- Email Settings
- Week-view Roster, daily/weekly budget, print-roster (no wages), 8 default positions
- Staff PIN-only login, Hourly/Daily/Annually salary types, unlimited custom roles

### Phase 8 — NUA + Items Module (Iter 18-19)
- Global NUVA → NUA rebrand
- 6-page Items module:
  - Item Library · Categories · Modifiers · Discounts & Offers · Comp/Void · Payment Links
- Drag-and-Drop Roster (`@dnd-kit`): drop shift across days, daily cost recalcs live

### Phase 9 — POS-First UX (Iter 20-21)
- Default landing = `/pos` for everyone
- Sidebar removed → BottomDock primary nav
- 4 role-based quick actions + More splash
- POS overhaul: smaller cards, category-wise sections
- Bigger 440px cart with **swipe-to-delete** / **swipe-to-repeat**
- Payment Link QR-code modal + SVG download

### Phase 10 — Mega-Drop A·C·D (Iter 22)
**A. UX:** Dock live-badges, Voice POS (Whisper), Ask NUA chat (GPT-5.2), Dark mode, 5-lang i18n, Hold/Recall Tabs, Loyalty preview chip, BNPL/Crypto pay buttons
**A. Items:** CSV bulk-import, Nano Banana image gen, Variant matrix, Per-item modifier ID
**A. Reservations:** Busy-time heatmap (DOW × hour)
**A. Roster:** AI Auto-Roster, Shift Swap requests + manager approve/reject
**A. AI:** Inventory anomaly detector (sales velocity spike), Customer Cohort Retention
**C. Infra:** Per-tenant rate limiter (120/min/IP), PWA + Service Worker
**D. Compliance:** Audit Log viewer · 2FA scaffold · GDPR export+anonymize · ATO BAS e-file

### Phase 11 — Loyalty + Autonomous Agent + Voice-Everywhere (Iter 23, this build)
- **Category-multiplied Loyalty Engine**
  - $1 spend = 1 base point · 1 point = $0.01 redeem value · min 50 pts to redeem
  - Owner-configurable category multipliers (Beverages 2x, Bakery 1.5x, …)
  - Points-and-Pay in POS cart with "All" shortcut
  - Immutable ledger (`loyalty_ledger`) + idempotent per-transaction credit
- **Ash — Autonomous AI Agent** (`/agent`)
  - Auto-segments customers (VIP / Regular / At-Risk / First-Timer)
  - Auto-flags 60-day-dormant customers
  - Auto-generates birthday vouchers (7-day window)
  - Auto low-stock reorder alerts
  - Auto inventory anomaly detection
  - Suggests SMS blasts to VIPs on low-booking nights
  - All decisions logged with audit trail + status badge
- **Voice Commands Everywhere**
  - Hold mic in POS → "Pay using points" / "Add 2 flat whites" / "Open dashboard"
  - GPT-5.2 classifies intent into: navigate / add_item / book_reservation / run_report / redeem_points / message_blast / agent_tick
  - Voice Catalog endpoint (`/agent/voice-catalog`) lists supported phrases per section

---

## Current Feature Set

### Core POS
- Mobile-first POS with category-grouped picker
- Swipe-to-delete / swipe-to-repeat cart
- Multi-method payment: card · cash · QR · UPI · split · Stripe · **BNPL** · **Crypto (USDC)**
- Cash change calc + custom tender
- Owner triple-click Ghost Discount
- Training Mode sandbox
- **Hold / Recall Tabs**
- **Voice ordering (Whisper)**
- **Points-and-Pay (min 50 pts, 1¢/pt)**
- **Multi-language labels (EN/ES/FR/HI/ZH)**
- **Loyalty earning preview chip in cart**

### Items
- Item Library CRUD + stock adjustment
- Categories with sort order & active flag
- Modifiers (list/dropdown, mandatory, multi-select, options w/ price)
- Discounts & Offers (% / $ / bundle / BOGO / half-price, date-bound)
- Comp/Void with reason + transaction-id + kitchen-print
- Payment Links + QR code modal + SVG download
- **CSV bulk import**
- **Nano Banana image generation**
- **Variant matrix (size × milk × temp)**

### Reservations
- Bookings + Floor Plan + Waitlist + Table Layout
- Rules + Schedule editor
- Experiences (themed sessions)
- Clubmember social offers
- Booking Analytics
- **Busy-time heatmap (DOW × hour)**

### Kitchen
- KDS with course firing, priority, prep list
- Category-wise print routing (Bar/Kitchen/Pizza)
- Pre-Shift dashboard (staff-safe, no revenue)

### Staff & Team
- JWT + bcrypt + PIN-only login + 2FA scaffold
- 8 default + unlimited custom roles
- Salary types: Hourly / Daily / Annually
- Timecards (clock in/out + break minutes)
- Week-view drag-and-drop roster, live cost projection
- **AI Auto-Rostering** (`/staff/auto-roster`)
- **Shift Swap requests** (`/staff/shift-swaps`)
- Payrun (week/fortnight/month/quarter/year) — gross/super/tax/net
- Staff Reports (filterable)
- Gamification: Leaderboard, Smart Tip, Quarterly Review

### Customers
- Customer list + profile pages
- **Category-multiplied Loyalty Engine** (owner-configurable)
- Editable Loyalty Tiers/Rewards
- Loyalty Events
- Email Marketing campaigns
- Member Portal (vouchers + referrals)
- **GDPR export + anonymize** (per Article 15/17)

### Analytics & AI
- **Ash autonomous agent dashboard** (`/agent`)
- AI Command Center
- Menu Engineering Matrix
- What-If Simulator
- Demand Forecasting
- Quarterly Menu Review w/ AI alternatives
- AI Smart Pantry
- **Inventory anomaly detection**
- **Customer cohort retention heatmap**
- **Ask NUA chat panel** (GPT-5.2 over real-time data)
- **Audit Log viewer**

### Accounting & Compliance
- Transactions + Refunds
- BAS/GST reports + **ATO e-file** with tracking number
- End-of-Day reports + AI insights
- Auto Surcharging

### Integrations & Hardware
- 18-integration hub
- Printer & Scanner registry
- Stripe Checkout

### Public-facing
- Booking Portal (no auth)
- Table-Side QR Ordering
- Member sign-up

### Navigation & UX
- BottomDock (live counter badges, More splash)
- Default to /pos for all roles
- **Dark mode toggle**
- **5-language i18n**
- **Per-tenant rate limit** (120 req/min)
- **PWA + Service Worker** (offline shell + installable)

### Multi-tenant & Auth
- Multi-Business management
- Granular permissions (26 keys)
- Seed auto-heal on startup

### Native builds
- Android via Capacitor (`build-android.sh`)
- Windows via Electron (`build-windows.bat`)

---

## Loyalty Engine

Owner-configurable at **`/loyalty-config`**:

| Rule              | Default | Configurable |
|-------------------|---------|--------------|
| Earn rate         | 1 pt/$1 | ✅           |
| Redeem value      | $0.01/pt| ✅           |
| Minimum redemption| 50 pts  | ✅           |
| Category multipliers | none | ✅ (e.g. Coffee 2x)|

**Flow at POS**:
1. Cashier selects customer → balance auto-loaded (e.g. ⭐ 240 pts)
2. If balance ≥ minRedeem, "Points & Pay" block appears in cart panel
3. Cashier types redemption (or taps "All") → discount applied live to total
4. On checkout: ledger records redemption first, then earns base points on net spend
5. Every credit is idempotent per transaction-id (no double-credit on retry)

**Math example**:
- Cart: 2× Latte ($5) + 1× Croissant ($4) = $14
- Multipliers: Beverages 2x, Bakery 1.5x
- Points earned: 10 × 1 × 2 = 20 (latte) + 4 × 1 × 1.5 = 6 (croissant) = **26 pts**

---

## Ash — Autonomous AI Agent

Visit **`/agent`** to see Ash in action.

**What Ash watches**:
- Customer behavior (last visit, total spend, total visits)
- Inventory stock levels
- Sales velocity (7-day vs 30-day baseline)
- Booking volume vs target
- Birthday calendar (next 7 days)

**Actions Ash can take**:
| Decision         | Trigger                                | Status      |
|------------------|----------------------------------------|-------------|
| At-Risk Flag     | No visit > 60 days                     | Executed    |
| Birthday Voucher | Birthday in next 7 days                | Executed    |
| Low-Stock Alert  | Product stock ≤ 5                      | Executed    |
| Anomaly Alert    | Sales velocity spike > 30%             | Executed    |
| Blast Suggestion | Bookings today < 5 → suggest VIP blast | Suggested   |

Every decision logged to `agent_decisions` with summary + payload + timestamp. Owner can drive cycles manually via "Run Cycle" or wire a cron.

---

## Voice Commands Everywhere

Mic icon in POS header. Behind the scenes:
1. Browser MediaRecorder → base64 audio
2. POST `/api/pos/voice-order` → OpenAI Whisper transcription
3. If matches product names → auto-add to cart
4. Otherwise → POST `/api/agent/voice-command` → GPT-5.2 classifies intent → instruction returned

**Example commands** (full catalog at `/api/agent/voice-catalog`):

| Section       | Example commands                                         |
|---------------|----------------------------------------------------------|
| **POS**       | "Add two flat whites and a croissant" · "Hold this order" · "Pay using points" · "Show tabs" |
| **Items**     | "Show items" · "Add new item Iced Latte $5.50 Beverages" · "Generate image for Avocado Toast" |
| **Reservations** | "Show today's bookings" · "Add booking for 4 at 7 PM" · "Open floor plan" |
| **Roster**    | "Show this week's roster" · "Run AI auto-roster" · "Approve all swap requests" |
| **Customers** | "Show VIP customers" · "Send tonight blast to at-risk" · "Export GDPR data for John" |
| **Reports**   | "Show today's revenue" · "Run end of day" · "Show inventory anomalies" |
| **Agent**     | "Run agent tick" · "Show recent decisions" · "Approve birthday vouchers" |

---

## Architecture

```
/app
├── backend/
│   ├── server.py                  # FastAPI entrypoint, rate-limit middleware
│   ├── database.py
│   ├── models/
│   └── routes/
│       ├── auth.py                # JWT + PIN + seed-heal
│       ├── products.py · categories+modifiers MOVED → items_system.py
│       ├── transactions.py · refunds
│       ├── customers.py · feedback
│       ├── reservations.py · floor_plans · waitlist
│       ├── kitchen.py · analytics.py · automation.py
│       ├── settings.py · loyalty.py · public.py
│       ├── table_ordering.py · integrations.py
│       ├── ai_pantry.py · members.py · multi_tenant.py
│       ├── advanced_features.py    # EOD · Marketing · Tips · Training
│       ├── staff_management.py     # PIN · timecards · roster · payrun · ROSTER PUT
│       ├── menu_features.py        # AI menu import · ghost · what-if
│       ├── enterprise_features.py  # surcharges · permissions · hardware
│       ├── gamification.py         # leaderboard · smart-tips · print-routing
│       ├── reservation_features.py # rules · experiences · clubmember · analytics
│       ├── items_system.py         # categories · modifiers · discounts · comp-void · payment-links
│       ├── v15_features.py         # tabs · favorites · variants · CSV · voice · ask-nua · image-gen · anomaly · auto-roster · swap · heatmap · cohort · audit · 2FA · GDPR · BAS e-file · i18n
│       └── loyalty_engine.py       # category-multiplied loyalty + Ash agent + voice command router
│
└── frontend/
    ├── public/manifest.json + service-worker.js   # PWA
    ├── electron/ · android/                       # Native wrappers
    └── src/
        ├── App.js
        ├── components/
        │   ├── BottomDock.jsx        # primary nav + live badges + More splash
        │   ├── AskNua.jsx            # global chat panel + FAB
        │   ├── VoiceOrderButton.jsx  # Whisper mic
        │   ├── VoiceCommandCatalog.jsx
        │   └── ui/                   # shadcn
        ├── contexts/                 # Theme (dark+lang), POS, Auth
        ├── pages/                    # 45+ pages
        └── services/api.js
```

---

## API Reference (condensed)

| Domain                   | Endpoints                              |
|--------------------------|----------------------------------------|
| Auth                     | `/api/auth/*` + `/auth/2fa/{setup,verify,disable}` |
| Items                    | `/api/{products,categories,modifiers,discounts,comp-void,payment-links}` |
| POS                      | `/api/pos/{tabs,favorites,voice-order,upsells}` |
| Loyalty                  | `/api/loyalty/{config,earn,redeem,balance/:id,ledger/:id}` |
| Ash Agent                | `/api/agent/{decisions,segments,tick,voice-command,voice-catalog}` |
| AI / LLM                 | `/api/ai/ask-nua` · `/api/items/generate-image` |
| Variants & Bulk          | `/api/products/:id/variants` · `/api/items/bulk-import` |
| Transactions / Refunds   | `/api/{transactions,refunds}`         |
| Customers / GDPR         | `/api/customers/:id/gdpr-export` · DELETE for erase |
| Reservations             | `/api/reservations` · `/api/floor-plans` · `/api/waitlist` · `/api/booking/*` · `/api/clubmember/*` |
| Analytics                | `/api/analytics/{inventory-anomalies,booking-heatmap,cohort-retention,demand-forecast}` |
| Kitchen / Pre-Shift      | `/api/kitchen/*` · `/api/pre-shift/today` |
| Staff & Roster           | `/api/staff/{roster,timecards,shift-swaps,auto-roster}` · `/api/payrun/*` |
| Tips · Leaderboard       | `/api/tips/*` · `/api/gamification/*` |
| Reports                  | `/api/reports/{end-of-day,quarterly-review}` |
| Print Routing · Hardware | `/api/print-routing/*` · `/api/hardware/*` |
| Permissions · Surcharge  | `/api/permissions/*` · `/api/surcharge/*` |
| BAS/GST                  | `/api/bas-gst/efile/:reportId`        |
| Compliance               | `/api/audit/logs`                     |
| Dock Live Counters       | `/api/dock/badges`                    |
| i18n                     | `/api/i18n/labels/:lang`              |
| Public / Table-Side      | `/api/public/*` · `/api/table/*`      |
| Integrations · Stripe    | `/api/integrations/*` · `/api/stripe/*` |
| Member portal · Multi-biz| `/api/members/*` · `/api/business/*` |
| Live Sales / EOD / Email | `/api/live-sales` · `/api/reports/end-of-day` · `/api/marketing/campaigns` |

---

## Potential Improvements

> Pending = Phase B (needs user API keys), Phase E (true autonomous decision-making), Phase F (Nomni gap features).

### Phase B — 3rd-party integrations (pending user keys)
- WhatsApp Business — one-tap WhatsApp receipts + reservation reminders
- Twilio SMS — booking confirmations, "tonight only" blasts, lost-customer win-back
- Stripe Tap-to-Pay on iPhone (needs native iOS build)
- Stripe Crypto (USDC tap-to-pay)
- Xero / QuickBooks live accounting sync
- Real Uber Eats / DoorDash POS push
- Google Reserve direct booking link
- TikTok Shop catalog sync
- Afterpay/Klarna BNPL provider connection

### Phase E — Deeper autonomy for Ash (every section gains autonomous decisions + voice)
- **POS**: auto-suggest upsells in cart based on customer history; auto-apply best applicable discount; voice "void last item" / "split bill"
- **Items**: auto-generate Nano Banana images for items missing photos; auto-tune prices based on sales velocity; voice "raise espresso by 50 cents"
- **Reservations**: auto-confirm SMS; auto-walk-in conversion; auto-overbooking guardrails based on heatmap; voice "block bookings tonight after 9pm"
- **Roster**: auto-publish AI roster if cost < target; auto-find swap candidates; voice "ask Maria to cover Friday lunch"
- **Customers**: auto-tag VIPs; auto-send birthday vouchers; auto-segment campaigns; voice "send 20% off to lost customers"
- **Reports**: auto-email EOD to owner; auto-anomaly alerts via push; voice "compare this week vs last week"
- **Kitchen**: auto-prioritize tickets by table turn time; auto-reroute when station overloaded
- **Marketing**: auto-trigger lost-customer win-back at 60-day mark; auto-A/B test subject lines

### Phase F — Nomni-style features we don't have yet
- **AI Phone Agent** for inbound orders/bookings (voice agent picks up, takes order, adds to POS, books table)
- **Predictive labor forecasting** tied directly to weather + bookings + historical demand
- **Auto-reorder PO generation** with per-supplier minimums and lead times
- **Real-time menu A/B testing** (random 50% of QR menus show variant)
- **Guest predictive ordering** — show "your usual" before they ask
- **Dynamic surge pricing** for peak hours (opt-in)
- **AI cost-control coach** — daily nudges: "reduce avocado spec by 15g to recover 8% margin"
- **Voice-to-recipe** for new menu R&D
- **Live menu kitchen-load balancing** (auto-86 items when station is overwhelmed)

### Phase G — Infrastructure & Dev
- Split `POSTerminal.jsx` (900+ lines) into Cart / Payment / VoiceBar / TabsDialog sub-files
- Convert `App.js` route list into structured react-router config
- Real TOTP via pyotp (currently demo accepts `123456`)
- WebSocket real-time orders/bookings (currently 30s polling)
- Multi-region Atlas deployment notes
- Per-route latency tracing + Prometheus metrics
- Snapshot rollback for owner config changes

### Phase H — Compliance & Security upgrades
- Audit log retention policy + exportable PDF
- SOC2-friendly admin action logging
- IP allowlist per tenant
- Per-customer consent ledger (cookie/notice acceptances)
- WCAG 2.2 AA accessibility pass
- Penetration-test friendly headers (CSP, HSTS, X-Frame-Options)

---

## License

Built by Emergent platform AI agents across 23+ iterations. Copyright © NUA — 2026.
