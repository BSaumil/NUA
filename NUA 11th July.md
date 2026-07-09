# NUA — Restaurant Operating System
**Snapshot · 11 July 2026**

> _NUA (formerly “Nua POS”) is an enterprise-grade, AI-native hospitality operating system._
> _What began as a fluid point-of-sale for a single café is now a full **Customer Commerce Platform**_
> _covering front-of-house, back-of-house, marketing, payroll, compliance and loyalty — with an_
> _AI copilot (Ash) sitting on top of every workflow._

---

## Table of contents
1. [What NUA is](#what-nua-is)
2. [Vision & positioning](#vision--positioning)
3. [The 12-month build story (Day 1 → Day 300)](#the-12-month-build-story)
4. [Feature catalogue](#feature-catalogue)
5. [Architecture](#architecture)
6. [Key data models](#key-data-models)
7. [API surface](#api-surface)
8. [Running NUA locally](#running-nua-locally)
9. [Deployment](#deployment)
10. [Testing & compliance](#testing--compliance)
11. [Roadmap](#roadmap)
12. [Credits](#credits)

---

## What NUA is

NUA is a single web application that a restaurant / café / bar / QSR / franchise HQ runs
their entire business on:

- **Front-of-house** — POS, floor plan, bookings, guest CRM, digital wallet.
- **Back-of-house** — inventory, AI pantry, KDS, print routing, temperature monitoring,
  supplier management, pre-shift briefings.
- **Marketing** — unified channel menus, social calendar, email/SMS campaigns, unified
  voucher engine, AI promotion builder.
- **Accounting** — full BAS/GST worksheet (NAT 4189), Fair-Work-compliant payroll with ATO
  Schedule 1 PAYG, tiered Super Guarantee, STP2 export.
- **Customer Commerce Platform** — universal vouchers, unified wallet ledger,
  loyalty 2.0 with milestones/streaks, AI personalisation, flexible refunds.
- **Enterprise** — multi-tenant, multi-location, licensing & entitlements, roles,
  audit log, deployment tooling for Fly.io / Railway / Docker.

Every value movement (points, credit, gift card, voucher, cashback, referral, refund) is a
**signed ledger entry** — single source of truth, complete audit trail, one QR to rule them all.

---

## Vision & positioning

> **“One place to run every guest interaction, every value exchange, every regulator obligation.”**

Most hospitality platforms bolt vouchers onto CRMs, refunds onto POS, payroll onto spreadsheets,
loyalty onto marketing tools. NUA’s design principle is **the opposite**: one signed ledger,
one voucher engine, one AI copilot — everything else is a UI over that.

| Layer | Product name | Design principle |
|---|---|---|
| Value | **NUA Wallet** | Every $ / point / voucher / gift is a signed ledger entry. |
| Redemption | **Universal Voucher Engine** | One QR standard for promos, refunds, gifts, referrals, birthdays, staff, corporate, event. |
| Copilot | **Ash AI** | Sits on POS, marketing, roster, payroll, pantry, promotions. |
| Compliance | **AU-native** | ATO Schedule 1 PAYG, tiered SG, Fair Work Modern Award, NES leave, BAS NAT 4189, STP2. |
| Deploy | **Container-first** | Fly.io / Railway / Docker Compose / GitHub Actions auto-deploy. |

---

## The 12-month build story

### v1.0 → v10.0 — POS foundation
- Fluid POS grid, categories, modifiers, allergens, dietary flags, printer/EFTPOS wiring.
- Floor plan with drag/drop tables, multi-locations, roles, PIN login, RBAC.
- Cash drawer, End-of-Day reconciliation, refunds, split payments, tips.

### v11.0 → v17.0 — CRM + Marketing + Compliance
- Customer CRM with tags, dietary prefs, feedback capture, LTV.
- Loyalty & Events (tier + points + referral).
- BAS/GST report shell, Superannuation calculations, Fair Work award catalogue.
- Multi-tenant licensing & entitlements.

### v18.0 → v24.0 — AI operations
- Ash AI (Gemini/GPT via Emergent Universal Key) integrated with POS, forecasting,
  inventory, sentiment.
- AI Pantry (image → items → allergens → cost).
- Voice notes for staff, AI review responses, sales copilot.

### v25.0 → v26.0 — Wave-2 features + Bookings AI
- Reservations + AI Booking Inbox (parse Insta DMs / SMS / email into structured bookings).
- Waitlist, table courses, seat-me flow, KDS enhancements.
- Enterprise licensing gates.

### v27.x → v28.x — Deployment, deep polish, AU compliance
- Deploy docs (Fly.io / Railway / Docker Compose / GitHub Actions).
- Editable subscriptions, seeded demo customers.
- Temperature monitoring (Bluetooth simulated), Pre-shift briefings, Print routing fix.
- Floor plan **Send-to-Table**, POS Cart UX overhaul.
- PDF exports for Low Stock + AI Pantry.
- **Iter 45**: `/api/settings/locations` defensive parse; AI Bookings Inbox merged into
  Reservations; Guest Digital Wallet QR; Automation Triggers with AI Suggest;
  Settings > Locations extended (logo, GMB, hours).
- **Iter 46**: `utils/mongo_safe.py` refactor; Booking Source Attribution strip;
  real Apple `.pkpass` + Google Wallet save-link; @dnd-kit migration for Social Calendar
  (touch-ready); Channel Menus per-channel pause/resume/schedule.
- **Iter 47**: Bundle & Category multi-select promotions (`pricingMode: percentage | fixed_price`,
  `bundlePrice`, `categories[]`, `minQuantity`, `maxQuantity`, `stackable`).
- **Iter 48**: **Australian Payroll compliance engine** (`utils/au_payroll.py` — ATO Sch 1,
  tiered SG, penalty matrix, NES leave, STP2 event shape, roster compliance checker).
  Full BAS worksheet endpoint (G1–G20 + W1–W5 + T1). Payroll page (Pay Run / Register /
  Roster Compliance tabs). Wallet Credentials Settings tab. **AI Bundle Discovery**
  (market-basket Apriori-lite → proposed price with 33 % margin floor).

### v29.0 — Customer Commerce Platform (Iter 49 – 50 · 9 Jul 2026)
The strategic milestone. NUA moves beyond “POS with add-ons” into a unified customer-value
platform:

- **Universal Voucher Engine** — every offer, gift, refund, referral, birthday, staff, corporate
  or event issue creates a voucher with signed QR + human-readable code + full audit trail.
  Prevents double redemption, supports partial retention, bulk issue.
- **Unified Wallet Ledger** — one `wallet_ledger` collection, six buckets (points, store credit,
  gift card, voucher, cashback, referral). Every movement snapshots `balanceAfter`.
- **Flexible Refund Engine** — split refunds across card / store credit / points / voucher in
  one action. Each split writes the correct ledger entry and auto-issues a voucher where relevant.
- **AI Promotion Builder** — plain-English goal → complete campaign (name, voucher, targeting,
  SMS + email copy, ROI estimate).
- **Loyalty 2.0** — Bronze → VIP tiers, 6 auto-awarded milestones, weekly streaks.
- **AI Personalisation** — per-customer favourite items + typical visit pattern → tailored offers.
- **Gift Card 2.0** — scheduled delivery, reload, personal messages.
- **Customer Journey Timeline** — one merged feed of bookings + orders + refunds + ledger +
  vouchers + reviews with LTV.

**Iter 49-50 tests**: 35/35 backend + all 6 frontend surfaces PASS · zero regressions.

---

## Feature catalogue

### Front of house
| Feature | Path | Notes |
|---|---|---|
| POS Terminal | `/pos` | Fluid grid, modifiers, allergens, split, tips, cart send-to-table |
| Floor Plan | `/floor-plan` | Drag & drop, courses, seat-me, table info drawer |
| Bookings + AI Inbox | `/reservations` | Unified tabs, source attribution strip |
| KDS | `/kds` | Course-timed tickets, print routing |
| Guest Wallet (POS) | inline | QR scan → auto-add customer, redeem voucher |

### CRM & Commerce
| Feature | Path | Notes |
|---|---|---|
| Customer List / Profile | `/customers` | Embedded **CustomerWalletPanel** (v29) |
| Universal Vouchers | `/vouchers` | Analytics + AI builder + QR + audit |
| Loyalty & Events | `/loyalty` | Milestones + streaks + tiers |
| Marketing Umbrella | `/marketing` | Social calendar, email/SMS, campaigns |
| Channel Menus | `/channel-menus` | Per-channel pause/resume/schedule |

### Kitchen / Back of house
| Feature | Path | Notes |
|---|---|---|
| Products, Recipes, Modifiers | `/products` | Bulk edit, Promotion Dialog with AI Bundle Discovery |
| Inventory + AI Pantry | `/inventory` | Low stock PDF, image → items |
| Temperature Monitoring | `/temperature` | Bluetooth-simulated devices + alerts |
| Pre-Shift Briefing | `/pre-shift` | Daily focus + AI briefing |
| Print Routing | `/print-routing` | Legacy dict → array migration |
| Suppliers | `/suppliers` | Purchase orders |

### Accounting & Compliance (AU-native)
| Feature | Path | Notes |
|---|---|---|
| Accounting | `/accounting` | Transactions + new **RefundDialog** with split modes |
| BAS/GST | `/bas-gst` | Full **NAT 4189 worksheet** (G1–G20 + W1–W5 + T1) |
| Payroll | `/payroll` | ATO Sch 1 PAYG + tiered SG + Fair Work rules + STP2 |
| Super | `/super` | Fair Work integration for super run |
| End of Day | `/end-of-day` | Cash reconciliation |

### Enterprise
| Feature | Path | Notes |
|---|---|---|
| Settings | `/settings` | Locations (logo/GMB/hours), Wallet Passes tab (Apple + Google) |
| Automation Engine | `/automation` | Event-driven rules |
| Automation Triggers | `/automation-triggers` | Owner-defined + AI-suggested |
| Audit Log | `/audit-log` | Every mutation |
| Multi-Tenant / Licensing | internal | Entitlements middleware |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│ React 19 + Tailwind + shadcn/ui + qrcode.react + @dnd-kit + lucide-react │
│  ⇅  process.env.REACT_APP_BACKEND_URL                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ FastAPI (Python 3.11) — 45+ routers                                      │
│  ├── /api/vouchers        Universal Voucher Engine                       │
│  ├── /api/wallet          Unified Wallet Ledger                          │
│  ├── /api/refunds/flexible  Split-mode refunds                           │
│  ├── /api/payroll         AU compliance (ATO Sch 1, SG, Fair Work, STP2) │
│  ├── /api/bas-gst         Full NAT 4189 worksheet                        │
│  ├── /api/v26/*           Legacy commerce (promotions, cart, etc.)       │
│  ├── /api/ai/*            Emergent Universal LLM Key                     │
│  └── … (customers, products, reservations, loyalty, etc.)                │
├─────────────────────────────────────────────────────────────────────────┤
│ MongoDB (Motor / AsyncIOMotorClient)                                     │
│  Collections: vouchers · wallet_ledger · loyalty_awards · payruns ·      │
│  payrun_rows · stp_events · transactions · customers · products ·        │
│  reservations · floor_plans · shifts · timecards · locations ·           │
│  business_settings · wallet_credentials · promotions · automation_       │
│  triggers · channel_states · gift_cards · feedback · … (~60 total)       │
├─────────────────────────────────────────────────────────────────────────┤
│ Emergent Universal LLM Key                                               │
│  • openai/gpt-4o-mini · gpt-5.2 · Gemini 3.5 Flash · Claude Sonnet 4.5    │
│  • Used by Ash AI, AI Booking Inbox, AI Promotion Builder, AI Pantry,    │
│    AI Bundle Discovery, AI Personalisation.                              │
├─────────────────────────────────────────────────────────────────────────┤
│ Supervisord managed processes (backend :8001 · frontend :3000)           │
│ Ingress: /api/* → 8001 · /* → 3000                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key architectural principles
1. **Signed ledger of truth** — every value movement writes an entry (never mutate balances).
2. **Defensive Mongo reads** — `utils/mongo_safe.py::safe_parse_list` coerces / drops legacy
   docs so one bad row can never 500 a list endpoint.
3. **Signed QR everywhere** — HMAC-SHA256 with `JWT_SECRET`; never displayed secrets.
4. **Compliance-grade math** — payroll uses ATO Schedule 1 coefficients, SG tiers, Fair Work
   penalty matrix from `utils/au_payroll.py`.
5. **Emergent Universal LLM Key** — no per-vendor SDK, single key across GPT/Gemini/Claude.

---

## Key data models

### Voucher (v29)
```python
{
  id, code: "NUA-XXXX-XXXX", qrPayload: "<hmac-signed>",
  sourceType: "promotion|refund|gift_card|referral|birthday|anniversary|
               staff|corporate|event|manual",
  sourceRef, label, description,
  valueType: "amount|percentage|free_item|tier_upgrade",
  value, faceValue, residualValue,
  usageType: "one_time|multi_use|unlimited",
  maxRedemptions, redemptionCount, partialRedeemable,
  customerId, customerEmail, customerName,
  rules: { startDate, endDate, activeDays[], startTime, endTime,
           happyHourOnly, firstVisitOnly, clubMembersOnly,
           minMembershipTier, minSpend, maxDiscount,
           eligibleItems[], eligibleCategories[], excludeItems[], excludeCategories[],
           locationIds[], deliveryChannels[], seatingAreas[], bookingSources[] },
  status: "active|partial|redeemed|expired|revoked",
  issuedAt, issuedBy, expiresAt, revokedAt, revokedBy, revokeReason,
  redemptions: [ { id, at, amount, staffId, staffName, terminalId,
                    transactionId, locationId, note } ],
  metadata: {}
}
```

### Wallet Ledger (v29)
```python
{
  id, customerId, type: "points|store_credit|gift_card|voucher|cashback|referral",
  sign: +1|-1, amount, balanceAfter,
  sourceType, sourceRef, note, createdAt, metadata: {}
}
```

### Payrun row (v28)
```python
{
  runId, staffId, name, role, employmentType, hoursWorked, baseHourly,
  ordinaryPay, penaltyPay, overtimePay, allowances, grossPay,
  payg, paygScale, ote, sgRate, super, netPay,
  leaveAccrual: { annual, personal, lsl },
  ytdGross, ytdTax, ytdSuper, payDate, period
}
```

### Promotion (v28.0 bundle-aware)
```python
{
  id, name, type: "category|bundle|mixed",
  pricingMode: "percentage|fixed_price",
  discount, bundlePrice, minQuantity, maxQuantity, stackable,
  products[], category, categories[],
  startDate, endDate, activeDays[], startTime, endTime, schedule, active
}
```

---

## API surface

### Universal Voucher Engine
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/vouchers` | Issue single voucher |
| POST | `/api/vouchers/bulk` | Bulk issue (corporate/event/staff) |
| GET | `/api/vouchers?status=&customer_id=&source_type=` | List with filters |
| GET | `/api/vouchers/{id}` | Full document + audit |
| GET | `/api/vouchers/lookup/{code}` | Resolve human code |
| POST | `/api/vouchers/validate` | Pre-flight (no redeem) |
| POST | `/api/vouchers/redeem` | Apply against a transaction (409 on dupe) |
| POST | `/api/vouchers/{id}/revoke` | Owner/manager revocation |

### Unified Wallet
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/wallet/{customerId}` | Balances + vouchers + expiring soon |
| POST | `/api/wallet/{cid}/credit` | Add value to any bucket |
| POST | `/api/wallet/{cid}/debit` | Deduct (with balance guard) |
| GET | `/api/wallet/{cid}/timeline` | Merged journey feed |

### Refund + AI + Loyalty + Personalisation
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/refunds/flexible` | Split-mode refund |
| POST | `/api/ai/promotion-goal` | Goal → complete campaign |
| GET | `/api/promo-analytics/summary?days=30` | Voucher analytics |
| GET | `/api/loyalty/status/{cid}` | Tier + milestones + streaks + badges |
| POST | `/api/loyalty/award` | Grant a manual badge/milestone |
| GET | `/api/personalisation/{cid}` | Per-customer recommendations |
| POST | `/api/gift-cards/schedule` | Deferred gift card |
| POST | `/api/gift-cards/{voucherId}/reload` | Top up an existing gift card |

### Payroll & Compliance
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/payroll/payrun/calculate` | Award-aware pay-run calc |
| POST | `/api/payroll/payrun/commit` | Persist + auto STP2 event |
| GET | `/api/payroll/register?days=90` | Pay-run history |
| GET | `/api/payroll/ytd/{staffId}` | Year-to-date summary |
| GET | `/api/payroll/payslip/{runId}/{staffId}/pdf` | Fair Work-compliant PDF |
| POST | `/api/payroll/stp/build` | STP2 event body |
| GET | `/api/payroll/roster-compliance?days_ahead=14` | Fair Work / Award violations |
| GET | `/api/bas-gst/worksheet?period_start=&period_end=` | Full NAT 4189 worksheet |
| GET,POST | `/api/settings/wallet-credentials` | Apple/Google wallet env plumbing |

### Commerce
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v26/cart/apply-promos` | Auto-apply active promos (fixed price + %) |
| GET | `/api/v26/promotions/bundle-suggestions?days=30` | AI market-basket bundle discovery |
| … | (see `routes/`) | 45+ additional endpoints |

Full auto-generated OpenAPI: `GET /api/openapi.json`.

---

## Running NUA locally

### Prerequisites
- Docker + Docker Compose _or_ Python 3.11, Node 20, MongoDB 6+.

### With Docker Compose
```bash
docker-compose up -d
# MongoDB on :27017, backend :8001, frontend :3000
open http://localhost:3000
```

### Native
```bash
# Backend
cd /app/backend
pip install -r requirements.txt
sudo supervisorctl restart backend        # supervisord manages uvicorn on :8001

# Frontend
cd /app/frontend
yarn install
sudo supervisorctl restart frontend       # supervisord manages CRA dev on :3000
```

### Environment
- `backend/.env` — `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `EMERGENT_LLM_KEY`.
- `frontend/.env` — `REACT_APP_BACKEND_URL`.
- **Wallet passes** — paste Apple certs + Google service account into the new
  Settings → Wallet Passes tab (persisted to DB + re-applied on startup).

### Default credentials
```
owner@nuva.com  /  NuvaOwner2026!
```

---

## Deployment

Complete guides live at the repository root:
- `For Sam.md` — plain-English handover.
- `Fly.io Setup.md` — Fly.io recipe.
- `Railway Setup.md` — Railway recipe.
- `Docker Local Setup.md` — Docker Compose recipe.
- `Auto Deploy Setup.md` — GitHub Actions CI/CD.
- `deploy.sh` — one-shot deploy script.
- `docker-compose.yml` — production compose file.

---

## Testing & compliance

- Backend tests live under `/app/backend/tests` (pytest).
- End-to-end + smoke coverage via the `testing_agent_v3_fork` framework — 50 iteration reports
  in `/app/test_reports/iteration_{n}.json` (latest: **35/35 backend + 6 frontend surfaces PASS**).
- Payroll math verified against ATO Schedule 1 (Nov 2023), SGAA (SG tiers), Fair Work
  Modern Awards MA000009 / MA000119.
- BAS worksheet uses ATO NAT 4189 field labels verbatim.
- Voucher tokens signed with HMAC-SHA256 (`JWT_SECRET`); duplicate-redemption guard on
  transactionId; partial residual tracked to 2 dp.

---

## Roadmap

### Next up
- **P1** — Real Meta / TikTok / X OAuth (needs client IDs & secrets).
- **P1** — SendGrid + Twilio production keys to activate SMS + email in AI campaigns.
- **P1** — User to paste real Apple Pass Type ID certs + Google Wallet service account
  key via Settings → Wallet Passes (flips loyalty passes from **preview** → **production-signed**).

### Backlog
- Auto-lodge weekly payroll workflow (Monday email → one-click Approve & Lodge STP2).
- Real STP2 SBR2 submission (needs ATO software ID + SSL cert).
- SuperStream clearing-house contribution export.
- Wallet auto-refresh via APNs push (Apple) + Google Wallet update push.
- AI Profit Guardian (recommends price / cost adjustments).
- Recipe costing with live GP per item + supplier price marketplace.
- Franchise HQ dashboard with centralised control.
- HACCP food safety compliance logs.
- Customer-facing mobile app (wallet, bookings, ordering, rewards).
- Corporate accounts with monthly invoicing + spending limits.
- Multi-country compliance switch (US 941/W-2, UK PAYE/RTI).
- Customer "Trust Score" (0-100) per guest — spend velocity + streak + refund ratio +
  voucher pattern + sentiment + no-show rate.

---

## Credits

- **Built with** — React 19, FastAPI, MongoDB, Tailwind, shadcn/ui, lucide-react,
  qrcode.react, @dnd-kit, motor, cryptography, PyJWT, emergentintegrations.
- **AI** — Emergent Universal LLM Key (OpenAI / Gemini / Claude / Nano Banana / Sora 2).
- **Standards** — ATO Schedule 1, ATO NAT 4189, Fair Work Modern Awards, NES, SGAA,
  Apple PassKit, Google Wallet API.
- **Design principle** — one signed ledger, one voucher, one copilot.
- **Snapshot compiled** — 11 July 2026.

---

_© 2026 NUA · All rights reserved · This document is a private snapshot for the NUA project._
