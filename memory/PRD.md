# NUA POS — PRD v26.0 (Enterprise Licensing & Entitlements)


## v27.4 — Iteration 41 (26 Jun 2026): Best-Time-to-Post Analytics · AI Fallback Header · Chargeback Console · For Sam

### What landed
- **`GET /api/social/best-times`** + reusable `_compute_best_times()` — mines 7-day POS transactions, groups quantity by `(hour-of-day, category)` and filters per platform via `PLATFORM_CATEGORY_AFFINITY`. Each row returns `{platform, platformLabel, recommendedHour, recommendedTime, sampleSize, source ∈ {pos_peak | pos_peak_clamped | default_band}, band [lo,hi]}` so the UI can show *why* it picked that hour.
- **`WeeklyPlanIn.useBestTimes: bool`** (default `False`) — when `True`, the AI weekly plan applies per-platform best hours from `_compute_best_times()` instead of a fixed `postTime`. Plan-days were refactored to carry `dayBase` (midnight ISO) and a helper `_resolve_scheduled_for(plan_day, platform)` / `_sched_for(...)` (inline preview + background worker) computes the per-platform `scheduledFor`. Job doc now persists `useBestTimes` + `bestTimeMap` so the polling UI knows the schedule shape.
- **`x-ai-parsed-fallback` header on `POST /api/bookings/inbox`** — `_ai_parse()` returns a 4th `fallback: bool`; the route sets the header (`true`/`false`) and also stores `aiParsedFallback` on the persisted document so historic cards can still surface a warning. `CORS expose_headers = ['x-ai-parsed-fallback']` so SPA `fetch` can read it.
- **Chargeback / Dispute Console rewrite** (`/app/frontend/src/pages/v25/Disputes.jsx`):
  - KPI strip: Open / Evidence-In / Won / At-risk $ / Recovered $ with tone-coloured cards.
  - Filter pills (All/Open/Evidence/Won/Lost), status-keyed badges with icons, monospace IDs, "Attach evidence" CTA opens a proper Radix dialog (with `DialogDescription` for a11y).
  - New-Dispute dialog replaces the old `prompt()`-driven flow — TX id + amount validation + reason dropdown (`fraud | product_not_received | duplicate | unrecognised | service_not_provided | other`).
- **Frontend best-time chips** in `SocialCalendar.jsx` — strip below the KPI row showing each platform's recommended time + source pill (POS / POS± / Default) + "Use best times in AI plan & drag-drop" toggle (default on). Drop-to-reschedule now snaps to the platform's best hour when the toggle is on.
- **`/app/For Sam.md`** — 350-line deployment doc covering Web (Docker + compose + hosting picks), Windows (PWA install OR Electron kiosk), Android (PWA OR TWA via Bubblewrap OR React Native shell), Day-2 ops (backups, secret rotation, monitoring), troubleshooting cheat-sheet, and a 5-year posture section (multi-tenant, offline-first, edge cache, reservations OAuth, hardware health).

### Iteration 41 Tests
- **Backend 10/10 PASS** (`tests/test_iteration41_best_times_and_inbox.py`). `/best-times` shape contract verified per platform; `ai-weekly-plan` preview honours per-platform hours when `useBestTimes=true`, falls back to fixed `postTime` when `false`; save-path returns queued, polls to complete, posts persisted with correct per-platform `scheduledFor`. Inbox header verified both true/false branches; CORS exposes the header.
- **Frontend 100%** on tested flows: best-time chip strip renders all 5 platforms with correct chips + toggle, Disputes console renders all 5 KPIs + dialog opens.

### Backlog
- **P2** Touch-friendly DnD for tablets (`@dnd-kit` migration).
- **P1** Real Meta / TikTok / X OAuth — playbook pending API keys from user.
- **P1** SendGrid / Twilio production keys.
- **P2** Hardware health monitoring (route already exists in `automation.py`).

## v27.3 — Iteration 40 (25 Jun 2026): Background Worker · Calendar Edit/Reuse · Bespoke Auth Cleanup

### What landed
- **`POST /social/ai-weekly-plan` is now a background job** (FastAPI `BackgroundTasks`). The HTTP call returns in **~64ms** (verified) with `{planId, status:'queued', expected, platformsUsed, message}`. Progress is streamed into `social_plan_jobs` with `{status, completed, expected, fallbacks}` — polled via new **`GET /social/plan-jobs/{plan_id}`** every 2.5s by the UI. Background worker catches exceptions and flips status to `failed` with the error string preserved. Save=true takes the background path; save=false still runs inline because the caller wants the preview body back synchronously.
- **`POST /social/posts/{id}/duplicate`** — owner clones any prior post as a fresh draft (or scheduled when `scheduledFor` is provided). Strips `autoPlan*` / `publishedAt` flags, regenerates id+createdAt, records `duplicatedFrom`. Optional body fields (`platform`, `caption`, `hashtags`, `imageUrl`, `scheduledFor`, `status`) allow tweaks at duplicate time. Status enum + platform validated.
- **Calendar `edit + reuse` UX** (`components/social/SocialCalendar.jsx`):
  - Click any chip OR the new Pencil icon on the Next-7-Days strip → `[data-testid=edit-post-dialog]` opens pre-filled with caption / hashtags / scheduledFor / imageUrl / status. Save fires `PATCH /api/social/posts/{id}` and reloads.
  - Inline **Duplicate** button (`Copy` icon) on every upcoming row, plus a Duplicate-as-draft link inside the Edit dialog header.
  - **Live progress bar** (`plan-progress-bar`) shows during AI Weekly Plan generation; calendar chips appear progressively as posts land; final 'Done — N posts saved' toast on completion.
- **Improved error wording** on `ai-weekly-plan` — structured `detail` with **`code: 'no_connected_accounts' | 'no_matching_platforms'`** plus `connected[]`, `requested[]`, `message`. UI surfaces `.message` if present, falls back to the raw detail otherwise.
- **Bespoke auth refactor (last ~8 endpoints) — cleared**:
  - `accounting/bas` + `accounting/bas.csv` — request dropped, `Depends(require_owner_or_manager)`.
  - `licensing/abn/approve/{req_id}` — request kept (header read) + `Depends(require_owner)`.
  - `agent/tick`, `agent/voice-command` (loyalty_engine) — request kept (voice/headers), auth via Depends.
  - `agent/auto-publish-roster`, `agent/tick-extended` (phase_ef) — Depends-gated.
  - `v25/products/{id}/86` — owner+manager+kitchen role check kept after Depends auth.
  - `v25/ash-pro/approve` — Depends(require_owner).
  - `v25/concierge` — Depends(get_user).
  - `v25/warehouse/export` — Depends(require_owner). Sig also cleaned (removed `request: Request = None` quirk).
  - Only `bookings_inbox.ack` retains inline auth — intentional graceful-degradation for webhook callers.
- **README updated** — Day 1 → 25 Jun 2026 timeline.

### Iteration 40 Tests
- **Backend 33/33 PASS** (`tests/test_iteration40_background_plan.py`). All 11 refactored endpoints validate anon-401, then owner-200 happy paths. Background job returns ~queued in <500ms. Polling advances queued→in_progress→complete in ~30-35s. Structured errors verified. Duplicate edge cases (anon, missing, status=scheduled without scheduledFor, fresh fields). PATCH (anon, invalid status, missing, success). Idempotency intact (iter 39 destructive-preview fix still holds).
- **Frontend 100% on tested flows**: AI Weekly Plan queue → progress bar (0→7) → completion toast in ~35s with chips appearing progressively. Edit dialog pre-fills + saves + reloads. Duplicate via upcoming button + via edit-dialog link both work. Composer regression clean.

### Minor (non-blocking)
- BAS field names — impl returns `g1TotalSales`/`oneA_gstOnSales`/`g11TotalPurchases`/`oneB_gstCredits`. Values correct; only key naming differs from the literal `G1`/`1A`/`G11`/`1B`. Won't change without explicit ATO contract guidance.

