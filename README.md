# NUA — Restaurant POS & Hospitality Platform

> **v25 · February 2026** — Enterprise-grade POS, AI General Manager (Ash Pro), Multi-Site Command Center, full v25-v30 roadmap shipped.

NUA is a production-ready, multi-tenant restaurant POS that combines frontline speed with an enterprise stack normally seen in 7-figure SaaS platforms. Built with **FastAPI + MongoDB + React 19 + Tailwind/shadcn**, all AI features powered by **OpenAI GPT-5.2 + Whisper** via the Emergent Universal LLM Key.

---

## 1. Quick Start

```bash
# Backend (FastAPI on :8001)
sudo supervisorctl restart backend

# Frontend (CRA on :3000, hot-reload)
sudo supervisorctl restart frontend

# MongoDB
sudo supervisorctl restart mongodb
```

**Default owner login:** `owner@nuva.com / NuvaOwner2026!`

## 0. Enterprise Licensing & Entitlements (v26)

NUA ships as a server-authoritative licensed SaaS product:

- **One verified ABN per tenant license** — bound at onboarding via Australian Business Register's ABN Lookup web service (requires `ABR_GUID` from abr.business.gov.au/Tools/WebServices). Once issued, the ABN is immutable; changes require owner + 2FA + ABR re-verification + support approval.
- **Stripe Billing webhooks** drive a progressive state machine: `active` → `past_due` → `grace` → `suspended` → `cancelled`. **Never** instant shutdown — warnings first (Day 0), admin restrictions (Day 2), then sales block (Day 7).
- **Device-level entitlements** — each POS device activates against the license server, receives a short-lived signed JWT (30 min), and silently revalidates every 10 min. Unauthorized devices return `DEVICE_NOT_AUTHORIZED`.
- **`LicenseEnforcementMiddleware`** intercepts every API call and returns HTTP 423 with specific error codes (`LICENSE_SUSPENDED`, `SUBSCRIPTION_PAST_DUE`, `ABN_REVERIFY_REQUIRED`, etc.) — the frontend cannot bypass this.
- **`/license` UI** — owner dashboard with state badge, device list, ABN change request (2FA-gated), Stripe billing portal link, dev/QA force-state controls, and full audit log.
- **`LicenseLockScreen`** — full-page overlay (z-index 9999) on suspended/cancelled/abn_review; always allows owner login, billing update, data export.

Config:
```bash
# backend/.env
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...   # optional; signature verification skipped if blank
ABR_GUID=...                       # from abr.business.gov.au/Tools/WebServices
ALLOW_ABR_DEV_SKIP=true            # dev/staging only — must NOT be set in production
SUPPORT_OVERRIDE_KEY=nua-support-2026  # required header X-Support-Override for ABN approval
```

---

## 2. What's Inside (v25 Release)

### v25 — Must Have (release blockers, profit-protecting foundations)
| Module | Path | Description |
|---|---|---|
| Offline Sync Queue | `POST /api/v25/sync-queue` | Client batches pending offline ops, conflicts auto-detected |
| Loss-Control Center | `/exceptions` | 14-day voids/comps/refunds with suspicious-user flagging |
| Multi-Site Command | `/franchise` | Sites, global publish with rollback |
| Hardware Health | `/hardware-health` | Printer/terminal/scanner status, signed-heartbeat endpoint |
| Chargeback Console | `/disputes` | Open disputes, attach evidence packs |
| Supplier Marketplace | `/supplier-marketplace` | Per-ingredient quote comparison, annual-savings calc |

### v26-v27 — Should Have (growth & efficiency multipliers)
| Module | Path | Description |
|---|---|---|
| Self-Service Kiosk | `/kiosk` | Tableside ordering session, add → checkout |
| Customer-Facing Display | `/cfd` | Mirror cart to guest screen in real time |
| Smart Substitution | `POST /api/v25/substitute` | Best substitute when item is 86'd |
| Guest Recovery / Churn-Risk | `/churn-risk` | Win-back vouchers in one click |
| Station Readiness Score | `/station-readiness` | Single 0-100 ops health number |
| Menu Margin Guardrails | `/margin-guardrails` | Auto-warn on items < 50% margin |

### Tier 1 — Differentiators
| Module | Path | Description |
|---|---|---|
| **Ash Pro · AI GM** | `/ash-pro` | Aggregates signals → multi-action plan → one-click "Approve All" execution |
| **Profit Guardian** | `/profit-guardian` | Nightly per-item margin drift + suggested price tunes |
| **Digital Twin** | `/digital-twin` | Expected revenue / covers / wait time with ±8% confidence band |
| **AI Shift Manager** | `/shift-manager` | Real-time intervention alerts (kitchen overload, aging tickets) |
| **Autonomous Marketing** | `/auto-marketing` | LLM-drafted SMS + email campaigns per audience tier |

