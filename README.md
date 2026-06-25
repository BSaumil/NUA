# Nua — Restaurant OS

> A production-ready, AI-first restaurant operating system. POS, kitchen, reservations, inventory, accounting, loyalty, social-media marketing — all in one place. Built with React + FastAPI + MongoDB. Themed in NUA's signature orange / purple / pink palette and rebranded as **Nua - Restaurant OS** from iteration 37 onward.

---

## Table of Contents

1. [What you get](#what-you-get)
2. [Tech stack](#tech-stack)
3. [Quick start](#quick-start)
4. [Demo credentials](#demo-credentials)
5. [Feature map](#feature-map)
6. [Project timeline (Day 1 → today)](#project-timeline-day-1--today)
7. [Repository layout](#repository-layout)
8. [API surface (selected)](#api-surface-selected)
9. [Configuration](#configuration)
10. [Testing](#testing)
11. [Roadmap / Backlog](#roadmap--backlog)

---

## What you get

- **POS Terminal** — fluid grid, modifier picker, dine-in / takeaway flows, customer attachment, points-and-pay, split payments with validation, QR / UPI / Cash / Card / Stripe, gift cards, vouchers, modifier sheet, live status bar with date/time/devices/network, table/walk-in inputs.
- **Kitchen Display** — station readiness, kitchen heat, station rebalance, prep-time AI sync.
- **Reservations** — booking inbox AI parser (web/social/SMS), AI auto-assign tables, channel source badges, overbooking guardrail, phone agent.
- **Catalog (Products & Promotions)** — categories with icons & colours, multi-modifiers, bulk-edit (price ±%, cost, GST, image, 86, modifiers), inline edit, image library, drag-to-select marquee, recently-edited sidebar, CSV import/export, promotion dialog with day-of-week & time-window targeting.
- **Channel Menus** — per-platform (Uber, DoorDash, Menulog, Deliveroo, Website, Kiosk, Google Food) pricing overrides, AI prep-time sync, AI slow-mover discounts.
- **Inventory & Accounting** — ingredients with base units (g/mL/ea), recipes with auto unit conversion, auto stock deduction on sale, weighted-moving-average ingredient cost, stock-take with shrinkage, BAS / GST report (FY + quarter + CSV), Fair Work superannuation by award.
- **CRM** — customers, tiers, points, your-usual, GDPR export/erase, cohort retention, booking heatmap.
- **Loyalty Engine** — category multipliers, points-and-pay (10pt = 10c floor), Ash AI agent.
- **Online Ordering** — public storefront, AI ETA with surge & queue penalty, kitchen load board, order tracking.
- **Social Media Marketing** — connect mocked Instagram/Facebook/TikTok/X/Google Business; AI composer (Claude Sonnet 4.6) generates caption + hashtags + image alt; **Content Calendar** with month grid, drag-to-reschedule, AI Weekly Plan that schedules 7 days from top sellers + active promos; wired to image library.
- **Voucher / Gift Card** lifecycle — auto-mint on sale, partial redemption ledger, barcode print, in-POS apply.
- **AI Suite** — voice recipe (Whisper + GPT), AI Pantry invoice OCR + suggested price, AI upsell strip, AI cost coach, AI labor forecast, AI price tune with audit, AI surge pricing, AI marketing emails, AI overbooking check.
- **Enterprise** — multi-tenant licensing with ABR/ABN verification, 30-min JWT entitlement, Stripe billing webhook with progressive lockout, audit log, 2FA, device fleet, dispute & evidence packs, supplier marketplace, multi-site command center, franchise dashboard, fraud detection, dynamic pricing, subscriptions, kiosk, customer-facing display, profit guardian, station readiness.
- **Integrations Hub** — Stripe, ElevenLabs, OpenAI, Anthropic, Gemini, 12 AU banks, 15 payment terminals, Resend, SendGrid, Twilio, Xero (placeholders), Uber Eats / DoorDash channel pricing.

## Tech stack

| Layer        | Tech                                                                  |
| ------------ | --------------------------------------------------------------------- |
| Frontend     | React 18, React Router 6, Tailwind, shadcn/ui, lucide-react, sonner   |
| Backend      | FastAPI, Pydantic, Motor (async MongoDB), httpx                       |
| Database     | MongoDB                                                               |
| LLMs         | Claude Sonnet 4.6 / GPT-5.x / Gemini (via `emergentintegrations`)     |
| Auth         | JWT (`jose`) + bcrypt + optional 2FA                                  |
| Payments     | Stripe (test key in pod env)                                          |
| Object store | base64-encoded data URLs (compressed client-side to ≤1.5 MB)          |

## Quick start

```bash
# 1. Backend
cd /app/backend
pip install -r requirements.txt
# Set MONGO_URL, DB_NAME, EMERGENT_LLM_KEY in .env (already pre-configured in the pod)
sudo supervisorctl restart backend

# 2. Frontend
cd /app/frontend
yarn install
sudo supervisorctl restart frontend
```

Both services are managed by **supervisord** with hot reload. Use `sudo supervisorctl status` to inspect.

## Demo credentials

| Role     | Email                | Password           |
| -------- | -------------------- | ------------------ |
| Owner    | `owner@nuva.com`     | `NuvaOwner2026!`   |
| Manager  | `manager@nuva.com`   | `Staff2026!`       |
| Cashier  | `cashier@nuva.com`   | `Staff2026!`       |
| Kitchen  | `kitchen@nuva.com`   | `Staff2026!`       |
| 2FA code | `123456`             | (demo only)        |

## Feature map

| Area                    | Route                | Backend module                                       |
| ----------------------- | -------------------- | ---------------------------------------------------- |
| POS                     | `/pos`               | `routes/transactions.py`, `routes/products.py`       |
| Kitchen                 | `/kitchen`           | `routes/kitchen.py`                                  |
| Reservations            | `/reservations`      | `routes/reservations.py`, `routes/bookings_inbox.py` |
| Items                   | `/products`          | `routes/products.py`, `routes/items_system.py`       |
| Channel Menus           | `/channel-menus`     | `routes/channel_menus.py`                            |
| Inventory & Accounting  | `/inventory-accounting` | `routes/inventory_accounting.py`, `routes/awards.py` |
| Customers               | `/customers`         | `routes/customers.py`                                |
| Loyalty                 | (POS embed)          | `routes/loyalty_engine.py`                           |
| Online Ordering         | `/online-orders`, `/order-online`, `/track/:code` | `routes/online_orders.py` |
| Social Media Marketing  | `/social-media`      | `routes/social_media.py`                             |
| Enterprise Command      | `/enterprise`        | `routes/v25_suite.py`, `routes/v26_commerce.py`      |
| License & Billing       | `/license`           | `routes/licensing.py`                                |

## Project timeline (Day 1 → today)

Each block is one user-driven iteration. Bullets are the **user instruction** plus what shipped.

### Day 1 — Foundation (Iterations 1–10, late 2025)
- **Build a restaurant POS** — initial scaffold: React + FastAPI + MongoDB, basic products / categories / transactions / customers CRUD, auth (JWT + bcrypt) with seeded admin user.
- **Add a kitchen display** — `/kitchen` with station load, prep timers, ticket aging.
- **Reservations** — table management, party-size grid, status flow.
- **Customer DB** — visits / spend / points / tier; "your usual" derived from last 20 transactions.
- **Modifiers, Discounts, Comps/Voids, Payment Links** — full `items_system` CRUD.

### Day 2 — Analytics + AI Wave 1 (Iterations 11–18, Dec 2025)
- **Analytics dashboard** — revenue, top items, hour-of-day heatmap.
- **AI upsell strip** under the POS cart (LLM-driven, debounced 1.2s).
- **AI Cost Coach, Labor Forecast, Surge Pricing, Voice Recipe** pages and endpoints (Wave 2).
- **Phone Agent, Purchase Orders, A/B Testing, Agent Autonomy** (Iteration 24).
- **Auto-PO from low stock**, **Auto-VIP tier promotion**, voice "raise espresso 50c" actions verified.

### Day 3 — Enterprise + Licensing (Iterations 25–27, Jan 2026)
- **Iteration 25–26** — Unified Gift Cards + AI Marketing Emails + AI Roster Blackouts + Live CFD. Atomic `find_one_and_update` gift-card redemption with ledger; `/v26/cfd/push` for live customer-facing display.
- **Iteration 26 (Enterprise)** — `routes/v25_suite.py` with 30+ endpoints: sync queue, exceptions, sites, hardware fleet, disputes, supplier marketplace, kiosk, CFD, recovery, station readiness, margin guardrails, dynamic pricing, subscriptions, gift cards, recipes, waste, concierge, reputation, franchise, fraud detection, Ash Pro, profit guardian, digital twin. EnterpriseCommandCenter UI with 24-tile launcher.
- **Iteration 27 (Licensing)** — `routes/licensing.py`: ABR-verified ABN issuance, JWT entitlement tokens, device fleet, Stripe billing webhooks with state machine `active → past_due → grace → suspended → cancelled`, owner+2FA ABN change with support override, lock screen overlay, audit log. `LicenseEnforcementMiddleware`.

### Iteration 28 — POS Refactor + Fluid Layout + Seed Catalog (Jan 2026)
- **"Make POS fluid and prettier"** — switched product grid to `auto-fill,minmax(130px,1fr)`, side cart `w-full lg:w-[440px]`. Extracted `SwipeableCartItem`, `CustomerCombobox`, `PaymentDialogs`.
- **"Add icons and colours per category"** — categories accept `icon` + `color`; admin page rewritten with 21-icon picker grid + 15-swatch row.
- **"Seed a real menu"** — `POST /api/seed/catalog` (owner): 5 canonical categories, 60 products, 10 modifiers (idempotent).
- 86-toggle on POS tiles + smart substitution + kiosk upsell.

### Iteration 29 — Online Ordering + Invoice OCR + Item Insights (Jan 2026)
- **"Build me online ordering"** — public storefront `/order-online`, owner pipeline board `/online-orders`, tracking `/track/:code`. Channel-aware (pickup/delivery/dine-in). AI ETA = base prep × surge × queue + delivery offset, wrapped in LLM-generated friendly message.
- **"Let me upload a supplier invoice and bump prices"** — AI Pantry invoice tab; LLM extracts supplier/items, fuzzy-matches to products, suggests price preserving margin %.
- **"Show me which items make money"** — `/api/products/insights` with weeklyUnitsSold / weeklyRevenue / marginAmount / marginPct. Product cards render margin chip (green ≥60% / amber ≥40% / red <40%) and a weekly-sales tile.

### Iteration 30 — Notifications + Recipes + BAS / GST + Stock-take (Jan 2026)
- **"Connect SendGrid + Twilio"** — `utils/notifications.py` channel abstraction. Wiring real channels is now a config change.
- **"Ingredients → Recipes → auto stock deduction"** — `routes/inventory_accounting.py`; recipes with kg↔g, L↔mL conversion; `deduct_recipe_stock(productId, qty)` runs on every sale.
- **"Invoice → ingredient assignment"** — increments stock with WMA cost, cascade re-rolls every dependent recipe.
- **"Stock-take with variance"** — counts vs expected → totalShrinkageValue.
- **"Australian BAS / GST report"** — G1, 1A (= total/11), G11, 1B, netGstPayable. CSV export.

### Iteration 31 — NUA Brand + Items: Categories & Multi-Modifiers + Page Split (Feb 2026)
- **"Apply NUA brand identity globally"** — orange `#f58c14` / purple `#8b5cf6` / pink `#ec4899`. Legacy indigo migrates from localStorage on next load. Light/dark toggle in BottomDock.
- **"Items must support multi-modifier assignment + dynamic categories"** — `categoryId` + `modifierIds[]` on Product. Multi-toggle chip picker in the dialog.
- **"Split V25/V26 page bundles"** — barrel re-exports; implementations in `/pages/v25/*.jsx` (21 files) and `/pages/v26/*.jsx` (5 files).

### Iteration 32 — POS Modifier Picker (Feb 2026)
- **"POS should prompt for modifiers when item has them"** — `ModifierSheet` opens on every product tap when `modifierIds.length > 0`. Required vs Optional badges, single/multi-select with `maxSelections`, per-option surcharges. Cart line gets a synthetic id so two Flat Whites with different milk are separate lines but resolve to the same product.

### Iteration 33 — Items Power Tools (Feb 2026)
- **"Add sort/filter, bulk-edit, image library, inline edit"** —
  - Toolbar: search by name/SKU, sort by name/category/price/stock/margin/recent-edit asc/desc, status filter, grid/table toggle, CSV export.
  - Category filter chips, select-all visible, per-row checkboxes.
  - Bulk: change category, ±% price, set cost/GST, set image (from library), 86/un-86, add/remove modifier ids, delete.
  - **Image Library** — owner uploads once, auto-compressed to ≤800px / 0.85 JPEG; picker reusable from single-product and bulk dialogs.
  - **Inline edit** on cards & rows for name/price/stock. Per-row quick 86 toggle.

### Iteration 34 — Big Sweep (Feb 2026)
- **"Cart Dine-in / Takeaway table inputs, POS Date/Time header, Super via Fair Work, AU Bank integrations, AI Bookings Inbox, Channel Menus overrides, Kitchen Heat AI prep times, P2 auth refactors"** — all of the above shipped:
  - POSHeaderBar with clock + date + connected devices + network.
  - Free-text table input for dine-in, walk-in-name for takeaway.
  - Fair Work Modern Awards catalogue with 7 seeded awards; superannuation computation by award.
  - 12 AU bank cards + 15 payment terminals in the Integrations Hub.
  - `/api/bookings-inbox` — AI parses inbound bookings from web/social/phone/SMS; convert to reservation in one click.
  - **Channel Menus** CRUD; per-channel price overrides; AI Kitchen Heat prep-time sync; AI slow-mover discount endpoint.
- **P2 auth refactor (partial)** — `_require_owner_or_manager` moved to `deps.py` (full apply landed in iteration 36).

### Iteration 35 — P0 Auth Precedence (Feb 2026)
- **"401/403 must fire before Pydantic 422"** — `deps.py` exposes `get_user`, `require_owner`, `require_owner_or_manager` as top-level FastAPI `Depends`. Refactored `products.py`, `items_system.py`, `channel_menus.py`. Anonymous POSTs with bogus payloads now correctly return 401, not 422.

### Iteration 36 — Full Auth Refactor + Products.jsx Split (Feb 2026)
- **"Apply the Depends pattern to all the legacy routers"** — 16 routers, ~230 endpoints refactored: `advanced_features`, `ai_pantry`, `enterprise_features`, `gamification`, `inventory_accounting`, `licensing`, `loyalty_engine`, `menu_features`, `multi_tenant`, `online_orders`, `phase_ef`, `phase_ef_wave2`, `reservation_features`, `staff_management`, `v15_features`, `v25_suite`, `v26_commerce`. Edge cases referencing `request` after the auth block (~8 endpoints) intentionally skipped for bespoke handling.
- **CRITICAL fix** — `/loyalty/redeem` auth bypass: legacy `routes/loyalty.py` was registering the route BEFORE the auth-protected one in `loyalty_engine.py`. Removed.
- **"Split Products.jsx into Toolbar / ProductTable / BulkEditDialog"** — 963 → 618 lines.

### Iteration 37 — Drag-to-Select Marquee + Recently Edited + Nua Rebrand (Feb 2026)
- **"Drag-to-bulk-select rectangle on the Products grid, plus a Recently Edited sidebar showing the last 10 items touched today"**
  - Finder-style marquee on the grid: mouse-down on empty space → drag → cards intersecting are selected. Shift/⌘/Ctrl = additive. Escape cancels. Drags on buttons/inputs ignored. 6px movement threshold.
  - `RecentlyEditedSidebar` top-10 with optimistic `touchTimes` map so the list updates instantly.
- **"Change title to Nua - Restaurant OS and make sure no emergent anywhere in code"** — title + PWA manifest rebranded. Only `EMERGENT_LLM_KEY` env var and `emergentintegrations` package stay (functional, not user-facing).

### Iteration 38 — Social Media Marketing + Loyalty + Split + Promotion Extract (Feb 2026)
- **"Extract Promotion dialog from Products.jsx"** — `components/products/PromotionDialog.jsx`.
- **"Make sure all components are interconnected for CRM, stock and availability"** — verified: `routes/transactions.py` decrements stock + recipe ingredients + customer totals on every sale; 86-toggle honoured everywhere.
- **"Split payment should update as per selection, and it should check if wrong payment is entered, also after payment"** — Pay button disabled on ≤ 0 or excess. Imbalance warning banner when custom-mode splits don't add to the bill. Final txn refuses to create if splits don't balance within 1¢.
- **"Customers can redeem points for payments, a minimum of 10 points for 10 cents"** — `minRedeem` 50 → 10 in `loyalty_engine.py`; POS shows "Points & Pay (1 pt = $0.01, min 10)".
- **"Social Media Marketing should be AI-implemented, posting posts/stories/reels from products and deals + specials, connected to image library"** —
  - `routes/social_media.py`: accounts (mock OAuth) for Instagram/Facebook/TikTok/X/Google Business, posts CRUD, publish stub, `POST /social/ai-generate` (Claude Sonnet 4.6).
  - `/social-media` page: composer (source toggle product/promotion/special, tone, format, platforms, image picker, schedule), drafts preview with editable captions and hashtag chips, posts history table.

### Iteration 39 — Content Calendar + AI Weekly Plan + README (Feb 2026, current)
- **"Add a content calendar + AI weekly plan, keep Social Media features as is"** — `components/social/SocialCalendar.jsx`:
  - Month grid, colour-coded chips per platform, drag-to-reschedule via `PATCH /api/social/posts/{id}`.
  - **AI Weekly Plan** — `POST /api/social/ai-weekly-plan`: pulls top-7 selling products from the last 7 days, mixes with active promos and chef-special seeds, distributes one post per connected platform per day. Idempotent — re-running deletes prior `autoPlanRun=true` posts in the window before regenerating.
  - "Next 7 days" upcoming strip with inline publish / delete.
  - Composer / Calendar tab toggle at the top of `/social-media`.
- **"Create a README from Day 1 till today"** — this file.

## Repository layout

```
/app
├── backend/
│   ├── deps.py                     # FastAPI auth dependencies (single source of truth)
│   ├── database.py                 # Motor client + DB_NAME
│   ├── server.py                   # FastAPI app + router registration
│   ├── middleware/
│   │   └── license_middleware.py
│   ├── models/                     # Pydantic models (product, transaction, customer, …)
│   ├── routes/
│   │   ├── auth.py
│   │   ├── products.py
│   │   ├── items_system.py
│   │   ├── transactions.py
│   │   ├── customers.py
│   │   ├── reservations.py
│   │   ├── kitchen.py
│   │   ├── analytics.py
│   │   ├── inventory_accounting.py
│   │   ├── awards.py
│   │   ├── channel_menus.py
│   │   ├── bookings_inbox.py
│   │   ├── social_media.py
│   │   ├── loyalty_engine.py
│   │   ├── licensing.py
│   │   ├── v15_features.py / v25_suite.py / v26_commerce.py
│   │   ├── phase_ef.py / phase_ef_wave2.py
│   │   └── ...
│   ├── services/
│   │   └── abr_service.py
│   ├── utils/
│   │   └── notifications.py
│   └── tests/                      # pytest suites per iteration
├── frontend/
│   ├── public/
│   │   ├── index.html              # title: "Nua - Restaurant OS"
│   │   └── manifest.json           # PWA name: "Nua - Restaurant OS"
│   ├── src/
│   │   ├── App.js                  # routes
│   │   ├── contexts/               # AuthContext, POSContext, ThemeContext, LicenseContext
│   │   ├── services/api.js         # axios bindings
│   │   ├── components/
│   │   │   ├── BottomDock.jsx
│   │   │   ├── ImageLibrary.jsx
│   │   │   ├── pos/                # ModifierSheet, PaymentDialogs, SwipeableCartItem, …
│   │   │   ├── products/           # ProductsToolbar, ProductTable, BulkEditDialog,
│   │   │   │                        # PromotionDialog, RecentlyEditedSidebar
│   │   │   ├── social/             # SocialCalendar (NEW)
│   │   │   └── ui/                 # shadcn primitives
│   │   └── pages/
│   │       ├── POSTerminal.jsx
│   │       ├── Products.jsx
│   │       ├── ChannelMenus.jsx
│   │       ├── BookingsInbox.jsx
│   │       ├── SocialMedia.jsx     # composer + calendar
│   │       ├── InventoryAccounting.jsx
│   │       ├── EnterpriseCommandCenter.jsx
│   │       ├── LicensePage.jsx
│   │       ├── v25/   v26/         # split bundles
│   │       └── ...
├── memory/
│   ├── PRD.md                      # full per-iteration changelog
│   └── test_credentials.md
└── test_reports/                   # iteration_NN.json per testing-agent run
```

## API surface (selected)

Every endpoint is prefixed `/api`. Auth via Bearer JWT from `POST /api/auth/login`.

| Domain         | Endpoint(s)                                                           | Notes |
| -------------- | --------------------------------------------------------------------- | ----- |
| Auth           | `POST /auth/login`, `POST /auth/2fa/{setup,verify,disable}`           | JWT + optional 2FA |
| Products       | `GET/POST/PUT/DELETE /products`, `POST /products/bulk-edit`           | Bulk has fast `update_many` path |
| Modifiers      | `GET/POST/PUT/DELETE /modifiers`                                      | |
| Categories     | `GET/POST/PUT/DELETE /categories`, `POST /categories/cleanup-legacy`  | icon + color + prepTime + channels |
| Transactions   | `GET/POST /transactions`, `POST /transactions/refund`                 | Stock + recipe + customer cascade |
| Loyalty        | `GET/PUT /loyalty/config`, `POST /loyalty/redeem`                     | `minRedeem` = 10 (= $0.10) |
| Reservations   | `GET/POST /reservations`, `POST /reservations/{id}/ai-assign-table`   | AI auto-assign by party size |
| Bookings Inbox | `POST /bookings/inbox`, `POST /bookings/inbox/{id}/ack`               | AI parse → reservation |
| Channel Menus  | `GET /channel-menus/{channel}`, `POST .../patch`, `.../ai-prep-times`, `.../ai-discount-slow` | |
| Awards         | `GET /awards/catalogue`, `POST /awards/install`, `POST /payruns/super-by-award` | Fair Work AU |
| Social Media   | `GET /social/platforms`, `GET/POST/DELETE /social/accounts`, `GET/POST/PATCH/DELETE /social/posts`, `POST /social/posts/{id}/publish`, `POST /social/ai-generate`, `POST /social/ai-weekly-plan` | Mock OAuth; AI via Claude Sonnet 4.6 |
| Online Orders  | Public: `GET /online/{categories,products}`, `POST /online/orders`, `GET /online/orders/track/{code}` · Auth: `GET /online/orders`, `PATCH .../status`, `POST .../eta` | AI ETA |
| Licensing      | `POST /license/{onboard,validate}`, `POST /license/device/{activate,revoke}`, `POST /license/abn/change-request`, `POST /license/stripe/webhook` | Progressive lockout |

## Configuration

Environment variables (all in `.env` files, never hard-coded):

| Var                       | Where             | Required | Notes                                     |
| ------------------------- | ----------------- | -------- | ----------------------------------------- |
| `MONGO_URL`               | `backend/.env`    | ✅       | Don't rename                              |
| `DB_NAME`                 | `backend/.env`    | ✅       | Don't rename                              |
| `EMERGENT_LLM_KEY`        | `backend/.env`    | ✅       | Universal LLM key for all AI features      |
| `LLM_GATEWAY_URL`         | `backend/.env`    | optional | Defaults to the Emergent gateway          |
| `JWT_SECRET`              | `backend/.env`    | ✅       | Signs entitlement tokens                  |
| `STRIPE_API_KEY`          | `backend/.env`    | optional | Live billing                              |
| `STRIPE_WEBHOOK_SECRET`   | `backend/.env`    | optional | Verifies Stripe webhooks                  |
| `SENDGRID_API_KEY`        | `backend/.env`    | optional | When set, real emails fire                |
| `TWILIO_ACCOUNT_SID`      | `backend/.env`    | optional | When set, real SMS fires                  |
| `ABR_GUID`                | `backend/.env`    | optional | Live ABR ABN verification                 |
| `ALLOW_ABR_DEV_SKIP`      | `backend/.env`    | optional | Off by default (production-safe)          |
| `REACT_APP_BACKEND_URL`   | `frontend/.env`   | ✅       | Don't rename                              |

## Testing

- **Unit / route tests** — `cd /app/backend && python3 -m pytest tests/ -q`. Each iteration ships its own suite (e.g. `tests/test_iteration38_social_loyalty.py`).
- **End-to-end** — `testing_agent_v3_fork` is the integrated subagent used for full Playwright + curl runs. Reports land in `/app/test_reports/iteration_NN.json`.
- **Per-iteration scorecards**

| Iter | Backend | Frontend                | Notes                                                              |
| ---- | ------- | ----------------------- | ------------------------------------------------------------------ |
| 33   | 10/10   | 100%                    | Items power tools                                                   |
| 34   | 16/16   | 100%                    | Cart inputs, bookings inbox, super, banks, channel menus            |
| 35   | 42/42   | n/a                     | Auth precedence                                                     |
| 36   | 85/85   | full Products flow      | Auth refactor (×230 endpoints) + Products split + loyalty bypass fix |
| 37   | n/a     | 9/10 → 10/10 post-fix  | Drag-select + Recently Edited + Nua rebrand                         |
| 38   | 20/20   | ~88% (testid gaps only) | Social Media + Loyalty 10pt + Split + PromotionDialog               |
| 39   | curl-verified | self-tested      | Content Calendar + AI Weekly Plan + README                          |

## Roadmap / Backlog

### P1
- Real **SendGrid / Twilio API keys** to activate live notifications.
- **Real Meta / TikTok / X OAuth** to lift the social-publish stub.

### P2
- **~8 inline-auth endpoints** still on the legacy pattern (custom role mixes / signed-device-secret) — bespoke refactor required.
- **Chargeback / dispute console** with evidence packs UI polish.
- **Hardware health monitoring** alerts.
- **`x-ai-parsed-fallback` response header** so the UI can warn when the LLM fell back.
- Surface **`partialFailures`** on AI weekly-plan response so the UI can warn when some platforms used the template.

### Stretch
- Real-time WebSocket push for kitchen load and live A/B exposure.
- Surge pricing applied to live POS prices (currently only persisted).
- One-click `/voice-recipe` → product, with cost rolled up from ingredients.
- Auto-swap-finder + auto-EOD-email.

---

© Nua — Restaurant OS. Built iteratively. Tested rigorously. Themed boldly.