### Backlog
- **P2** Touch-friendly drag-and-drop for the calendar (HTML5 DnD doesn't work on tablets) → `@dnd-kit` migration.
- **P2** Chargeback / dispute console with evidence packs UI polish.
- **P2** `x-ai-parsed-fallback` header on AI endpoints so the UI can warn when LLM fell back.
- **P1** Real SendGrid / Twilio API keys.
- **P1** Real Meta / TikTok / X OAuth to lift the publish stub.

## v27.2 — Iteration 39 (Feb 2026): Content Calendar · AI Weekly Plan · README

### What landed
- **Content Calendar** at `/social-media` (Calendar tab):
  - Month grid (6×7), Monday-first, day-of-week header, prev/next/today nav.
  - Posts rendered as colour-coded chips per platform (Instagram pink, Facebook blue, TikTok cyan, X black, Google Business green) with status glyph (`✓` published, `◷` scheduled, `✎` draft).
  - **Drag-to-reschedule** — HTML5 native drag-and-drop. Drop a chip onto any cell → `PATCH /api/social/posts/{id}` bumps `scheduledFor` and flips `draft` → `scheduled` if needed. Published posts are non-draggable.
  - **AI Weekly Plan button** runs `POST /api/social/ai-weekly-plan` (auth, owner/manager) — pulls top-7 selling products from the last 7 days of transactions (`$unwind` + `$group` pipeline), mixes them with active promos and chef-special seeds, distributes one post per connected platform per day. Idempotent: re-running deletes prior `autoPlanRun:true` scheduled posts in the window before regenerating.
  - KPI strip: `scheduled / published / drafts` counts.
  - "Next 7 days" upcoming strip with inline publish/delete.
- **`PATCH /api/social/posts/{id}`** — small allow-list mutation (`caption`, `hashtags`, `imageUrl`, `scheduledFor`, `status`, `postType`). Status & postType validated against the same enums as create. 404 if not found.
- **Composer/Calendar tab toggle** on `/social-media` — existing composer + drafts + posts history all preserved.
- **README** at `/app/README.md` — full timeline from Day 1 through iteration 39, feature map, tech stack, API surface, configuration, testing scorecards, roadmap.

### Iteration 39 Tests
- **Backend 9/9 PASS** (`tests/test_iteration39_social_calendar.py`, ~130s — real Claude Sonnet 4.6 calls per platform/day). Covers: anon 401, save=true persistence, idempotent re-run, **save=false preview no longer destructive** (post-fix), PATCH reschedule, PATCH 400/401/404, no-accounts → 400.
- **Frontend 100% on tested flows**: tab toggle, calendar mount + month nav (`June 2026` → `July 2026` → Today), KPI strip render, 12 colour-coded `cal-post-{id}` chips rendering, 25 upcoming items, publish-from-upcoming flips chip to ✓, composer tab regression, 5-page regression (`/pos`, `/products`, `/channel-menus`, `/reservations`, `/inventory-accounting`) with 0 console errors. Drag-to-reschedule was UX-deferred from browser e2e (already covered by backend PATCH tests).

### Bug fixed during testing
- **CRITICAL** — `POST /social/ai-weekly-plan` preview mode (`save=false`) was destructive: the `delete_many({autoPlanRun:True, scheduledFor: in-window})` ran unconditionally BEFORE the `if body.save:` branch, so calling Preview wiped the user's saved auto-plan. Fixed by gating the delete inside `if body.save:`. Verified end-to-end: save=true creates 7 posts → save=false leaves them intact (preview returns 7 in `preview[]` without persistence).

### Backlog
- **P2** Move `ai_weekly_plan` to a background task — currently N×P Claude calls run inline (7 days × 5 platforms = 35 LLM calls in one HTTP request — risks gateway timeout in high-platform deployments).
- **P2** Touch-friendly drag-and-drop for the calendar (HTML5 native DnD doesn't work on tablets) — `@dnd-kit` migration.
- **P2** Distinguish "no connected accounts" from "no platforms in request matched" in the weekly-plan error message.
- **P2** ~8 inline-auth endpoints still on legacy pattern (custom role mixes / signed-device-secret) — bespoke refactor pending.
- **P1** Real SendGrid / Twilio API keys to activate live notifications.
- **P1** Real Meta / TikTok / X OAuth to lift the social-publish stub.

## v27.1 — Iteration 38 (Feb 2026): Social Media Marketing · Loyalty 10pt Floor · Split Validation · Promotion Dialog Extract

### What landed
- **Social Media Marketing** — new top-level feature at **`/social-media`**:
  - **Backend** `routes/social_media.py` with full CRUD for connections (Instagram/Facebook/TikTok/X/Google Business), draft + scheduled + published posts, and an AI generation endpoint. Mock OAuth at the connection boundary; actual cross-posting is a stub on `POST /social/posts/{id}/publish` (status flip + logged).
  - **AI content** via **Claude Sonnet 4.6** through the Emergent LLM Key. Pick a product, promotion, or describe a daily special → returns platform-tuned `{caption, hashtags[], imageAlt, isFallback}` per platform. Falls back to templated copy if the LLM key is missing or upstream errors (with `aiError` flag). Validated: real generations come back in ~5s, `isFallback: false`.
  - **Frontend** `pages/SocialMedia.jsx` — composer card (source toggle product/promotion/special, tone/format/platforms/image picker/schedule), drafts preview with editable captions and clickable hashtag chips, posts history table with per-row publish/delete. Wired to the existing **Image Library** for hero images. Mock-OAuth banner clearly communicates that connections are sandboxed.
  - **Nav** — added to `BottomDock` (More menu) with the Sparkles icon.
- **Promotion dialog extracted** to `components/products/PromotionDialog.jsx` (117 lines). `Products.jsx` is now 608 lines.
- **Split payment validation** (`PaymentDialogs.jsx` + `POSTerminal.handlePaySplit`):
  - Pay button **disabled** when amount ≤ $0 OR exceeds remaining.
  - **Imbalance warning banner** (`split-imbalance-warning`) when custom-mode splits don't add to bill total.
  - Final txn refuses to create if splits don't balance within 1¢ (reverts the just-confirmed status so the cashier can fix it).
- **Loyalty floor lowered**: `minRedeem` 50 → **10 points (= $0.10)** in `routes/loyalty_engine.py` DEFAULT_CONFIG + live config row updated. POS POS displays "min 10" prompt and 10 points discount = $0.10. CRM still records earnings/visits/lastVisit/totalSpent on every txn.
- **Components interconnection (verified, not new)**:
  - `routes/transactions.py` already decrements `products.stock`, fires `deduct_recipe_stock()`, and increments customer `totalSpent/visits/points + lastVisit` per sale.
  - 86-toggle persists via `products.eightySixed` and is honoured throughout grid/table/POS.

### Iteration 38 Tests
- **Backend 20/20 PASS** (`tests/test_iteration38_social_loyalty.py`). Anonymous 401 / cashier 403 / duplicate 409 / invalid platform 400 / invalid status 400 / AI generation real (non-fallback) / accounts + posts CRUD / publish / delete / loyalty config minRedeem=10.
- **Frontend ~88% PASS**. SocialMedia create → generate → publish flow live; Promotion dialog extraction works; split-pay validation works; loyalty 10pt floor honoured. Bug found: legacy `social_accounts` doc (channel_menus / v25 era) leaking into `GET /social/accounts` → **FIXED** by filtering `{tokenStatus: {$exists: True}}` and adding `data-testid="platform-card-{key}"` for E2E determinism.

### Backlog
- **P2** Real Meta / TikTok / X OAuth integration to lift the publish stub.
- **P2** ~8 inline-auth endpoints (custom role mixes / signed-device-secret) still on the legacy pattern — bespoke refactor required.
- **P2** `social_media_router` `partialFailures` top-level field so the UI can warn when LLM fell back.
- **P1** Real SendGrid / Twilio API keys to activate notifications.

## v27.0 — Iteration 37 (Feb 2026): Drag-to-Select Marquee · Recently Edited Sidebar · Nua Rebrand

### What landed
- **Browser title** is now **"Nua - Restaurant OS"** (`/app/frontend/public/index.html`). PWA manifest rebranded to `Nua - Restaurant OS` / short name `Nua` with the orange theme colour `#f97316`.
- **User-facing "Emergent" references removed**: the only remaining occurrence was a code comment in `routes/v15_features.py`; it now reads "Universal LLM gateway (OpenAI-compatible)…" and the gateway base URL is overridable via `LLM_GATEWAY_URL` env var. The Python lib `emergentintegrations` and the `EMERGENT_LLM_KEY` env var stay (required for the LLM integration to function).
- **Drag-to-select marquee** on the Products grid (Finder/Explorer-style). Mouse-down on empty grid space starts a marquee rectangle; cards whose bounding box intersects the rectangle become selected on release. Hold **Shift / ⌘ / Ctrl** during drag-start to ADD to the existing selection; plain drag REPLACES it. Drags that start inside a button/input/anchor/select/textarea are ignored so single-clicks still work. Movement under 6px is treated as a click, not a marquee. **Escape** during drag cancels without changing selection. `data-testid="marquee-rect"` and `data-testid="products-grid"` are exposed for tests.
- **Recently Edited sidebar** (`/app/frontend/src/components/products/RecentlyEditedSidebar.jsx`) — shows the 10 most recently touched products *today*, sorted newest first. Each item is clickable and opens the product editor. Hidden on screens narrower than `lg` so the grid keeps its full width on tablets/mobile. Powered by a hybrid source: backend `updatedAt` / `createdAt` PLUS an optimistic client `touchTimes` map so the list updates the instant you finish an inline-edit, bulk-edit, 86-toggle or save — no waiting for the next GET.
- **Backend fix** — `models/product.py` no longer falls back to `datetime.utcnow()` for missing `createdAt` / `updatedAt`. Both are now `Optional[datetime] = None`. Previously every read filled them with NOW, which made every legacy product look "edited just now" and silently pushed freshly-edited products further down the Recently Edited list. `POST /api/products` explicitly sets both timestamps on create; `PUT /api/products/{id}` continues to bump `updatedAt`.

### Iteration 37 Tests
- Iter 37 (frontend-only): 9/10 → **after the touchTimes + Pydantic fix, expected 10/10**. Title + manifest rebrand verified, drag-select marquee verified (shows during drag, bulk action bar reflects count, Shift+drag additive, mouse-down on buttons ignored, Escape cancels, table view hides grid), sidebar visible + renders prior edits + clicking opens editor.
- Backend regression on Products CRUD (curl) — PUT now returns a real ISO `updatedAt`; GET returns the persisted value (no longer "now").

### Backlog
- P2: ~8 remaining inline-auth endpoints (custom role mixes / signed-device-secret auth) skipped in iter 36's refactor — bespoke handling required.
- P1: Provide real SendGrid / Twilio API keys to activate the notification abstraction.
- P2: AI bookings inbox response header `x-ai-parsed-fallback` so UI can warn when LLM is unavailable.
- P2: Extract the Promotion dialog from `Products.jsx` into its own component (file is at ~631 lines now).

## v26.9 — Iteration 36 (Feb 2026): Full Auth-Depends Refactor + Products.jsx Split

### What landed
- **Backend `Depends` refactor — 16 legacy routers, ~230 endpoints**: `advanced_features.py`, `ai_pantry.py`, `enterprise_features.py`, `gamification.py`, `inventory_accounting.py`, `licensing.py`, `loyalty_engine.py`, `menu_features.py`, `multi_tenant.py`, `online_orders.py`, `phase_ef.py`, `phase_ef_wave2.py`, `reservation_features.py`, `staff_management.py`, `v15_features.py`, `v25_suite.py`, `v26_commerce.py` — all inline `from routes.auth import get_current_user` patterns converted to top-level `Depends(get_user / require_owner / require_owner_or_manager)` from `/app/backend/deps.py`. Anonymous POSTs now reliably return **401 BEFORE Pydantic 422**, cashier-role calls return **403**. Edge cases that referenced `request` after the auth block (~8 endpoints) were intentionally skipped and remain on the inline pattern.
- **CRITICAL bug fix — `/loyalty/redeem` auth bypass**: the legacy `routes/loyalty.py` was registering `POST /loyalty/redeem` BEFORE the auth-protected version in `routes/loyalty_engine.py`, allowing anonymous callers to deduct points from any customer. The legacy unprotected handler has been **removed**; `routes/loyalty.py` now also guards `POST /loyalty/rewards` and `DELETE /loyalty/rewards/{id}` with `Depends(require_owner_or_manager)`. A code comment in the file marks the redeem endpoint as owned by `loyalty_engine.py`.
- **Frontend — `Products.jsx` split (963 → 618 lines)**: extracted into three pure, presentational components under `/app/frontend/src/components/products/`:
  - `ProductsToolbar.jsx` (160 lines) — search, sort, status filter, layout toggle, CSV export, category chips, bulk-action bar, select-all checkbox.
  - `ProductTable.jsx` (307 lines) — both grid and table renderings of the catalog, with inline price/stock/name edit and 86 toggle.
  - `BulkEditDialog.jsx` (161 lines) — bulk-edit form with category/price-delta/cost/GST/status/image/modifier add+remove.
  All `data-testid` attributes preserved; bulk-edit, inline-edit, layout toggle, 86 toggle, CSV export and Image Library wiring all validated end-to-end.

### Iteration 36 Tests
- **Backend 85/85 PASS** (after fix). Anon-401 across 24 endpoints, owner-GET across 43 endpoints, owner-POST happy-path across 10 endpoints, iter-35 regression intact. Test: `/app/backend/tests/test_iteration36_depends_refactor.py`.
- **Frontend** — Products.jsx split fully validated: toolbar renders, bulk-edit dialog opens + applies +5% delta, inline price persists, table view loads, select-all works, CSV downloads. Smoke-tested /pos, /channel-menus, /reservations, /bookings-inbox, /inventory-accounting all clean.

### Note on intentionally-public storefront endpoints
- `POST /api/v25/kiosk/session*` and `POST /api/online/orders` remain **public by design** (guest kiosk checkout & customer-facing online ordering). Documented in route comments.

### Backlog
- P2: ~8 remaining inline-auth endpoints across `v25_suite.py`, `phase_ef.py`, `phase_ef_wave2.py`, `licensing.py`, `inventory_accounting.py`, `loyalty_engine.py` that use `request` after the auth block (custom role mixes or signed-device-secret auth) — skipped intentionally, would need bespoke refactor.
- P2: AI bookings inbox response header `x-ai-parsed-fallback` so the UI can warn when the LLM is unavailable.
- P1: Provide real SendGrid / Twilio API keys to fully activate the notification abstraction.

## v26.8 — Iteration 35 (Feb 2026): P0 Auth-Precedence Refactor (Depends Pattern)

### What landed
- **`/app/backend/deps.py`** is now the single source of truth for FastAPI auth dependencies. Exposes `get_user`, `require_owner`, `require_owner_or_manager` — all wired as top-level `Depends(...)` so the auth check fires BEFORE Pydantic body validation. Anonymous POSTs with bogus payloads now correctly return **401** (not 422); cashier-role calls return **403** instead of leaking the schema.
- **Refactored routes** to remove inline `from routes.auth import get_current_user` boilerplate:
  - `routes/products.py` — `bulk-edit`, `product-images` GET/POST/DELETE
  - `routes/items_system.py` — categories CRUD, modifiers CRUD, discounts CRUD, comp-void, payment-links, seed/catalog
  - `routes/channel_menus.py` — replaced its local `_owner_or_manager` with the shared dep; all 7 protected endpoints now use `Depends(require_owner_or_manager)`
- **Channel Menus** (already implemented in iteration 34, validated in 35): `/api/channel-menus/{channel}/ai-prep-times` syncs per-product prep times against current kitchen heat (active KDS tickets ×1.0/1.1/1.25/1.5). `/api/channel-menus/{channel}/ai-discount-slow` applies an N%-off to bottom-N slowest sellers of the last 7 days, with unsold products surfaced first. UI is wired in `pages/ChannelMenus.jsx` via `ai-prep-btn` and `ai-discount-btn`.

### Iteration 35 Tests
- **Backend 42/42 PASS** — 12 endpoints × {anon 401, cashier 403} = 24 precedence tests, plus happy-path Products bulk-edit / Modifiers CRUD / Product Images / Channel Menus CRUD+AI / Reservations AI assign-seat-complete chain / Fair Work Awards (catalogue, install, sync-fairwork, super-by-award) / Bookings AI Inbox (real LLM parse). Regression on products/transactions/customers green.
- Test file: `/app/backend/tests/test_iteration_p0_auth_refactor.py`.

### Backlog
- P2: Apply the same `Depends` refactor to legacy routers (`advanced_features.py`, `loyalty_engine.py`, `phase_ef_wave2.py`, `v25_suite.py`, `v26_commerce.py`, `enterprise_features.py`, `inventory_accounting.py`, `staff_management.py`, etc.) — currently still inline `get_current_user(request)`. Not a behaviour bug, just consistency.
- P2: Split `Products.jsx` (~960 lines) into `components/products/{Toolbar, ProductTable, BulkEditDialog}.jsx`.
- P2: AI bookings inbox response header `x-ai-parsed-fallback` so UI can warn when LLM is unavailable.
- P1: Provide real SendGrid / Twilio API keys to activate the notification abstraction.

## v26.7 — Iteration 34 (Feb 2026): Cart inputs · POS status bar · AI Bookings Inbox · Super (Awards) · Banks + Payment Terminals · P2 fixes

### What landed
- **Cart inputs simplified**: replaced 1-10 table buttons with a single free-text `Table #` input (`data-testid='table-input'`) for Dine-in and `Name` input (`data-testid='walk-in-name'`) for Takeaway. CustomerCombobox still ties the order to a loyalty profile.
- **POS Header Bar** (`/app/frontend/src/components/pos/POSHeaderBar.jsx`): replaces the "POS Terminal" title. Shows live HH:MM:SS clock, full date, devices-online count `N/M devices online` with offline-device names tooltipped, and a Wi-Fi / Ethernet / Offline indicator using the browser Network Information API. Polls `/api/v25/hardware` every 30s.
- **AI Bookings Inbox** (`/bookings-inbox` route + `routes/bookings_inbox.py`): unified inbox for inbound bookings from Instagram DM, Facebook Messenger, WhatsApp, SMS, phone, email, web form, walk-in. POST `/api/bookings/inbox` runs an LLM parse (env-configurable model via `BOOKINGS_INBOX_MODEL`, defaults to `gpt-4o-mini`) and extracts `{date, time, partySize, name, phone, notes}` + summary + suggestedReply. Past-dated extracted dates are now clamped to today so the LLM can't hallucinate "tonight" → 2023. `POST /bookings/inbox/{id}/ack` flips status and optionally converts to a reservation; `acknowledgedBy` is now taken from the auth token, never from the body (security fix flagged in code review).
- **Super (Awards) tab** in `/inventory-accounting`: new panel under `InventoryAccounting.jsx`. Award catalogue includes 4 Fair Work AU awards (Restaurant MA000119, Hospitality MA000009, Fast Food MA000003, General Retail MA000004) plus seed NZ/UK/US equivalents. Each award has classifications with base hourly + casual + weekend/PH loadings + super rate. Owner can Install/Uninstall awards (POST `/api/awards/install`, DELETE `/api/awards/{code}`). `POST /api/payruns/super-by-award` computes super per staff member from a payrun; returns `unresolvedAwards: []` so the UI can prompt to install missing codes.
- **Integrations Hub** extended (`routes/integrations.py`): 12 new AU bank cards (CBA, Westpac, ANZ, NAB, Macquarie, Bendigo, Bankwest, Suncorp, HSBC, ING Direct, BOQ, Judo) and 15 payment-terminal cards (Tyro, Smartpay, QIKI, Westpac EFTPOS Air, ANZ Worldline, NAB Easy Tap, Square Terminal, Zeller, mx51/Linkly, Verifone, Ingenico, PAX, Adyen, Razorpay, PayPal Zettle). Two new categories: 'Banks (AU)' (Building2 icon) and 'Payment Terminals' (Wallet icon). All auto-render in the existing Integrations page.
- **P2 fixes**:
  - `POST /api/products/bulk-edit` now picks a `update_many` fast path when no per-row math is needed (no `pricePercentDelta`, no add/remove modifier ops); returns `mode: 'update_many' | 'per_row'`. Per-row math still uses the slow path with price clamping.
  - **Auth guard** added to `/api/product-images`: POST + DELETE require owner/manager; GET requires any signed-in user (cashiers need to see images).

### Iteration 34 Tests
- **Backend pytest 16/16 PASS** — Bookings ingest/ack/convert, dismiss-404, Awards catalogue/install/uninstall/super-by-award math, country filter, Integrations Banks + Payment Terminals present, bulk-edit mode dispatch correct in both branches, product-images auth (anonymous 403, cashier 403, owner 200, GET requires auth).
- **Frontend 100% PASS** — POS header bar (clock + date + 5/5 devices + Wi-Fi), table-input free-text in dine-in, walk-in-name in takeaway, customer picker preserved, bookings-inbox compose → AI parse → Book it → reservation creation, Super (Awards) catalogue render + install/uninstall + Load Payrun + Compute Super, Integrations Banks (AU) and Payment Terminals chips filter correctly and Connect dialog opens.

### Backlog
- P2: SEED_AWARDS in `routes/awards.py` is hardcoded — production deployments will want a sync job to pull from Fair Work Modern Awards API.
- P2: AI bookings inbox header `x-ai-parsed-fallback` so UI can warn when LLM is unavailable.
- P2: Split `Products.jsx` (~960 lines) into smaller components — deferred again to avoid risking the just-added power-user features.
- P2: Move `_require_owner_or_manager` into a top-level FastAPI `Depends` so auth fires before Pydantic 422 (schema currently leaks to anonymous callers).



## v26.6 — Iteration 33 (Feb 2026): Items Page Power Tools — Filter, Sort, Bulk Edit, Image Library, Inline Edit

### What landed
- **Toolbar**: search by Name OR SKU, sort by name/category/price/stock/margin/recent-edit with asc/desc toggle, status filter (all/active/86), grid ↔ table layout toggle, CSV export of current view.
- **Category filter chips** — multi-select. Tap chips to OR-filter; tap 'All' to clear.
- **Selection + bulk actions**: per-row checkboxes, "Select all visible", bulk action bar appears when items selected. Supports:
  - bulk **change category**
  - bulk **±% price** (clamped to ≥-99% server-side to avoid negative prices)
  - bulk **set cost / GST rate**
  - bulk **set image** (pick from Image Library)
  - bulk **86 / un-86**
  - bulk **add/remove modifier ids**
  - bulk **delete**
- **Image Library** (NEW): `/app/frontend/src/components/ImageLibrary.jsx`. Owner uploads pictures once — auto-compressed client-side to ≤800px / 0.85 JPEG (~150-400 KB). Stored as base64 `dataUrl` in `db.product_images`. Search by name, tag-filter, delete. Pickable from single-product dialog **and** bulk-edit dialog.
- **Inline edit** on cards & table rows for `name`, `price`, `stock` — click → input → Enter → PUT /api/products/{id}. 4xx responses re-fetch instead of leaving stale optimistic UI.
- **Per-row quick 86 toggle**.

### New API surface
- `POST /api/products/bulk-edit` — body `{productIds, category?, categoryId?, pricePercentDelta?, cost?, gstRate?, image?, eightySixed?, active?, addModifierIds?, removeModifierIds?, replaceModifierIds?, onlineChannels?}` → `{updated, failed}`. `pricePercentDelta` clamped to ≥-99 and final price floored at 0.
- `GET  /api/product-images?search=&tag=&limit=` (default 100, max 500)
- `POST /api/product-images` — `{name, contentType, dataUrl, tags?, createdBy?}` — rejects non-data: URLs (400) and payloads >1.5MB (413)
- `DELETE /api/product-images/{id}`
- `ProductCreate.image` is now `Optional[str] = ""` (was required) to match the inline-edit UX

### Iteration 33 Tests
- Backend pytest **10/10 PASS** — bulk-edit price/cost/gst/category/eightySixed/modifier-ops, invalid+empty IDs, image upload/list/delete, non-data URL 400, oversize 413, delete 404.
- Frontend smoke **100%** — toolbar testids all present, sort by price persists, category chip filter works, grid↔table toggle, bulk-action-bar with correct count, bulk-edit-dialog with bulk-pick-image, inline price → Enter persists, image-library modal opens, CSV download works.

### Backlog from iteration 33 test report (P2)
- Split Products.jsx (~960 lines) into `components/products/{Toolbar,ProductTable,BulkEditDialog}.jsx`
- Auth guard on /api/product-images (currently open)
- Optimise bulk-edit with `update_many` when no per-row math



## v26.5 — Iteration 32 (Feb 2026): POS Modifier Picker End-to-End

### What landed
- **ModifierSheet** (`/app/frontend/src/components/pos/ModifierSheet.jsx`) — opens on every product tap when the product has `modifierIds.length > 0`. Required vs Optional badges, single-select / multi-select with `maxSelections`, per-option surcharges. Add button gated until all mandatory groups have ≥1 pick. data-testids: `modifier-sheet`, `mod-group-{id}`, `mod-opt-{modId}-{optName}`, `mod-confirm`, `mod-cancel`, `mod-validation`, `mod-loading`.
- **POSContext.addToCart** extended to `(product, qty, selectedModifiers, extraPrice)`. Items with modifier picks get a unique synthetic line id `${productId}__${shortUuid}` while preserving the original `productId` field — so two Flat Whites with different milk are separate cart lines but still resolve to the right product on the backend.
- **SwipeableCartItem** displays selected modifiers under the product name (`data-testid='cart-mods-{lineId}'`).
- **POSTerminal**: loads `/api/modifiers` once in parallel with categories. `handleProductClick` opens the sheet when `modifierIds` is non-empty (no longer gated on defs being loaded — sheet shows a loading hint and disables Confirm during the race). Both product card layouts (categorised + flat) show a `+N options` hint (`data-testid='pos-prod-mod-hint-{id}'`).
- **Transactions**: new helper `toTxItem` flattens each line's `selectedModifiers` into the backend `TransactionItem.modifiers: List[SelectedModifier]` shape — `{modifierId, modifierName, optionId, optionName, price}` — verified round-trips via GET /api/transactions/{id}.
- **Backend** `transaction.py` — widened `Transaction.tableNumber` and `TransactionCreate.tableNumber` to `Optional[str]` (was `Optional[int]`) since the frontend sends string table numbers and freeform 'Other' values.

### Verified (iter32, 4/4 backend + 100% frontend)
- Flat White: 6 modifier groups render, Required/Optional badges, surcharges, single-select cycle, multi-select cap, validation message.
- Cart shows the modifier breakdown per line.
- Cash transaction persists modifier picks; GET /api/transactions returns them.
- Items without modifiers (Soft Drink, Smoothies, etc.) bypass the sheet and merge as before.

### Files added / changed (iter32)
- NEW: `components/pos/ModifierSheet.jsx`
- CHANGED: `contexts/POSContext.js`, `components/pos/SwipeableCartItem.jsx`, `pages/POSTerminal.jsx`, `backend/models/transaction.py`
- NEW pytest: `backend/tests/test_iteration32_modifiers.py`



## v26.5 — Iteration 31 (Feb 2026): NUA Brand Identity + Items: Categories & Multi-Modifiers + V25/V26 Page Split

### Brand Identity Applied
- **ThemeContext default:** primary `#f58c14` (orange), secondary `#8b5cf6` (purple), accent `#ec4899` (pink). Legacy indigo (`#6366f1`) auto-migrates from localStorage to NUA orange on next load.
- **Dark / Light toggle** added to BottomDock (Sun/Moon icon, `data-testid='dock-theme-toggle'`). Flips body bg between NUA dark `#0b0b0f` and light `#f6f7fb`. CSS vars exposed: `--nua-bg`, `--nua-surface`, `--nua-card`, `--nua-text`, `--nua-muted`, `--nua-primary/secondary/accent`.
- **StaffLayout** now uses `darkMode` for body bg + text color (no more hard-coded `bg-gray-50`).
- **Login page** Sign-In button + Email/PIN tabs now use brand orange (was emerald).

### Items — Categories & Multi-Modifier Assignment (new requirement)
- **Backend** `models/product.py` — added `categoryId: Optional[str]` and `modifierIds: List[str] = []` to `Product`, `ProductCreate`, `ProductUpdate`. Empty list `[]` is honored by PUT (verified by pytest).
- **Frontend** `pages/Products.jsx`:
  - Loads `categoriesAPI.getAll()` + `modifiersAPI.getAll()` dynamically (no more hardcoded Beverages/Food/Bakery dropdown).
  - Add/Edit Product dialog has dynamic category `<select>` (`data-testid='product-category-select'`) populated from `/api/categories`, sorted by `sortOrder`, filtered to active.
  - Add/Edit Product dialog has new multi-toggle modifier chips area (`data-testid='product-modifiers-picker'`). Each modifier chip is `data-testid='mod-toggle-{id}'`. Tap-to-toggle persists `modifierIds: []` on save.
  - Product cards now show a "{n} modifier(s) attached" line under SKU when `modifierIds` is non-empty.

### V25 / V26 Page Split (refactor, no behaviour change)
- `pages/V25Pages.jsx` (688 lines) → barrel re-export. Implementations live in `/pages/v25/*.jsx` (21 files: `ShiftManager`, `AutoMarketing`, `Exceptions`, `HardwareHealth`, `Disputes`, `SupplierMarketplace`, `GiftCards`, `PredictiveOrders`, `WasteTracking`, `Concierge`, `Reputation`, `Franchise`, `FraudDetection`, `MarginGuardrails`, `StationReadiness`, `KioskMode`, `CFD`, `ChurnRisk`, `RecipeCosting`, `DynamicPricing`, `Subscriptions`).
- `pages/V26Pages.jsx` (599 lines) → barrel re-export. Implementations live in `/pages/v26/*.jsx` (5 files: `VoucherManager`, `EventsManager`, `StaffAvailability`, `GiftCardSale`, `MarketingEmails`).
- `App.js` imports unchanged.

### Iteration 31 Bug Fixes (post-test-agent)
- `pages/v26/StaffAvailability.jsx` — was reading `localStorage.getItem('token')` (returns `null`) instead of the actual `'nuva_token'` key. Auth-failed response then crashed `.filter`. Fixed key + added `Array.isArray(d) ? d : []` guard. Page now renders cleanly.
- `Inventory.jsx` + `Products.jsx` `<img>` tags — added placeholder fallback for empty `product.image` to eliminate 404 spam.

### Test Status — Iteration 31
- **Backend 7/7 PASS** — `categoryId`/`modifierIds` POST + PUT + GET persistence + empty-list semantics.
- **Frontend 12/12 PASS after fixes** — theme toggle, Products modifier picker, staff-availability render, all 26 v25/v26 routes.



## v26 (Feb 2026) — Iteration 27 — LICENSING RELEASE

### New backend module — `routes/licensing.py` (12 endpoints, prefix `/license`)
- `POST /api/license/onboard` — Issue tenant license bound to ABR-verified ABN (one ABN per license, immutable). `devSkipAbr=true` + `ALLOW_ABR_DEV_SKIP=true` env allows dev-mode issuance without ABR_GUID; production must omit the override.
- `POST /api/license/validate` — Server-authoritative startup/periodic check. Returns short-lived signed JWT entitlement token (30 min TTL). Specific error codes: `NO_LICENSE`, `DEVICE_NOT_AUTHORIZED`, `ABN_REVERIFY_REQUIRED`, `SUBSCRIPTION_PAST_DUE`, `LICENSE_SUSPENDED`, `LICENSE_CANCELLED`.
- `POST /api/license/device/activate` · `POST /api/license/device/revoke` — owner-gated device list with `maxDevices` enforcement.
- `POST /api/license/abn/change-request` — owner + 4-char 2FA + ABR re-verification + 7-day grace; immediately moves tenant into `abn_review` state.
- `POST /api/license/abn/approve/{req_id}` — gated by `X-Support-Override` header (per spec: "ABN cannot be changed once a license is issued").
- `POST /api/license/stripe/webhook` — handles `invoice.paid`, `invoice.payment_failed`, `customer.subscription.updated`, `customer.subscription.deleted`. Progressive state machine: Day 0-1 `past_due` (warn) → Day 2-6 `grace` (restrict admin) → Day 7+ `suspended` (block sales) → `cancelled` (export-only).
- `POST /api/license/billing/recovery-link` — generates a Stripe Billing Portal session URL for owner card update.
- `GET /api/license/me` · `GET /api/license/audit` — owner dashboard data.
- `POST /api/license/dev/force-state` — owner-only QA helper to simulate any of the 6 states.

### New services
- `services/abr_service.py` — `checksum_valid()` (MOD-89) + `lookup_abn()` (live ABR REST call via httpx, requires `ABR_GUID` from abr.business.gov.au/Tools/WebServices). Raises `RuntimeError("ABR_GUID not configured")` if env missing — refuses silent fallback unless explicit dev override.

### New middleware — `middleware/license_middleware.py`
- `LicenseEnforcementMiddleware` — server-authoritative. Allowlist: `/auth/`, `/license/`, `/payments/`, `/webhook/`, `/v25/warehouse/`. State enforcement:
  - **active** → all OK
  - **past_due / grace** → admin writes (settings, sites/publish, dynamic-pricing, device activation) → 423 `SUBSCRIPTION_PAST_DUE`
  - **suspended** → new sales (transactions, tabs, kiosk, gift-cards) → 423 `LICENSE_SUSPENDED`
  - **abn_review** → same as suspended but error code `ABN_REVERIFY_REQUIRED`
  - **cancelled** → only `/license/` + `/v25/warehouse/export` work; everything else → 423 `LICENSE_CANCELLED`

### New frontend
- `contexts/LicenseContext.jsx` — `LicenseProvider`, `useLicense()`, periodic 10-min revalidation, stable deviceId via localStorage.
- `pages/LicensePage.jsx` — three exports:
  - **default `LicensePage`** — owner dashboard: onboarding form (when no license), state badge, plan/devices/ABN verified/grace cards, device table with revoke, ABN change request (with 2FA + reason), dev/QA force-state controls, audit log.
  - **`LicenseLockScreen`** — full-page dark overlay (z-index 9999) shown when state is suspended/cancelled/abn_review; "POS Locked", "What you can still do", Update Billing + License Details CTAs, error code visible.
  - **`LicenseBanner`** — non-blocking amber strip at top of app shown during past_due/grace.
- `App.js` — `LicenseProvider` wraps `StaffLayout`; `LicenseBanner` + `LicenseLockScreen` mounted globally; `/license` route added.
- `BottomDock` — "License & Billing" entry added under Enterprise group (owner-only).
- `services/api.js` — `licenseAPI` export (me, audit, validate, onboard, activateDevice, revokeDevice, requestAbnChange, billingRecovery, forceState).

### Security & policy
- All license decisions server-side; the frontend cannot bypass state.
- 30-min JWT entitlement tokens (`HS256`, env `JWT_SECRET`).
- Stripe webhook signature verification when `STRIPE_WEBHOOK_SECRET` is set (warns and falls back in dev).
- Progressive lockout — never instant shutdown.
- Audit log of every state change (`license.created`, `device.activated/revoked`, `state.*`, `abn.change_requested`, `billing.paid/payment_failed`).
- Owner+2FA required for ABN change; support override key required for approval.
- Always-open routes: auth, license itself, billing recovery, data export, webhooks — even when suspended.

### Hardenings
- `ALLOW_ABR_DEV_SKIP` defaults to **off** (production-safe). Set explicitly on dev/staging.
- `forceState` in LicensePage now awaits `revalidate()` before resolving so navigation reflects new state immediately.

### Verified
- `testing_agent_v3_fork` iteration_24: **19/19 backend pytest passed**, all enforcement flows verified (suspended → 423, grace → 423 on admin writes, allowlist intact, ABN re-verification flow gates 2FA + support override, device authorization, stripe webhook with unknown customer returns 200 ignored, audit log chronological, no ObjectId leaks).
- Lock screen overlay verified visually with "SUSPENDED · POS Locked · LICENSE_SUSPENDED" + Update Billing CTA.

## Backlog (post-licensing polish)

## v25 (Feb 2026) — Iteration 26 — ENTERPRISE RELEASE

### Bug fix (P0)
- POSTerminal crash on customer selection — `yourUsual` state was referenced but never declared. Added `useState([])`.

### New backend module — `routes/v25_suite.py` (30+ endpoints, prefix `/v25`)

**MUST-HAVE (v25)**
- `POST/GET /api/v25/sync-queue` — Offline sync queue with duplicate detection
- `GET /api/v25/exceptions` — Loss-control: voids/comps/refunds + suspicious-user flagging
- `GET/POST /api/v25/sites` · `POST /v25/sites/publish` · `POST /v25/sites/rollback/{id}` — Multi-site command center
- `GET /api/v25/hardware` · `POST /v25/hardware/heartbeat` (X-Device-Secret) — Device fleet
- `GET/POST /api/v25/disputes` · `POST /v25/disputes/{id}/evidence` — Chargeback console with evidence packs
- `GET /api/v25/suppliers/compare` · `POST /v25/suppliers/quote` — Supplier marketplace with annual-savings calc

**SHOULD-HAVE (v26-v27)**
- `POST /api/v25/kiosk/session` + add + checkout + `GET /v25/kiosk/sessions` — Self-service kiosk
- `GET /api/v25/cfd/current` — Customer-facing display mirror
- `POST /api/v25/substitute` — Smart 86 substitution
- `GET /api/v25/recovery/churn-risk` · `POST /v25/recovery/win-back` — Guest recovery
- `GET /api/v25/station-readiness` — 0-100 ops score
- `GET /api/v25/margin-guardrails` — Items below 50% margin

**TIER 1 — Differentiators**
- `GET /api/v25/ash-pro/plan` (idempotent per-day) · `POST /v25/ash-pro/approve` — AI GM "Approve All"
- `GET /api/v25/profit-guardian` — Nightly margin drift detection
- `GET /api/v25/digital-twin` — Today's revenue ± 8% + covers + wait
- `GET /api/v25/shift-manager` — Real-time intervention alerts
- `POST /api/v25/marketing/auto` · `GET /v25/marketing/auto` — LLM-drafted campaigns

**TIER 2 — Revenue**
- `GET/POST /api/v25/dynamic-pricing` — Per (category, dow, hour) multipliers
- `GET /api/v25/subscriptions/plans` · `POST /v25/subscriptions/plans` · enroll · members
- `GET/POST /api/v25/gift-cards` · `POST /v25/gift-cards/{code}/redeem` (atomic findOneAndUpdate)

**TIER 3 — Inventory**
- `GET /api/v25/recipes/list` · `POST /v25/recipes/upsert` · `GET /v25/recipes/{productId}` — Recipe costing, pushes computedCost back to product
- `POST /api/v25/predictive-orders` — 14-day velocity → next-week POs grouped by supplier
- `GET/POST /api/v25/waste` · `GET /v25/waste/insights` — 30d cost insights

**TIER 4 — Guest Experience**
- `GET /api/v25/guest/{id}` — Universal profile (spend + visits + reservations + points)
- `POST /api/v25/concierge` — LLM classifies + auto-creates reservation
- `GET /api/v25/reputation` · `POST /v25/reputation/respond` (LLM-drafted)
- `POST /api/v25/recovery-action` — Service recovery voucher + flag

**TIER 5 — Enterprise**
- `GET /api/v25/franchise/dashboard`
- `GET /api/v25/benchmark` — Multi-store comparison
- `GET /api/v25/warehouse/export` — Power BI / Tableau export
- `GET /api/v25/fraud-detection` — Per-staff risk score

### New frontend
- `EnterpriseCommandCenter.jsx` — 24-tile launcher + 3 live KPI cards (Station Readiness, Expected Revenue, Live Alerts)
- `NuaPro.jsx` — Signals + actions + Approve All (one-click executor)
- `ProfitGuardian.jsx`, `DigitalTwin.jsx` — dedicated rich pages
- `V25Pages.jsx` — 21 compact pages: ShiftManager, AutoMarketing, Exceptions, HardwareHealth, Disputes, SupplierMarketplace, GiftCards, PredictiveOrders, WasteTracking, Concierge, Reputation, Franchise, FraudDetection, MarginGuardrails, StationReadiness, KioskMode, CFD, ChurnRisk, RecipeCosting, DynamicPricing, Subscriptions
- BottomDock — new "Enterprise (v25)" group with 25 entries; owner quick-action now shows "Enterprise" instead of Dashboard
- `services/api.js` — `v25API` export with all 40+ method bindings

### Hardenings applied post-test
- Gift-card redeem: atomic `findOneAndUpdate` with balance precondition (no race)
- Hardware heartbeat: requires `X-Device-Secret` header
- Ash-plan: idempotent upsert by `planDate` (no collection bloat)
- All seeded items pop `_id` before returning (no ObjectId leak)
- LLM errors logged via `logger.warning`, graceful degradation

### Verified
- `testing_agent_v3_fork` iteration_23: **34/34 backend pytest green · 25/25 frontend routes · 0 console errors**
- POSTerminal customer-selection regression PASSED
- All seed data prefixed `TEST_` for cleanup

## Backlog (post-v25 polish)

### Diagnostic fixes (P0)
- `/api/reservations` 500 → 200: `Reservation` model now accepts legacy `customerName`/`phone` via `model_validator(mode='before')`.
- `/api/purchase-orders` 500 → 200: removed conflicting strict-schema GET in `analytics.py`; `phase_ef.py` is the canonical handler.
- `phase_ef.py` phone-agent + auto-confirm now insert/read using `guestName`/`guestPhone`.

### Backend (`routes/phase_ef_wave2.py` — new)
- `POST /api/ai/upsell` — LLM (GPT-5.2) suggests 1-3 high-margin add-ons given current cart
- `GET /api/ai/price-tune` · `POST /api/ai/price-tune/apply` — 30-day velocity vs median → recommend raise/drop with audit `priceHistory` array
- `POST /api/ai/overbooking-check` — capacity + 10% buffer (configurable via `settings.overbooking.bufferRatio`) vs existing covers in ±30 min slot
- `GET /api/ai/cost-coach` — 30-day food-cost analysis vs 32% target + LLM 3-action plan
- `GET /api/ai/labor-forecast` — 8-week pattern → 7-day hourly FOH/BOH staffing needs
- `GET /api/ai/surge-recommendations` · `POST /api/ai/surge/apply` · `GET /api/ai/surge/active` — per (day, hour) demand multipliers
- `POST /api/ai/voice-recipe` · `GET /api/ai/recipes` — chef text or voice → structured recipe spec (Whisper + GPT-5.2); validates name+ingredients before persist
- `GET /api/ai/kitchen-load` — open-ticket station load + rebalance/priority suggestions

### Frontend
- New pages: `AICostCoach.jsx` `LaborForecast.jsx` `SurgePricing.jsx` `VoiceRecipe.jsx` `KitchenLoad.jsx` `PriceTune.jsx`
- 6 new routes wired in `App.js`: `/ai-cost-coach` `/labor-forecast` `/surge-pricing` `/voice-recipe` `/kitchen-load` `/price-tune`
- `BottomDock` "More" splash — Analytics & AI group expanded with 6 new tiles
- `POSTerminal.jsx` — AI upsell strip (debounced 1.2s, LLM-driven) under cart with 1-3 high-margin pairings
- `Reservations.jsx` — overbooking guardrail dialog before reservation creation (fail-open)

### Curl + Playwright verified
- All 8 Wave 2 endpoints return 200; LLM upsell returns 3 valid suggestions referencing real productIds
- POS cart → 3-5s → "✨ AI SUGGESTS" strip with reasoned upsells ✅
- All 6 new pages render with correct titles, no console errors ✅
- testing_agent iteration_22: 13/13 backend pytest green, 6/6 frontend smoke green

## v18 (Feb 2026) — Iteration 24

### Backend (`routes/phase_ef.py`)
- `GET/PUT /api/agent/autonomy` — owner toggles for auto-publish-roster, auto-confirm-SMS, A/B testing, VIP thresholds, reorder threshold
- `GET /api/comms/sms-queue` · `POST /api/comms/auto-confirm/{resId}` — auto SMS confirmation queue
- `POST /api/agent/voice-extended` — extended voice intents: void_last_item · price_change · eighty_six
- `POST /api/agent/auto-publish-roster` — generates + commits AI weekly shifts within budget cap
- `GET /api/phone-agent/calls` · `POST /api/phone-agent/simulate` — AI Phone Agent (GPT-5.2 classifier, auto-creates reservation, queues confirmation SMS)
- `GET /api/purchase-orders` · `POST /api/purchase-orders/generate` · `POST /api/purchase-orders/{id}/{approve,send,receive,cancel}` — auto-PO generation, receive auto-increments stock
- `GET/POST /api/ab-tests` · `POST /api/ab-tests/{id}/{exposure,conversion,conclude}` — live menu A/B testing with winner auto-pick
- `GET /api/customers/{id}/your-usual` — top-3 frequent items from last-20 transactions
- `POST /api/agent/tick-extended` — runs auto-VIP + auto-SMS + auto-PO rules in one shot

### Frontend
- `pages/PhoneAgent.jsx` (`/phone-agent`) — call log + simulate inbound call
- `pages/PurchaseOrders.jsx` (`/purchase-orders`) — supplier-grouped POs with workflow buttons
- `pages/MenuABTesting.jsx` (`/ab-tests`) — variant pair creator, exposure/conversion table, winner trophy
- `pages/AgentAutonomy.jsx` (`/agent-autonomy`) — owner toggle panel + threshold inputs + "Run Extended Tick"
- POSTerminal: **Your Usual** strip when known customer selected
- VoiceOrderButton now hands off transcript to `voice-extended` for void/price/86 commands
- BottomDock splash: 4 new tiles added under Analytics & AI group

## Curl-verified
- Voice "raise espresso by 50 cents" → $5.70 → $6.20 ✅
- Voice "drop latte by 1 dollar" → Product not found (handled gracefully) ✅
- Phone agent "book for 4 Saturday 7pm" → reservation auto-created + SMS queued ✅
- Auto-PO: seeded 3 low-stock products with supplier "Acme Wholesale" → 1 PO created ✅
- Auto-VIP: Sarah Johnson with spend=1500, visits=25 → tier auto-promoted from Gold to VIP ✅
- Your Usual: customer with 2 past orders → 2 most-frequent items returned ✅

## Frontend Playwright-verified
- `/phone-agent`, `/purchase-orders`, `/ab-tests`, `/agent-autonomy` all render ✅
- `/pos` with Sarah Johnson selected → Your Usual block visible ✅

## Credentials
Owner: owner@nuva.com / NuvaOwner2026!  
Manager: manager@nuva.com / Staff2026!  
Cashier: cashier@nuva.com / Staff2026!  
Kitchen: kitchen@nuva.com / Staff2026!  
2FA demo: 123456

## Backlog
- Phase B (user keys): WhatsApp · Twilio Voice/SMS · Stripe Tap-to-Pay · Crypto USDC · Xero/QB · Uber Eats · DoorDash · Google Reserve · TikTok Shop
- Real-time: WebSocket for kitchen-load auto-refresh and live A/B test exposure
- Refactor: Split POSTerminal.jsx (~1220 lines) into Cart/Payment/QR sub-components, split V25Pages.jsx and V26Pages.jsx mega-files
- Surge pricing apply to live POS prices (currently only persisted) — hook into product price calc
- Recipe → menu item: 1-click convert /voice-recipe generated spec into a product with cost-rolled-up from ingredient prices
- Auto-swap-finder + auto-EOD-email (Phase E next wave residual)

---

## v26.4 — Iteration 30 (Feb 2026): Notifications + Ingredients + Recipes + BAS + Stock-take

### Backend
- **`utils/notifications.py`** — channel abstraction `send_email` (SendGrid), `send_sms` (Twilio), `notify_order` (both, best-effort). Drops to `delivered:false / reason:not_configured` when env vars absent. **Wiring real channels is now a config change, not a code change** — just drop `SENDGRID_API_KEY`/`SENDGRID_FROM_EMAIL` + `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`/`TWILIO_FROM_PHONE` into backend/.env.
- **Order notifications wired**: `/online/orders` (place) + `/online/orders/{id}/status` now call `notify_order` and store `deliveryReceipts[]` on the order.
- **`routes/inventory_accounting.py`** — new module:
  - **Ingredients** with canonical `baseUnit` (g / mL / ea). CRUD + low-stock alert + reorderLevel guard.
  - **Recipes** (`PUT /recipes/product/{id}`) — auto-converts kg↔g, L↔mL, cl→mL. Rejects incompatible conversions (g↔mL). Computes product cost = `Σ qtyBase × ingredient.unitCost` and pushes back to the products collection so margin chips stay accurate.
  - **Auto stock deduction** on POS sale — `routes/transactions.py` calls `deduct_recipe_stock(productId, qty)` per item.
  - **Invoice → Ingredient assignment** (`POST /invoices/{id}/assign-stock`) — increments stock with unit conversion, updates unitCost as **weighted moving average**, posts a `stock_movements` audit row, then **cascade re-rolls** every recipe that uses the touched ingredients.
  - **Stock-take** (`POST /stock-takes`) — counts vs expected → variance + totalShrinkageValue.
  - **Australian BAS / GST report** (`GET /accounting/bas`) — G1 sales (incl GST), 1A GST collected (= total/11), G11 purchases (incl), 1B GST credits, netGstPayable. Supports `?fy=2026&quarter=Q3` or arbitrary `?monthStart&monthEnd`. CSV export at `/accounting/bas.csv` (ASCII-safe filename).

### Frontend (`pages/InventoryAccounting.jsx`)
- New 5-tab page at `/inventory-accounting`:
  1. **Ingredients** — inline add-form + table with low-stock alert banner.
  2. **Recipes** — product list ↔ recipe editor with kg/g/L/mL/ea selects, computed-cost preview.
  3. **Invoices → Stock** — pick a parsed invoice from AI Pantry, map each line to an ingredient + unit, one-click "Apply" updates stock + WMA cost + cascades recipe re-cost.
  4. **Stock-take** — table of all ingredients with expected vs counted vs Δ + history sidebar.
  5. **BAS / GST** — financial-year + quarter selector + 8 KPI tiles in system colours + CSV download.

### Test status — Iteration 30
- Backend **16/16 PASS** — every flow above + notification fallback (no keys → graceful `not_configured`).
- Frontend tabs all render, recipe editor + stock-take + BAS all interact.
- One issue auto-fixed by testing agent: CSV download filename was using Unicode arrow; now ASCII-sanitised.
- `retest_needed=false`.

## v26.3 — Iteration 29 (Feb 2026): Online Ordering + AI ETA + Invoice OCR + Item Insights

### Backend additions
- **`/api/online/*`** new module (`routes/online_orders.py`) — public storefront + owner inbox + AI ETA engine:
  - `GET /online/categories` (public) — channel-filtered active categories with prepTime + icon + color.
  - `GET /online/products` (public) — in-stock, not-86'd, online-channel-enabled catalog.
  - `POST /online/orders` (public) — places an order; computes deterministic ETA = max(category prepTime per line, +30% per extra unit of same cat) × surge(load-based, ≤1.6×) + queuePenaltyMins + deliveryOffsetMins. Wraps the ETA in a friendly LLM-generated natural-language message (GPT-5.2; deterministic fallback if no key).
  - `GET /online/orders/track/{code}` (public) — exposes only customer-safe fields (no phone/email/address leak).
  - `GET /online/orders` · `GET /online/orders/{id}` · `PATCH /online/orders/{id}/status` · `POST /online/orders/{id}/eta` (auth) — owner pipeline with channel-aware notification messages.
  - `GET /online/kitchen/load` (auth) — live snapshot of {pending, accepted, preparing, queuePenaltyMins}.
- **Categories** gain `prepTime` + `channels` (`dine-in` / `pickup` / `delivery`).
- **`POST /api/categories/cleanup-legacy`** (owner) — removes any non-canonical category that has zero products attached; safe / idempotent.
- **`POST /api/ai-pantry/parse-invoice`** (owner/manager) — accepts `text` or `imageBase64`. GPT-5.2 extracts supplier, invoice#, date, line items. Fuzzy-matches each line to existing products (exact lower-case → token overlap fallback). Computes suggestedPrice that preserves the current margin %.
- **`POST /api/ai-pantry/apply-invoice/{id}`** (owner/manager) — applies selected price/cost updates; returns audit trail.
- **`GET /api/products/insights`** — per-product `weeklyUnitsSold`, `weeklyRevenue`, `marginAmount`, `marginPct` (last-7-day window).
- **Product pydantic model** unchanged but `eightySixed`/`active` now visible in GET responses.

### Frontend additions
- **`/online-orders`** (owner) — pipeline board (5 stages: pending/accepted/preparing/ready/out_for_delivery/completed) with kitchen-load chip, click-through order details modal showing AI ETA breakdown (base / surge / queue penalty), step-by-step timeline, and stage-advance buttons (channel-aware: `Dispatch driver` for delivery, `Mark Ready` etc.). Polls every 8s.
- **`/order-online`** (public storefront, no auth) — channel picker (Pickup / Delivery / Dine-in), category strip with prepTime hint, fluid product grid, sticky cart with customer details form, navigates to tracking page on submit.
- **`/track/:code`** (public) — large AI ETA tile, ordered step-by-step timeline (channel-aware), customer notification feed. Polls every 12s.
- **AI Pantry — Invoice Upload tab** — file dropper (accepts image / PDF, FileReader → base64) + paste-text textarea, parsed invoice table with apply-cost / apply-price checkboxes per row, suggestedPrice shown in theme accent, one-click apply.
- **Items dashboard (`/items`)** — product cards now show: (a) margin chip in tier colours (green ≥60% / amber ≥40% / red <40%), (b) weekly-sales tile in `theme.primary` accent showing units sold + revenue past 7 days, (c) 86 corner badge preserved.
- **Categories admin** — prepTime input + 3 channel toggle pills, "Remove demo categories" cleanup button.

### Test status — Iteration 29
- **Backend 11/11 PASS** — full lifecycle, PII privacy on tracking endpoint, AI ETA accuracy, invoice OCR (LLM parsed "INVOICE 12345 / 2x Espresso / 5x Long Black" → matched + applied + audit), insights endpoint.
- **Frontend E2E PASS** (Playwright) — public storefront → order placement → auto-navigate to /track → AI ETA + timeline rendering; owner pipeline + kitchen load; categories with prep+channels; AI Pantry invoice tab; product cards with margin/weekly badges.
- `retest_needed=false`.

## v26.2 — Iteration 27-28 (Feb 2026): Fluid POS, Category Icons, Seed Catalog, P2 Refinement, Refactor

### Backend additions
- **`/api/seed/catalog`** (owner-only, idempotent): inserts 5 canonical categories (Coffee, Burgers, Mains, Cakes & Slices, Pasta), 60 products and 10 modifiers (Milk Choice, Extra Shot, Coffee Strength, Syrup, Burger Cheese, Burger Add-ons, Cooking Pref, Side Choice, Pasta Style, Sauce Add-on) — assigned by category.
- **Categories now accept `icon` + `color`** (`POST/PUT /api/categories`). `icon` is a lucide-react name (`Coffee`, `Beef`, `UtensilsCrossed`, `Cake`, `Soup`, …), `color` is a hex string.
- **`/api/v25/sync-queue/process`** (owner/manager): replays pending offline ops into real collections — `transaction.create`, `kitchen.order`, `stock.adjust`, `tab.append`. Idempotent via `clientOpId`. Returns `{applied, errors, pendingBefore}`.
- **`/api/v25/products/{id}/86`**: toggles 86 (out-of-stock) flag. Persists `eightySixed`, `eightySixedAt`, `eightySixedBy`. Sets stock to 0 when 86'd. Returns a `suggestedSubstitute` so the cashier can offer it on the spot.
- **`/api/v25/substitute`**: now ranks substitutes by price-proximity + stock and attaches a `substitutionReason` string per result.
- **`/api/v25/kiosk/session/{sid}/upsell`**: smart category-based upsell — examines what's missing in the kiosk cart and suggests up to 3 complementary items with reasons (e.g. "Add a drink to round out the meal", "Save room for something sweet").
- **`Product` pydantic model** gained `active`, `eightySixed`, `eightySixedAt`, `eightySixedBy` so the 86 flag round-trips through `GET /api/products`.

### Frontend
- **POSTerminal refactor**: extracted three components into `/app/frontend/src/components/pos/`:
  - `SwipeableCartItem.jsx` — left-swipe delete, right-swipe repeat
  - `CustomerCombobox.jsx` — cmdk-based searchable customer picker
  - `PaymentDialogs.jsx` — QR / UPI / Split payment dialogs as named exports
- **Fluid POS dashboard**: product grid switched to `[grid-template-columns:repeat(auto-fill,minmax(130px,1fr))]` (was fixed `grid-cols-3 sm:4 md:5 lg:6`). Side cart panel is `w-full lg:w-[440px]` so it stacks on narrow viewports.
- **Category icons on the POS**: each category button shows its custom icon + color (icon in coloured tile, active state floods the button with the category colour, not the global theme colour).
- **Categories admin (`/categories`)** rewritten with: large icon preview card, name+sortOrder+active inputs, **icon picker grid (21 lucide icons)**, **15-swatch colour row + custom colour picker**, live preview. Added `DialogDescription` for shadcn a11y.
- **`Barcode128`** extracted to shared `/components/Barcode128.jsx` (used by gift card sale page & subscription plans).
- **Login → POS redirect**: `Login.jsx` now uses `useNavigate('/pos', { replace: true })` after `login()` resolves.
- **86 indicator**: POSTerminal product tiles render a red "86" badge on out-of-stock items and disable the click handler (`opacity-50 cursor-not-allowed`).

### Frontend API surface (`services/api.js`)
- `itemsSystemAPI.createCategory/updateCategory` already accepted icon+color (passthrough).
- `v25API.processSync()`, `v25API.kioskUpsell(sid)`, `v25API.toggle86(id, eightySixed)`.

### Test status
- **Iteration 27**: Backend 10/10 PASS (seed idempotency, category icon CRUD, sync-queue replay, 86 toggle + substitute, kiosk upsell, gift card regression). Frontend POSTerminal + Categories admin rendered correctly.
- **Iteration 28**: Backend 6/6 PASS + Frontend 3/3 PASS — all action items from iteration 27 (Product model fields, login redirect, 86 badge, dialog a11y) verified fixed. `retest_needed=false`.


## v26.1 — Iteration 25-26 (Feb 2026): Unified Gift Cards + AI Marketing + AI Roster Blackouts + Live CFD

### Backend additions (`routes/v26_commerce.py`)
- **Unified Voucher↔Gift Card lifecycle**:
  - `POST /v26/vouchers` with `kind=gift` now also mints a paired `gift_card` row in `pending_activation` (shared code + barcode, `currentBalance=0`, `voucherId` linked).
  - `POST /v26/gift-cards/{code}/activate` — idempotent state transition pending → active. Sets `currentBalance = initial + bonus`, writes an `activate` ledger row in `db.gift_card_transactions`. Called automatically by POS *after* the cart paying for the card settles.
  - `POST /v26/gift-cards/{code}/redeem` — atomic partial redemption via `find_one_and_update` guarded by `currentBalance >= amount`. Writes a `redeem` ledger row, flips status to `depleted` at 0.
  - `GET /v26/gift-cards/{code}/transactions` — ledger by ascending createdAt.
  - `GET /v26/gift-cards?status=...` — list (optional status filter).
  - `GET /v26/gift-cards/lookup/{code}` — back-fills legacy cards with `currentBalance`.
  - `POST /v26/gift-cards/sell` — counter sale activates immediately + writes ledger; online channel lands as pending.
- **AI Marketing Email engine**:
  - `POST /v26/marketing/email/generate` — LLM (`emergentintegrations` GPT-5.2) drafts a complete email featuring upcoming events, active vouchers, and tier perks. Audience-aware, tone-aware, horizon-aware. Persisted as `draft` in `db.marketing_emails`.
  - `GET /v26/marketing/emails` · `PATCH /v26/marketing/emails/{id}` · `DELETE /v26/marketing/emails/{id}`.
- **Customer Display live push**:
  - `POST /v26/cfd/push` — POS pushes live cart + customer to `db.cfd_live` (keyed by terminalId).
  - `GET /v26/cfd/enriched?terminalId=...` — returns the pushed feed enriched with customerName, tableNumber, pointsEarned/missed; falls back to `pos_tabs` when no live feed.

### Backend update (`routes/v15_features.py`)
- `POST /staff/auto-roster` now consumes `db.staff_availability`:
  - Filters out staff whose weekly availability excludes the day or whose blackoutDates cover that calendar date.
  - Response gains an `excluded[]` array `{staffId, staffName, date, reason}` and reasoning string reports exclusion count.

### Backend update (`routes/v25_suite.py`)
- `POST /v25/subscriptions/plans` now mints a scannable manualCode + barcode (`SUB-XXXX-XXXX`), accepts `inclusions[]`, `termsAndConditions`, `trialDays`, `priceAnnual`.

### Frontend additions
- **POSContext.js** — added `appliedGiftCards` tender array and `pendingGiftActivations` queue. `calculateTotal()` returns both `total` (gross) and `balanceDue` (after gift-card tenders) so cash/QR/UPI/Stripe only charge the remainder.
- **POSTerminal.jsx**:
  - "🎁 Apply" gift-card input inside the discount picker. Looks up the card, auto-tenders min(balance, balanceDue).
  - Totals panel shows applied gift cards as violet chips with × to remove + a "Balance due (after gift cards)" line.
  - `settleGiftCards()` runs after every successful checkout (standard / QR / UPI / Split) and: activates any pending-sold cards, redeems applied tenders, all via the ledger endpoints.
  - Live cart pushed to `/v26/cfd/push` 400ms-debounced on every cart/customer change.
- **V26Pages.jsx**:
  - `VoucherManager.save()` surfaces the auto-minted gift-card code in a toast when `kind=gift`.
  - **New `MarketingEmails` page** (`/marketing-emails`) — generate · list drafts · edit subject/preheader/body/sms/cta · delete (owner only). Bottom Dock entry added under Enterprise.
- **api.js** — `v26API` extended: `listGiftCards`, `activateGift`, `redeemGiftPartial`, `giftTransactions`, `generateMarketingEmail`, `listMarketingEmails`, `updateMarketingEmail`, `deleteMarketingEmail`, `cfdPush`.

### Test status (Iteration 25 + 26)
- **Backend**: 19/19 PASS (`/app/test_reports/iteration_25.json`) — full gift-card lifecycle, ledger correctness, AI marketing CRUD, blackout-aware roster, live CFD.
- **Frontend**: 6/6 PASS (`/app/test_reports/iteration_26.json`) — gift card chip in POS totals, voucher creation toast, marketing email generator + editor, bottom-dock entry.

### Known status
- License enforcement remains feature-flagged OFF for dev (`LICENSE_ENFORCEMENT_ENABLED=false`).
- P2 backlog items (offline-first sync, kiosk mode, smart 86/substitution) have working MVP backend + frontend stubs from earlier iterations — production-grade refinement still backlogged.