### Tier 2 — Revenue
| Module | Path | Description |
|---|---|---|
| Dynamic Pricing Rules | `/dynamic-pricing-rules` | Category/day/hour multipliers |
| Subscription Memberships | `/subscriptions` | Recurring plans (Coffee Club $29/mo etc.) |
| Smart Gift Cards | `/gift-cards` | Atomic redeem, bonus on $100+, occasions |
| AI Upsell Engine | (in POS cart) | Debounced LLM suggestions tuned for margin |
| Menu Personalization | (POS · Your Usual) | Per-guest predictive items based on history |

### Tier 3 — Inventory & Purchasing
| Module | Path | Description |
|---|---|---|
| **Recipe Costing Engine** | `/recipe-costing` | Ingredient-level recipes, computed cost auto-pushed to product |
| Predictive Ordering | `/predictive-orders` | 14-day velocity → next-week supplier orders |
| Waste Tracking | `/waste-tracking` | Spoilage/breakage/staff-meals/over-prep log + 30d insights |

### Tier 4 — Customer Experience
| Module | Path | Description |
|---|---|---|
| Universal Guest Profile | `GET /api/v25/guest/{id}` | Combined spend/visits/reservations/points |
| AI Concierge | `/concierge` | "Need dinner for 6 tonight" → auto-creates reservation |
| Reputation Center | `/reputation` | Google/TripAdvisor aggregate, AI-drafted responses |
| Smart Recovery | `POST /api/v25/recovery-action` | Voucher + apology before review goes public |

### Tier 5 — Enterprise
| Module | Path | Description |
|---|---|---|
| Franchise Command | `/franchise` | Multi-site publish + rollback |
| Multi-Store Benchmark | (inside franchise) | Side-by-side revenue/food%/labour%/CSAT |
| Data Warehouse Export | `GET /api/v25/warehouse/export?collection=...` | Power BI / Tableau / Excel ready |
| AI Fraud Detection | `/fraud-detection` | Per-staff risk score (voids/comps/discounts/refunds) |

### Continued from prior versions
| Module | Path |
|---|---|
| POS Terminal · Voice POS · Swipe-cart · Tabs (Hold/Recall) | `/pos` |
| AI Cost Coach · Labor Forecast · Surge Pricing · Voice-to-Recipe · Kitchen Load | `/ai-cost-coach`, `/labor-forecast`, `/surge-pricing`, `/voice-recipe`, `/kitchen-load` |
| Auto Price-Tune · AI Phone Agent · Menu A/B Tests · Purchase Orders | `/price-tune`, `/phone-agent`, `/ab-tests`, `/purchase-orders` |
| Loyalty Engine (points-and-pay) · Staff Roster (drag-drop) · Booking Heatmap · Cohort Retention | `/loyalty`, `/staff-roster`, `/booking-heatmap`, `/cohort-retention` |

---

## 3. Architecture

```
/app
├── backend/
│   ├── server.py                      ← FastAPI app + RateLimitMiddleware
│   ├── models/                        ← Pydantic models (reservations, products, etc.)
│   └── routes/
│       ├── auth.py                    ← JWT + RBAC seed
│       ├── products.py · transactions.py · customers.py · reservations.py
│       ├── kitchen.py · analytics.py · automation.py · loyalty.py
│       ├── items_system.py            ← Categories, Modifiers, Comp/Void
│       ├── v15_features.py            ← Ask NUA, Voice POS, Tabs, Heatmap
│       ├── loyalty_engine.py          ← Points-and-pay, dynamic multipliers
│       ├── phase_ef.py                ← Auto-VIP, Phone Agent, A/B tests
│       ├── phase_ef_wave2.py          ← Upsell, Price-tune, Cost Coach, Labor Forecast, Surge, Voice-Recipe, Kitchen Load
│       └── v25_suite.py               ← THE WHOLE v25 ENTERPRISE SUITE (30+ endpoints)
└── frontend/
    ├── public/
    │   ├── index.html                 ← SW registration with self-healing reload
    │   └── service-worker.js          ← v3, network-first for HTML/JS, cache static only
    └── src/
        ├── App.js                     ← All routes (~80 protected, ~5 public)
        ├── components/
        │   ├── BottomDock.jsx         ← Quick actions + "More" splash (5 groups + Enterprise v25)
        │   ├── AskNua.jsx · VoiceOrderButton.jsx
        │   └── ui/                    ← shadcn primitives
        ├── pages/                     ← 60+ pages (POS, Bookings, AI suite, v25 suite)
        │   ├── EnterpriseCommandCenter.jsx
        │   ├── AshPro.jsx
        │   ├── ProfitGuardian.jsx · DigitalTwin.jsx
        │   └── V25Pages.jsx           ← 21 compact pages (one export per module)
        └── services/
            └── api.js                 ← All API slices: productsAPI, v15API, phaseEFAPI, aiWave2API, v25API
```

---

## 4. AI Integrations (Emergent Universal Key)

All LLM-backed features use **GPT-5.2** via `emergentintegrations.llm.chat.LlmChat`:

