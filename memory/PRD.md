# NUA POS — PRD v26.0 (Enterprise Licensing & Entitlements)

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
- `AshPro.jsx` — Signals + actions + Approve All (one-click executor)
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
- Refactor: Split POSTerminal.jsx (~950 lines) into Cart/Payment/QR sub-components, structured react-router config, real TOTP via pyotp
- Surge pricing apply to live POS prices (currently only persisted) — hook into product price calc
- Recipe → menu item: 1-click convert /voice-recipe generated spec into a product with cost-rolled-up from ingredient prices
- Auto-swap-finder + auto-EOD-email (Phase E next wave residual)