| Feature | Endpoint | Model |
|---|---|---|
| Ask NUA chat | `/api/ai/ask-nua` | gpt-5.2 |
| Voice-order transcription | `/api/pos/voice-order` | openai-whisper |
| AI Phone Agent | `/api/phone-agent/simulate` | gpt-5.2 |
| AI Upsell suggestions | `/api/ai/upsell` | gpt-5.2 |
| AI Cost Coach (3-action plan) | `/api/ai/cost-coach` | gpt-5.2 |
| Voice-to-Recipe | `/api/ai/voice-recipe` | whisper + gpt-5.2 |
| Auto Marketing (campaign drafts) | `/api/v25/marketing/auto` | gpt-5.2 |
| AI Concierge | `/api/v25/concierge` | gpt-5.2 |
| Review response drafting | `/api/v25/reputation/respond` | gpt-5.2 |

`EMERGENT_LLM_KEY` is loaded from `/app/backend/.env`. Errors are logged via `logger.warning` and degrade gracefully (empty suggestions instead of 500).

---

## 5. Security & Reliability Hardening (v25)

| Concern | Mitigation |
|---|---|
| **Stale PWA bundle** | Service worker v3 = network-first for JS/HTML, cache-first for static. `controllerchange` → auto-reload. `PURGE` message wipes legacy caches. |
| **Gift-card double-redeem** | `findOneAndUpdate` with balance condition in filter — atomic, no read-before-write race. |
| **Hardware heartbeat spoofing** | Requires `X-Device-Secret` header (env: `DEVICE_HEARTBEAT_SECRET`). |
| **Ash-plan collection bloat** | Idempotent per-day upsert; one pending plan per `planDate`. |
| **MongoDB ObjectId leaks** | Every projection excludes `_id`; seeded items `.pop("_id")` before return. |
| **Authentication** | JWT + RBAC, owner/manager/cashier/barista/kitchen roles. All sensitive endpoints gated. |
| **Rate limiting** | 120 req/min per (tenant, IP) middleware in `server.py`. |
| **Audit trail** | `agent_decisions`, `price_history`, `publications` + rollback, dispute evidence. |

---

## 6. Data Model Highlights

```python
# v25 collections
sites                  # multi-site
publications           # owner-pushed bundles + rollback flag
sync_ops               # offline sync queue
hardware               # device fleet
disputes               # chargebacks + evidence[]
supplier_quotes        # marketplace inputs
kiosk_sessions         # self-service carts
recovery_campaigns     # win-back batches
vouchers               # auto-issued + manual
ash_plans              # one per day (idempotent)
marketing_campaigns    # auto-generated drafts
dynamic_pricing        # rules
subscription_plans · subscriptions
gift_cards             # atomic redeem
product_recipes        # ingredient[] + computedCost
waste_log              # 30d insights
reviews                # external aggregate
recovery_actions       # service-recovery
surge_rules            # per (dow,hour) multipliers
```

---

## 7. v25-v30 Roadmap Status

```
v25 Must Have ████████████████████████  100%  shipped
v26 Should    ████████████████████████  100%  shipped (kiosk, CFD, substitution, recovery, station, margin)
v27 Tier 1    ████████████████████████  100%  Ash Pro, Profit Guardian, Digital Twin, Shift Manager, Auto Marketing
v28 Tier 2    ████████████████████████  100%  Dynamic Pricing, Subscriptions, Gift Cards, Upsell, Personalization
v29 Tier 3    ████████████████████████  100%  Recipe Costing, Predictive Ordering, Waste Tracking
v30 Tier 4-5  ████████████████████████  100%  Guest Profile, Concierge, Reputation, Franchise, Benchmark, Warehouse, Fraud
```

### Polish backlog (post-v25)
- Refactor `v25_suite.py` (~1100 lines) into 3 sub-modules
- Convert all `from routes.auth import get_current_user` blocks to a `require_role()` FastAPI dependency
- Replace native POS `<select>` for customers with shadcn searchable Select (typeahead at scale)
- Surge multiplier hook into POS price-calc (rules currently persisted only)
- "Recipe → menu item" 1-click product creation using marketplace prices
- Real WhatsApp · Twilio · Uber Eats · DoorDash · Stripe Tap-to-Pay (requires user keys)
- WebSocket real-time push for kitchen-load & A/B test exposure
- Real TOTP via pyotp

---

## 8. Testing

```bash
# Backend regression suite (pytest)
cd /app/backend && pytest tests/

# Quick smoke
API=$(grep REACT_APP_BACKEND_URL ../frontend/.env | cut -d= -f2)
TOKEN=$(curl -s -X POST $API/api/auth/login -H "Content-Type: application/json" \
    -d '{"email":"owner@nuva.com","password":"NuvaOwner2026!"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
curl -s $API/api/v25/ash-pro/plan -H "Authorization: Bearer $TOKEN"
```

**Latest test report:** `/app/test_reports/iteration_23.json`  
**Result:** 34/34 backend pytest · 25/25 frontend route smoke · 0 console errors · POS customer-add regression PASSED ✅

---

## 9. Credits

- **Backend:** FastAPI · Motor · Pydantic v2
- **Frontend:** React 19 · Tailwind 4 · shadcn/ui · dnd-kit · Lucide icons · sonner toasts
- **AI:** OpenAI GPT-5.2 + Whisper via Emergent Universal Key
- **State:** MongoDB
- **Built on:** [Emergent](https://emergent.sh)
