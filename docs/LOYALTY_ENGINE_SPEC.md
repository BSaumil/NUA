# NUA POS — Enterprise Loyalty Engine Specification

**Status:** Draft for engineering review
**Owner:** Product / Platform
**Scope:** Backend services, database schema, REST API, POS UI, customer-facing app/portal, reporting, fraud prevention, AI automation
**Source brief:** `NUA_POS_Loyalty_Engine.md` (12 loyalty program types, owner configuration model, core rules)

---

## 0. How to read this document

This spec is written to be handed directly to engineering for implementation planning. It is grounded in the **current NUA POS codebase**, not written from a blank slate — Section 2 documents what already exists today, because what already exists is fragmented across four separate, non-communicating subsystems. Every subsequent section (schema, API, workflows) is a **target architecture** that consolidates those four systems into one coherent Loyalty Engine, with an explicit migration plan (Section 15) rather than a rewrite-and-hope approach.

Conventions used throughout:
- `snake_case` — MongoDB field/collection names in the **target** schema.
- `camelCase` — field names as they exist **today** in the live codebase (called out explicitly wherever current-state and target diverge).
- Every API endpoint entry lists auth requirements using the roles already defined in NUA POS: `owner`, `manager`, `cashier`/staff, `customer` (app/portal), `system` (service-to-service / agent).
- "Ash" refers to NUA POS's existing AI agent framework (`nua_agent.py`, `nua_tools.py`, `nua_trust.py`, `approval_service.py`), not a new system to be built from scratch — Section 12 wires the loyalty engine into it.

---

## 1. Executive Summary & Goals

NUA POS must support **all 12 loyalty program types** from the source brief, simultaneously, per business, with owner-level configuration of which programs are active. Today it supports fragments of roughly 6 of the 12, spread across four uncoordinated backend subsystems with conflicting tier definitions, no shared audit trail, and a real point-loss bug at checkout. This spec defines:

1. A **single canonical loyalty account and ledger model** per customer per business, replacing four different "what is this customer's balance/tier" answers with one.
2. **Database schema** for all 12 program types, including three (Corporate, Family, Subscription) that do not exist in any form today.
3. A **unified REST API** that POS, the customer app, the customer portal, and Ash all call — no more three different `/loyalty/*` route files with different idempotency guarantees.
4. **POS workflows** that fix the current non-atomic redemption bug (points can currently be deducted twice, or not at all, if the checkout transaction succeeds and the redemption call fails).
5. **Customer app/portal flows** for balance visibility, redemption, and self-service (referrals, family/corporate account management).
6. **Reporting dashboards** for owners/managers: program performance, liability tracking (points/store credit are a financial liability, same accounting pattern already used for gratuity in NUA POS), cohort and tier analysis.
7. **Fraud prevention** rules specific to loyalty abuse (point farming, self-referral, voucher code sharing, tier gaming) layered on top of NUA POS's existing general fraud-detection endpoint.
8. **AI automation** wired into the real Ash agent — not a new AI system, but new tools, triggers, and approval-tier registrations on the existing `nua_tools.py` catalog and `approval_service.py` queue.
9. **Text/structural UI wireframes** for every new or modified screen, on both POS and customer-facing surfaces.
10. A **migration plan** from the four existing systems (Section 2) into this target architecture, sequenced so nothing breaks mid-migration.

### 1.1 Non-goals

- This spec does not redesign NUA POS's general multi-tenant/business model (`multi_tenant.py`) — it consumes `businessId` as an existing concept and specifies where loyalty data must start being filtered by it (a gap that exists today, see §2.6).
- This spec does not replace the existing universal Voucher model (`models/voucher.py`, HMAC-signed QR codes) — it consolidates the *three* voucher-issuing code paths that currently exist on top of that one model.
- Payment processing, EFTPOS integration, and receipt printing are out of scope except where loyalty balances must appear on a receipt (§8.6) or ticket.

---

## 2. Current-State Assessment: Four Fragmented Systems

This section exists so engineering does not "discover" these systems mid-build and have to replan. NUA POS today has **four separate backend subsystems** that all claim to own some part of "loyalty," none of which know about each other.

### 2.1 System A — Rewards & Tiers Catalog (`backend/routes/loyalty.py`, `backend/models/loyalty.py`)

- CRUD on `db.loyalty_rewards`: `{id, name, description, pointsCost, rewardType: discount|free_item|experience, discountAmount, discountPercent, freeItemId, isActive, createdAt}`.
- `GET/PUT /api/loyalty/tiers` seeds and edits `db.loyalty_tiers`: **Bronze (0 pts, 1.0x) / Silver (500 pts, 1.25x, "3% discount") / Gold (2000 pts, 1.5x) / Platinum (5000 pts, 2.0x, "10% discount")**.
- Also hosts unrelated `/api/events` and `/api/menu/qr-data` endpoints (not loyalty, noted only because they share the route file).
- A code comment records that an earlier, unprotected `/loyalty/redeem` handler was removed here in "iteration 36" after a points-bypass security bug — i.e., this exact class of bug (redemption without server-side balance enforcement) has bitten this codebase before.

### 2.2 System B — Points Earn/Redeem Engine + Ash Agent Hooks (`backend/routes/loyalty_engine.py`)

- `db.loyalty_config` (singleton doc, `id:"default"`): `earnRate` (default 1.0 pt/$1), `redeemRate` (default 0.01 $/pt), `minRedeem` (default 10 pts), `categoryMultipliers` (e.g. `{"Coffee": 2.0}`), `active`.
- `GET/PUT /api/loyalty/config` — PUT is `require_owner`.
- `POST /api/loyalty/earn` — **idempotent** per `transactionId` (checks `db.loyalty_ledger` before crediting), applies category multipliers, `$inc`s `customers.loyaltyPoints`.
- `POST /api/loyalty/redeem` — enforces `minRedeem`, checks balance, `value = points * redeemRate`.
- `GET /api/loyalty/balance/{customerId}`, `GET /api/loyalty/ledger/{customerId}`.
- Also hosts Ash-adjacent endpoints: `/api/agent/segments` (vip/regular/at_risk/first_timer), `/api/agent/decisions`, `POST /api/agent/tick` (runs segmentation, issues birthday vouchers via `wallet_service.ensure_birthday_voucher`, raises low-stock alerts), `/api/agent/voice-command` + `/api/agent/voice-catalog` (LLM voice routing).
- **This is the only one of the four systems with a real idempotency guarantee and a real config surface.** It is the closest thing to a canonical points engine today, but it is not wired into checkout tier discounting (§2.5) and has no concept of tiers, badges, or non-points programs at all.

### 2.3 System C — Badges/Milestones/Challenges/Referrals (`backend/routes/loyalty_v2.py`, prefix `/api/loyalty/v2`)

- Seeds `db.loyalty_badges` (10 badges, e.g. `badge-first-visit`: `visits>=1`; `badge-whale`: `spend>=5000`) and `db.loyalty_milestones` (6 thresholds).
- Milestone rewards **directly `$set` `customers.membershipTier`** — e.g. `mile-spend-500` → Silver, `mile-spend-2000` → Gold, `mile-spend-5000` → Platinum. **These thresholds differ from System A's** (500/2000/5000 pts vs. these being *spend* thresholds) and write the same field two different systems both claim to own.
- `evaluate_customer()` is idempotent via a composite key in `db.customer_badges`; interprets condition strings like `visits>=5`, `categorySpend:Wine>=200`.
- CRUD for badges/milestones/challenges; referral program ($20 referrer / $10 referee vouchers); leaderboard (`metric=points|visits|spend|referrals`).
- **This is the only system with referrals, badges, or challenges — none of that exists elsewhere.**

### 2.4 System D — "Loyalty 2.0" / Unified Wallet (`backend/routes/commerce_v29.py`)

- `GET /api/loyalty/status/{customerId}` computes tier **live from spend** using its own `_TIER_THRESHOLDS`: **Bronze(0)/Silver(500)/Gold(1500)/Platinum(5000)/VIP(10000)** — a *third, five-tier* scheme, distinct from both System A and System C.
- Computes weekly visit streaks; its own `_MILESTONES` written to `db.loyalty_awards` (a fifth collection).
- `POST /api/loyalty/award` (manual badge grant, owner/manager).
- `GET /api/personalisation/{customerId}` — rule-based offers: winback (>14 days since last visit → 25% off), favourite-item-free, high-value ($15 off), time-of-week pattern offer.
- Hosts the **unified wallet ledger**: `LedgerEntry` model (`models/wallet_ledger.py`) with buckets `points | store_credit | gift_card | voucher | cashback | referral`, signed entries (`sign: ±1`), `sourceType`, `metadata`. `GET /api/wallet/{customerId}`, `POST /api/wallet/{customerId}/credit|debit` (owner/manager only, debit is balance-checked), `GET /api/wallet/{customerId}/timeline`.
- **This is the most architecturally sophisticated of the four** (proper signed ledger, multiple buckets) but it duplicates System B's points concept in a different collection and computes yet another tier scheme.

### 2.5 What checkout actually does (`backend/routes/transactions.py:101-116`, `:151`)

The code path that actually runs on every sale reads `customer.membershipTier` (a plain string) and applies **hardcoded** tier discounts: Silver = 3% / 1.25x, Gold = 5% / 1.5x, Platinum = 10% / 2.0x. `points_earned = int(total * loyalty_multiplier)` — this is a **fourth, independent points-earning calculation**, not wired to System B's category-multiplier earn logic at all. The transaction record stores `discount`, `discountAmount`, `appliedDiscounts`, `pointsRedeemed`, `pointsDiscount` inline.

**Frontend redemption gap (`frontend/src/pages/POSTerminal.jsx`, ~line 549):** the cashier enters `pointsToRedeem`; the transaction POST embeds `pointsRedeemed`/`pointsDiscount` and the server applies the discount to the total but **does not itself decrement the points balance**. The frontend then fires a **separate, best-effort** `loyaltyEngineAPI.redeem(...)` call wrapped in `try { } catch {}` that **silently swallows failures**. If that second call fails (network blip, server error, race), the customer keeps their points but already received the discount — a real, exploitable point-duplication path. Conversely, if the page is refreshed or the tab closed between the two calls, points are permanently lost with no discount ever recorded against them. **This is the single most important reliability defect this spec must close** (§8.3, §16.2).

### 2.6 Multi-tenancy gap

`multi_tenant.py` defines a real `businesses` collection and franchise/business model, and `middleware/actor_context.py` propagates a business context through requests. **None of the four loyalty systems filter any query by `businessId`.** All loyalty config, balances, tiers, badges, and vouchers are effectively global across every business on the install. This was previously flagged and explicitly deprioritized by the business owner for general tenant isolation, but it cannot stay deprioritized for the Loyalty Engine specifically once Corporate Accounts (type 10) and per-business program configuration (owner configuration model, brief §"Owner Configuration") are implemented — a corporate account's shared balance must be scoped to one business by construction. §13 specifies the minimum required scoping.

### 2.7 Other loyalty-adjacent code inventoried

- **Vouchers**: `models/voucher.py` (canonical model, HMAC-SHA256-signed QR, `sourceType` incl. `promotion|refund|gift_card|referral|birthday|anniversary|staff|corporate|event|manual`, `faceValue`/`residualValue` partial redemption, full CRUD + AI Promotion Builder in `commerce_v29.py`) — but **three separate route files** also issue/redeem vouchers independently: `members.py` (`POST /vouchers/create`, `/vouchers/{code}/redeem`), `v26_commerce.py` (`POST /vouchers`, `/vouchers/{code}/apply`, `/vouchers/{vid}/redeem`), and `commerce_v29.py` itself. `nua_tools.py` references yet another collection name, `db.commerce_vouchers`.
- **Wallet (simple)**: `services/wallet_service.py` — `get_wallet()`, `ensure_birthday_voucher()` (deduped per customer/year, config in `db.settings{key:"wallet_offers"}`), `redeem_wallet_voucher()`. Exposed via `customers.py`: `GET /api/customers/{id}/wallet`, `POST /api/customers/{id}/store-credit/redeem` (atomic `find_one_and_update` — this one endpoint does redemption correctly), `GET/POST /api/customers/wallet-offers`.
- **Customer model** (`models/customer.py`): fields `membershipTier`, `totalSpent`, `visits`, `points`, `storeCredit`, plus a 360-profile (`birthday`, `seatingPreference`, `dietaryRestrictions`, `allergies`, `isVip`, `tags`, `noShowCount`, `feedbackRating`). **Field-name drift**: the Pydantic model declares `points`/`totalSpent`/`visits` while various services actually write `loyaltyPoints`/`totalSpend`/`totalVisits` to the same documents — meaning reads through the model silently miss data written by other paths.
- **Ash agent tools** (`nua_tools.py`): `add_wallet_credit` (high risk, requires approval), `issue_voucher` (medium risk), `upgrade_customer_tier` (medium risk — directly `$set`s `customers.membershipTier`, bypassing every tier-calc system above), `check_promo_voucher` (read-only, no approval).
- **Churn prediction** (`nua_intelligence.py`): `predict_customer_churn()` flags at-risk customers by visit cadence and recommends a win-back offer via notification — **not auto-executed**, sits behind the approval queue.
- **Trust/approval**: `nua_trust.py` is graduated autonomy for Ash's *own* tool execution risk (`db.ash_tool_config.trust`), not a customer-facing trust/fraud score — `approval_service.py` (`requires_approval`, `enqueue_approval`, `enqueue_or_execute`, `approve`, `reject`) is the generic gate that already covers `add_wallet_credit`, `issue_voucher`, `upgrade_customer_tier`.
- **Fraud**: `v25_suite.py:1142` `GET /api/v25/fraud-detection` scores void/comp/refund rate and average discount size per cashier — general POS fraud, **not loyalty-specific** (no points/voucher abuse signal at all today).
- **Audit**: `services/audit_service.py` (`log_event()`) and `services/entity_service.py` (`stamped_insert`/`stamped_update` — the one sanctioned place for `createdBy`/`updatedBy`/`businessId`/`version` stamping + history snapshots) both exist but are **inconsistently applied**; most loyalty writes above go directly to `db.<collection>.insert_one/update_one`, bypassing both.

### 2.8 Summary table — conflicting tier definitions today

| System | Collection | Thresholds | Basis |
|---|---|---|---|
| A (`loyalty.py`) | `loyalty_tiers` | Bronze 0 / Silver 500 / Gold 2000 / Platinum 5000 | points |
| C (`loyalty_v2.py`) | milestone `$set` on `customers.membershipTier` | Silver 500 / Gold 2000 / Platinum 5000 | **spend** |
| D (`commerce_v29.py`) | computed live, `_TIER_THRESHOLDS` | Bronze 0 / Silver 500 / Gold 1500 / Platinum 5000 / VIP 10000 | spend |
| Checkout (`transactions.py`) | reads `customer.membershipTier` string, hardcodes discount % | consumes whatever is currently in the field | n/a |

Three different numeric schemes, two different bases (points vs. spend), and the number actually applied at checkout depends entirely on which of A/C/D last wrote `membershipTier`. This is not a hypothetical risk — it is the current production behavior.

---

## 3. Target Architecture

### 3.1 Principle: one account, one ledger, many programs

The target architecture replaces "four systems, four truths" with:

- **One `loyalty_accounts` document per customer per business** — the single source of truth for tier, points balance, wallet bucket balances, and punch-card/streak progress. Nothing else writes a balance anywhere else.
- **One `loyalty_ledger`** — an append-only, signed, idempotent ledger. Every earn, redeem, adjustment, expiry, and manual override is a ledger entry. Balances on `loyalty_accounts` are a **cached projection** of the ledger, always rebuildable from it (audit-safe, matches the accounting pattern NUA POS already uses for gratuity-as-liability).
- **One `loyalty_programs` config collection**, per business, describing which of the 12 program types are enabled and their rules — the "Owner Configuration" model from the brief, implemented as data rather than as four different config docs.
- **One `loyalty_service.py`** backend module that is the only code allowed to write to `loyalty_accounts` or `loyalty_ledger`. All routes (POS, app, portal, Ash) call into this service; none write to the collections directly. This directly fixes the root cause of §2.5–2.8 (multiple independent writers to the same logical balance).
- **One REST namespace**, `/api/v3/loyalty/*`, versioned so it can be rolled out alongside the legacy `/api/loyalty/*` routes during migration (§15) without breaking existing frontend callers mid-deploy.

### 3.2 Service layering

```
POS Terminal ─┐
Customer App ─┼──▶  /api/v3/loyalty/*  ──▶  loyalty_service.py  ──▶  loyalty_accounts, loyalty_ledger, loyalty_programs, ...
Portal       ─┤                                     │
Ash Agent    ─┘                                     ├──▶ entity_service.stamped_* (createdBy/updatedBy/businessId/version)
                                                      ├──▶ audit_service.log_event()
                                                      ├──▶ fraud_service.check_loyalty_event()  (new, §11)
                                                      └──▶ notification_service (balance changes, tier-ups, expiring points)
```

`loyalty_service.py` exposes internal functions (`earn()`, `redeem()`, `adjust()`, `evaluate_tier()`, `evaluate_badges()`, `issue_voucher_for_program()`, `credit_wallet()`, `debit_wallet()`) that are called both by the REST layer and directly by Ash's tools (§12) and by `transactions.py` at checkout — replacing the fourth, independent points calculation currently embedded there.

### 3.3 Why not a full rewrite of transactions.py

`transactions.py` remains the system of record for the sale itself (subtotal, tax, GST, gratuity liability posting — an already-correct precedent this spec follows for points/store-credit-as-liability). This spec's checkout change is narrow and precise: transaction creation calls `loyalty_service.redeem()` and `loyalty_service.earn()` **synchronously, inside the same request, before the transaction is committed** — not as a fire-and-forget side call from the frontend (§8.3). This is additive to the existing transaction flow, not a rewrite of it.

---

## 4. Domain Model & Terminology

| Term | Definition |
|---|---|
| **Loyalty Account** | One per (customerId, businessId). Holds current tier, points balance, wallet bucket balances, punch-card progress, streaks. |
| **Ledger Entry** | Immutable record of one balance-affecting event. Never edited or deleted; corrections are new offsetting entries. |
| **Bucket** | A named balance within a wallet: `points`, `store_credit`, `gift_card`, `cashback`, `punch_card:<cardId>`. |
| **Program** | One of the 12 configured loyalty program types, with its own rule set, scoped to a business. |
| **Reward** | A redeemable catalog item (discount, free item, experience) costing points or punches. |
| **Voucher** | A single-use or partial-use, HMAC-signed, code-bearing credit instrument issued by a program (existing `models/voucher.py`, kept canonical). |
| **Tier** | A membership level (Bronze→VIP) with associated multipliers/benefits. Exactly one authority computes it (§6.3). |
| **Idempotency Key** | Caller-supplied key (typically `transactionId` or a UUID) that makes an earn/redeem/adjust call safely retryable. |
| **Corporate Account** | A business-customer entity whose members earn into one shared `loyalty_accounts` document. |
| **Family Account** | A consumer-customer grouping whose members earn into one shared `loyalty_accounts` document, distinguished from Corporate by `accountType`. |
| **Subscription** | A recurring-billing record granting periodic benefits (bonus points, discounts, free items) independent of transaction activity. |

---

## 5. Loyalty Program Types — Full Specification

Each program type below is specified with: what it does, configuration schema (stored in `loyalty_programs`), the trigger/evaluation logic, and edge cases engineering must handle. All programs share the owner on/off switch and per-business scoping described in §3.1/§13.

### 5.1 Coffee PunchPass (`type: "punch_pass"`)

- **Config**: `{eligibleProductIds: [...], eligibleCategoryIds: [...], punchesRequired: int, rewardId: <catalog reward>, allowPartialRedemption: bool, resetOnRedeem: bool}`.
- **Trigger**: on transaction commit, for each eligible line item, increment `loyalty_accounts.punchCards[cardId].punches` by line-item quantity (a 3-coffee order in one transaction = 3 punches, per brief).
- **Redemption**: when `punches >= punchesRequired`, the reward becomes redeemable; if `allowPartialRedemption` is false, redemption requires the full count and resets to 0; if true, a partial-value credit is computed pro-rata and posted as a `store_credit` ledger entry, with the remainder carried over.
- **Edge cases**: eligible item refunded after punch granted → ledger posts a compensating `punch_card` debit entry (never mutate the original grant); product moved out of eligible category mid-cycle → punches already earned are preserved, only future earning is affected; multiple active punch cards per customer (e.g., coffee + car wash) are independent `punchCards[cardId]` keys.

### 5.2 Spend-Based Rewards (`type: "spend_points"`)

- **Config**: `{earnRate: float (pts/$1), earnBasis: "pre_discount"|"post_discount", redeemRate: float ($/pt), minRedeemPoints: int, maxRedeemPercentOfBill: float, categoryMultipliers: {category: multiplier}, roundingRule: "floor"|"round"|"ceil"}`.
- This is System B's config, promoted to canonical, with `earnBasis` and `maxRedeemPercentOfBill` added (neither exists today — both are needed to prevent a $0 bill after redemption, a real gap since today's redeem has no bill-relative cap).
- **Trigger**: `loyalty_service.earn()` at checkout, idempotent per `transactionId`.
- **Edge cases**: refund/void of a transaction that already earned points → automatic clawback ledger entry, capped at the customer's current balance (never drives balance negative; shortfall is logged as an uncollectable adjustment visible to owner in reporting, §10).

### 5.3 Product Punch Cards (`type: "product_punch_card"`)

- Generalized version of 5.1 for any product/category (pizza, burgers, smoothies, haircuts, car washes — per brief). Same schema as 5.1, one config document per punch card definition, `programId` distinguishes multiple simultaneous punch cards.

### 5.4 Membership Tiers (`type: "membership_tier"`)

- **Config**: ordered list `{tierName, thresholdBasis: "points"|"spend"|"visits", threshold, benefits: {discountPercent, pointsMultiplier, exclusivePricing: bool, earlyAccess: bool, birthdayGiftRewardId}}`. Default seed: Bronze/Silver/Gold/Platinum/VIP (per brief; the specific numeric thresholds are an **owner-configurable business decision**, not hardcoded — this is the fix for §2.8's three-scheme conflict).
- **Single authority**: `loyalty_service.evaluate_tier(customerId, businessId)` is the *only* code path allowed to write `loyalty_accounts.tier`. It runs after every ledger-affecting event (earn, spend-basis transaction, visit). Checkout reads the tier from `loyalty_accounts`, never recomputes it.
- **Edge cases**: threshold basis change (owner switches from points-based to spend-based tiers) triggers a one-time recompute job for all accounts, logged as a bulk adjustment; downgrade policy is explicit config (`downgradeOnThresholdLoss: bool`, `downgradeGraceDays: int`) — today's systems only ever upgrade, never downgrade, which is itself a decision this spec makes explicit rather than accidental.

### 5.5 Birthday Rewards (`type: "birthday_reward"`)

- **Config**: `{rewardType: "free_item"|"discount"|"points", value, validityDays, issueDaysBeforeBirthday: int}`.
- Builds directly on the existing `wallet_service.ensure_birthday_voucher` dedup pattern (per-customer-per-year), generalized to any reward type, not just a fixed-value voucher. Runs via Ash's daily tick (§12.2).

### 5.6 Anniversary Rewards (`type: "anniversary_reward"`)

- **Config**: same shape as 5.5, keyed off `customer.createdAt` (join date) instead of birthday. **Edge case**: customers imported via bulk migration with a backfilled `createdAt` should have an `anniversaryEligibleFrom` override field so migrated customers don't all trigger anniversary rewards on the same day.

### 5.7 Visit-Based Rewards (`type: "visit_reward"`)

- **Config**: `{visitsRequired: int, rewardId, resetOnRedeem: bool}`. A "visit" is defined as one committed transaction per customer per calendar day (configurable `visitDefinition: "per_transaction"|"per_day"` to avoid a large group split across multiple checks counting as many visits).

### 5.8 AI Smart Rewards (`type: "ai_smart_reward"`)

- Not a separate reward mechanism — a **modifier layer** over the other programs, driven by Ash (§12). Config: `{enablePredictiveReturn: bool, enableQuietPeriodBoost: bool, enablePersonalisedRecommendation: bool, enableAbuseDetection: bool, enableWinback: bool}`. Each capability maps to a specific existing or new Ash tool (§12.1 table) — this spec does not invent a new AI system, it registers new tools on the existing one.

### 5.9 Wallet Cashback (`type: "wallet_cashback"`)

- **Config**: `{cashbackRate: float (% of spend), creditBucket: "cashback"|"store_credit", minTransactionValue}`. Posts to the `cashback` bucket on `loyalty_accounts`, using the same signed-ledger mechanics System D already proved out — promoted to canonical rather than living only in `commerce_v29.py`.

### 5.10 Corporate Loyalty (`type: "corporate"`) — net new

- **Config**: `{corporateAccountId, memberCustomerIds: [...], sharedBucket: "points"|"store_credit", monthlySpendCap, invoiceBilling: bool}`.
- A `corporate_accounts` document (new collection, §6.7) groups member customers; each member's earn events post to the **corporate account's** `loyalty_accounts` document (via `accountId` indirection, not the individual customer's), while spend attribution per member is retained in the ledger's `metadata.memberCustomerId` for reporting/chargeback.
- **Edge cases**: member leaves the company → member is removed from `memberCustomerIds`, their historical ledger entries remain (they contributed to a shared pool, not a personal one — do not retroactively re-attribute); monthly spend cap exceeded → transaction still completes, but a fraud/policy flag is raised (§11) rather than blocking the sale.

### 5.11 Family Accounts (`type: "family"`) — net new

- Same underlying mechanism as Corporate (shared `loyalty_accounts` via a grouping document, `family_accounts`, §6.7), consumer-oriented: `{familyAccountId, memberCustomerIds: [...], primaryHolderCustomerId, sharedBucket}`.
- **Edge cases**: a member can belong to at most one family account at a time (enforced at the service layer, not just UI); primary holder is the only role permitted to add/remove members or dissolve the account (customer portal, §9.4).

### 5.12 Subscription Loyalty (`type: "subscription"`) — net new

- **Config**: `{planId, priceRecurring, billingInterval: "monthly"|"annual", benefits: {bonusPointsPerCycle, discountPercent, freeItemPerCycle, prioritySupport: bool}}`.
- A `loyalty_subscriptions` document (§6.8) per active subscriber; a scheduled job (reusing NUA POS's existing scheduler pattern, `nua_scheduler.py`) grants the cycle's benefits and posts the corresponding ledger entries on each billing date. **Payment collection itself is out of scope of this spec** — it assumes an existing or forthcoming recurring-billing integration and only specifies the loyalty-benefit side; the subscription record carries a `paymentStatus` field so benefit-granting can be gated on payment success (`active` only, not `past_due`/`cancelled`).

---

## 6. Database Schema (Target)

All collections below follow the codebase's existing conventions: `_id` (Mongo ObjectId), `id` (string UUID, app-facing), `businessId` (required, §13), `createdAt`/`updatedAt`, `createdBy`/`updatedBy` (via `entity_service.stamped_insert/update`), `version` (optimistic concurrency).

### 6.1 `loyalty_accounts`

```jsonc
{
  "id": "acct_...",
  "businessId": "biz_...",
  "customerId": "cust_...",           // null if accountType is corporate/family (owned by the group doc instead)
  "accountType": "individual" | "corporate" | "family",
  "groupAccountId": null,             // set for corporate/family: points at corporate_accounts/family_accounts.id
  "tier": "Bronze",
  "tierEvaluatedAt": "2026-08-06T...",
  "balances": {
    "points": 1240,
    "store_credit": 15.00,
    "cashback": 3.50,
    "gift_card": 0
  },
  "punchCards": {
    "coffee_punch": { "punches": 4, "required": 8, "lastPunchAt": "..." }
  },
  "streaks": { "weeklyVisit": 3, "lastVisitAt": "..." },
  "stats": { "totalSpend": 4820.50, "totalVisits": 62, "lastTransactionAt": "..." },
  "createdAt": "...", "updatedAt": "...", "createdBy": "...", "updatedBy": "...", "version": 14
}
```
Unique index: `{businessId, customerId}` (individual accounts), `{businessId, groupAccountId}` (group accounts).

### 6.2 `loyalty_ledger`

```jsonc
{
  "id": "ldg_...",
  "businessId": "biz_...",
  "accountId": "acct_...",
  "bucket": "points" | "store_credit" | "cashback" | "gift_card" | "punch_card:<cardId>",
  "entryType": "earn" | "redeem" | "adjust" | "expire" | "clawback" | "manual_grant" | "manual_revoke",
  "amount": 120,
  "sign": 1,                          // +1 credit, -1 debit — same convention as existing wallet_ledger.py
  "balanceAfter": 1240,
  "sourceType": "transaction" | "punch_card" | "birthday" | "anniversary" | "referral" | "milestone" | "badge" | "corporate_pool" | "subscription_cycle" | "manual" | "ai_agent" | "fraud_reversal",
  "sourceReferenceId": "txn_...",     // e.g. transactionId
  "programId": "prog_...",
  "idempotencyKey": "txn_...",        // unique index with businessId — the enforcement point for §8.3/§16.2
  "actor": { "type": "cashier" | "customer" | "owner" | "system" | "ash_agent", "id": "user_..." },
  "metadata": { "memberCustomerId": "cust_..." },
  "createdAt": "..."
}
```
Unique index: `{businessId, idempotencyKey, entryType}` — this is the single mechanism that makes earn/redeem safe to retry and is the direct fix for the checkout double-deduction bug in §2.5.
`loyalty_ledger` is **append-only**: no update/delete routes exist in the API (§7). Corrections are new entries with `entryType: adjust` and a `metadata.correctsEntryId` reference.

### 6.3 `loyalty_programs`

```jsonc
{
  "id": "prog_...",
  "businessId": "biz_...",
  "type": "punch_pass" | "spend_points" | "product_punch_card" | "membership_tier" | "birthday_reward" | "anniversary_reward" | "visit_reward" | "ai_smart_reward" | "wallet_cashback" | "corporate" | "family" | "subscription",
  "name": "Coffee PunchPass",
  "active": true,
  "config": { /* type-specific schema, §5 */ },
  "createdAt": "...", "updatedAt": "...", "createdBy": "...", "updatedBy": "...", "version": 3
}
```
One document per program instance per business (a business may run two `product_punch_card` programs — coffee and car wash — as two documents). This collection **is** the "Owner Configuration" screen's data model (§14.1).

### 6.4 `loyalty_tiers` (replaces System A/C/D's three conflicting sources)

```jsonc
{
  "id": "tier_...", "businessId": "biz_...", "programId": "prog_...",
  "name": "Silver", "rank": 1, "thresholdBasis": "points", "threshold": 500,
  "benefits": { "discountPercent": 3, "pointsMultiplier": 1.25, "exclusivePricing": false, "earlyAccess": false, "birthdayGiftRewardId": null },
  "createdAt": "...", "updatedAt": "..."
}
```

### 6.5 `loyalty_rewards_catalog` (formerly `loyalty_rewards`, businessId added)

Same shape as today's System A `loyalty_rewards`, plus `businessId`, plus `programId` linkage where relevant.

### 6.6 `loyalty_badges`, `loyalty_milestones`, `customer_badges`, `loyalty_challenges`

Carried forward from System C largely as-is (they are the one part of the current architecture with no competing implementation), with `businessId` added and milestone rewards changed to **post a ledger entry / call `evaluate_tier()`** instead of directly `$set`-ing `membershipTier` (closes the §2.3 conflict at the root).

### 6.7 `corporate_accounts` / `family_accounts` (net new, §5.10/5.11)

```jsonc
{
  "id": "corp_...", "businessId": "biz_...",
  "name": "Acme Consulting", "type": "corporate",
  "memberCustomerIds": ["cust_1", "cust_2"],
  "primaryHolderCustomerId": "cust_1",      // family only; corporate uses a designated billing contact instead
  "sharedBucket": "points",
  "monthlySpendCap": 5000,                  // corporate only
  "invoiceBilling": true,                   // corporate only
  "loyaltyAccountId": "acct_...",           // points at the shared loyalty_accounts doc
  "createdAt": "...", "updatedAt": "..."
}
```

### 6.8 `loyalty_subscriptions` (net new, §5.12)

```jsonc
{
  "id": "sub_...", "businessId": "biz_...", "customerId": "cust_...",
  "planId": "prog_...", "status": "active" | "past_due" | "cancelled",
  "billingInterval": "monthly", "currentPeriodStart": "...", "currentPeriodEnd": "...",
  "lastBenefitGrantedAt": "...", "createdAt": "...", "updatedAt": "..."
}
```

### 6.9 `loyalty_fraud_flags` (net new, §11)

```jsonc
{
  "id": "flag_...", "businessId": "biz_...", "accountId": "acct_...",
  "ruleId": "self_referral" | "point_farming" | "voucher_sharing" | "tier_gaming" | "corporate_cap_exceeded",
  "severity": "low" | "medium" | "high",
  "evidence": { "...": "..." },
  "status": "open" | "reviewed_ok" | "confirmed_abuse" | "reversed",
  "reviewedBy": null, "reviewedAt": null,
  "createdAt": "..."
}
```

### 6.10 Migration-relevant field mapping

| Legacy field/collection | Target | Notes |
|---|---|---|
| `customers.points` / `customers.loyaltyPoints` | `loyalty_accounts.balances.points` | resolves §2.7 field-name drift |
| `customers.totalSpent` / `totalSpend` | `loyalty_accounts.stats.totalSpend` | |
| `customers.visits` / `totalVisits` | `loyalty_accounts.stats.totalVisits` | |
| `customers.membershipTier` | `loyalty_accounts.tier` | writes centralized in `evaluate_tier()` |
| `customers.storeCredit` | `loyalty_accounts.balances.store_credit` | |
| `loyalty_tiers` (System A) | `loyalty_tiers` (target) | thresholds become owner-configurable, not hardcoded |
| `loyalty_ledger` (System B) | `loyalty_ledger` (target) | schema extended with `bucket`, `businessId`, richer `sourceType` |
| `loyalty_awards` (System D) | `loyalty_ledger` entries with `sourceType: milestone/badge` | collection retired |
| wallet `LedgerEntry` (System D) | `loyalty_ledger` (target) | merged, same signed-entry convention preserved |
| `db.vouchers` / `db.commerce_vouchers` | single `vouchers` collection | route consolidation, §15.3 |

---

## 7. API Specification — `/api/v3/loyalty/*`

All endpoints require standard NUA POS auth (`Authorization` bearer) and are `businessId`-scoped via the actor context middleware (§13). Idempotency-sensitive endpoints require an `Idempotency-Key` header or `transactionId` body field.

### 7.1 Configuration (owner)

| Method & Path | Auth | Description |
|---|---|---|
| `GET /programs` | owner, manager | List all `loyalty_programs` for the business |
| `POST /programs` | owner | Create a program (any of the 12 types) |
| `PUT /programs/{programId}` | owner | Update config / toggle `active` |
| `DELETE /programs/{programId}` | owner | Soft-delete (sets `active:false`, retains history) |
| `GET /tiers` | owner, manager | List tier ladder |
| `PUT /tiers` | owner | Replace tier ladder (triggers recompute job, §5.4) |
| `GET/POST/PUT/DELETE /rewards` | owner, manager (read: all staff) | Rewards catalog CRUD |

### 7.2 Account & balance

| Method & Path | Auth | Description |
|---|---|---|
| `GET /accounts/{customerId}` | staff, customer (self), owner | Full account: tier, balances, punch cards, streaks |
| `GET /accounts/{customerId}/ledger?bucket=&from=&to=&cursor=` | staff, customer (self) | Paginated ledger history |
| `POST /accounts/resolve` | staff | Resolve customer by phone/QR/NFC/email/membership ID (brief §"Core Rules") → returns account summary for POS lookup |

### 7.3 Earn / redeem / adjust — the canonical write path

| Method & Path | Auth | Description |
|---|---|---|
| `POST /earn` | system (called by `transactions.py`), Ash | Body: `{customerId, businessId, transactionId, lineItems, subtotal, ...}`. Idempotent on `transactionId`. Computes program-driven earn across every active program for the business in one pass (points, punches, streaks, tier re-eval) and returns the full set of ledger entries created. |
| `POST /redeem` | system (called by `transactions.py`), staff (manual), customer (self, portal/app) | Body: `{customerId, bucket, amount, transactionId?}`. Balance-checked, bill-cap-checked (§5.2), idempotent on `transactionId`/`Idempotency-Key`. |
| `POST /adjust` | owner, manager | Manual credit/debit with mandatory `reason` field — always audit-logged (`audit_service`), always a `manual_grant`/`manual_revoke` ledger entry, never silent. |
| `POST /vouchers/{code}/redeem` | staff, customer | Single consolidated voucher redemption path (retires the three duplicate paths in §2.7). |

**Non-negotiable contract**: `/earn` and `/redeem` are the *only* two endpoints that may write to `loyalty_ledger`/`loyalty_accounts` on behalf of a transaction, and `transactions.py` must call both **synchronously** as part of transaction creation (§8.3) — not from the frontend as a follow-up call.

### 7.4 Programs — type-specific reads

| Method & Path | Description |
|---|---|
| `GET /punch-cards/{customerId}` | Per-card progress |
| `GET /badges/{customerId}`, `POST /badges/evaluate/{customerId}` | Badge state / manual re-evaluation |
| `GET /milestones/{customerId}` | Milestone progress |
| `GET/POST /challenges`, `POST /challenges/{id}/join` | Challenge CRUD + enrollment |
| `GET /leaderboard?metric=points\|visits\|spend\|referrals` | Unchanged from System C, `businessId`-scoped |
| `POST /referrals`, `GET /referrals/{customerId}` | Referral issuance + status |
| `GET/POST /corporate-accounts`, `PUT /corporate-accounts/{id}/members` | Corporate account management |
| `GET/POST /family-accounts`, `PUT /family-accounts/{id}/members` | Family account management (member add/remove restricted to `primaryHolderCustomerId`, enforced server-side) |
| `GET/POST /subscriptions`, `POST /subscriptions/{id}/cancel` | Subscription lifecycle |
| `GET /personalisation/{customerId}` | Carried forward from System D, now reading from unified account/ledger |

### 7.5 Fraud & reporting (owner/manager)

| Method & Path | Description |
|---|---|
| `GET /fraud-flags?status=open` | List open flags |
| `PUT /fraud-flags/{id}` | Review/resolve a flag (`reviewed_ok`/`confirmed_abuse`/`reversed`) |
| `GET /reports/liability` | Outstanding points/store-credit/cashback value (§10.2) |
| `GET /reports/program-performance` | Redemption rate, breakage, cost-per-program (§10.1) |
| `GET /reports/tier-distribution` | Customer count per tier |
| `GET /reports/cohort` | Retention/spend by signup cohort |

### 7.6 Error codes

| Code | Meaning |
|---|---|
| `LOYALTY_INSUFFICIENT_BALANCE` | Redeem exceeds available balance in bucket |
| `LOYALTY_MIN_REDEEM_NOT_MET` | Below `minRedeemPoints` |
| `LOYALTY_BILL_CAP_EXCEEDED` | Redeem would exceed `maxRedeemPercentOfBill` |
| `LOYALTY_DUPLICATE_IDEMPOTENCY_KEY` | Returns the original result instead of re-applying (safe retry) |
| `LOYALTY_PROGRAM_INACTIVE` | Program toggled off after client fetched config |
| `LOYALTY_VOUCHER_INVALID` | Bad/expired/already-redeemed/signature-mismatch code |
| `LOYALTY_ACCOUNT_LOCKED` | Account frozen pending fraud review (§11.4) |

---

## 8. POS Workflows

### 8.1 Customer identification at checkout

1. Cashier opens checkout, taps **"Add Loyalty"**.
2. Search by phone, email, membership ID, or scan QR/NFC (brief's multi-channel requirement) → `POST /accounts/resolve`.
3. On match: account summary chip appears in the cart header — tier badge, points balance, any active punch-card progress, any redeemable rewards/vouchers.
4. No match: **"New Customer"** quick-add (name + phone minimum) creates the customer and a `loyalty_accounts` doc in one step.

### 8.2 Earning (automatic, no cashier action required)

Happens server-side inside transaction creation (§8.3) — cashier sees a toast confirmation ("+120 pts, Silver → Gold!") after payment completes, sourced from the `/earn` response, not recomputed on the frontend.

### 8.3 Redemption (fixes the §2.5 atomicity bug)

**Current (broken) flow**: transaction commits with `pointsRedeemed` embedded → frontend separately calls `/redeem` in a swallowed try/catch → possible double-spend or point loss.

**Target flow**:
1. Cashier taps **"Redeem"** on the loyalty chip → sheet shows available buckets/vouchers/rewards with live value preview (calls `GET /accounts/{id}` for current balance + `loyalty_programs` config for rates — read-only, no balance mutation yet).
2. Cashier selects redemption (points amount, voucher code, or reward catalog item) → stored as **pending redemption state on the cart**, not yet posted anywhere.
3. Cashier proceeds to payment. On **`POST /transactions`**, the backend, inside the same request/transaction:
   a. Calls `loyalty_service.redeem()` (balance/cap-checked) — if it fails, the **entire checkout fails** with `LOYALTY_INSUFFICIENT_BALANCE`/etc. and no partial discount is applied.
   b. Applies the resulting discount to the bill total.
   c. Calls `loyalty_service.earn()` on the final (post-discount, per `earnBasis` config) total.
   d. Commits the transaction record with both resulting ledger entry IDs attached (`transaction.loyaltyLedgerEntryIds: [...]`).
4. If payment itself later fails/is voided, the transaction void flow (already exists) triggers the ledger clawback described in §5.2's edge case — reusing the existing void/refund code path, extended to call `loyalty_service.adjust()`.

This removes the frontend's independent `loyaltyEngineAPI.redeem()` call entirely — redemption becomes a property of transaction creation, not a follow-up network call, which is the structural fix (retry-safe via `Idempotency-Key`/`transactionId`, all-or-nothing).

### 8.4 Manager override

Cashier taps **"Manager Override"** on the loyalty sheet (e.g., to redeem below `minRedeemPoints`, waive a bill cap, or manually grant points for a service failure) → PIN/manager auth prompt → `POST /adjust` with mandatory `reason` → always logged to `audit_service`, always visible in the manager's shift report.

### 8.5 Manual reward issuance (comp)

From the customer profile in POS: **"Issue Reward"** → pick from catalog or free-text voucher → `POST /vouchers` (owner/manager) → prints/sends the voucher code immediately.

### 8.6 Receipt & printer

Receipt footer (reusing the existing configurable ESC/POS footer/padding settings from `print_targets`, established in the printer-ticket-footer work) gains a loyalty block: `Points earned: +120 | Balance: 1,240 pts | Tier: Gold | [QR: portal balance link]`.

---

## 9. Customer App / Portal Flows

### 9.1 Balance & activity (home screen)

Real-time balance across all buckets, current tier + progress bar to next tier, active punch cards, upcoming/expiring rewards, ledger activity feed — all sourced from `GET /accounts/{customerId}` and `GET /accounts/{customerId}/ledger`, the exact same endpoints POS uses (single source of truth, no app-specific balance computation).

### 9.2 Redemption (self-service)

Customer selects a reward/voucher from their balance → generates a redemption QR/code → cashier scans it at POS, which calls the same `/redeem` path as §8.3 (`actor.type: "customer"` vs `"cashier"` distinguishes the audit trail only).

### 9.3 Referrals

Share a referral link/code → new customer signup attributed via `POST /referrals` → both parties' vouchers issued automatically on the referee's first qualifying transaction (fraud-checked against self-referral, §11.2).

### 9.4 Family / Corporate account management

Primary holder (family) or billing admin (corporate) sees a **"Manage Members"** screen: add member by phone/email (sends an accept-invite notification, does not silently enroll), remove member, view per-member contribution to the shared pool (from `loyalty_ledger.metadata.memberCustomerId`), view/download monthly statement (corporate, `invoiceBilling`).

### 9.5 Subscription management

View current plan/benefits, next billing date, cancel (sets `status: cancelled`, benefits stop at period end, no further ledger grants).

---

## 10. Reporting Dashboards (Owner/Manager)

### 10.1 Program Performance

Per program: enrollment count, redemption rate (%), average time-to-redeem, breakage rate (issued-but-never-redeemed value — a real cost/liability release metric), top-performing programs by incremental repeat-visit rate.

### 10.2 Liability Tracking

Outstanding points/store-credit/cashback value converted to dollar liability (points × `redeemRate`), trended over time — same accounting posture already established for gratuity-as-liability in NUA POS, extended here. Surfaced alongside expiry schedule if points-expiry is configured (owner-configurable `pointsExpiryDays`, not covered by legacy systems today — recommended addition).

### 10.3 Tier Distribution & Cohort

Customer count per tier, tier migration over time (upgrades/downgrades), cohort retention curves by signup month, average spend by tier (validates whether tier benefits are actually driving incremental spend).

### 10.4 Fraud Summary

Open flags by rule/severity, resolution rate, $ value of confirmed-abuse reversals — feeds directly from `loyalty_fraud_flags` (§6.9, §11).

### 10.5 AI Automation Activity

Ash actions taken/recommended for loyalty (birthday vouchers issued, churn win-back offers sent, abuse flags raised, quiet-period boosts triggered), with approval-queue status for anything gated by `approval_service` — this reuses NUA POS's existing agent activity log, filtered to loyalty-tagged tool calls.

---

## 11. Fraud Prevention

### 11.1 Rules (new `fraud_service.check_loyalty_event()`, called from `loyalty_service` on every earn/redeem)

| Rule | Trigger | Default action |
|---|---|---|
| `point_farming` | Repeated minimum-value transactions from same customer/card in short window purely to earn points | Flag `medium`, no auto-block |
| `voucher_sharing` | Same voucher code redemption-attempted from multiple distinct terminals/IPs in short window | Flag `high`, voucher auto-locked pending review |
| `self_referral` | Referrer and referee share phone/email/device fingerprint | Flag `high`, referral vouchers held unissued |
| `tier_gaming` | Large single manual `adjust` immediately followed by tier-benefit redemption, then reversal pattern | Flag `medium` |
| `corporate_cap_exceeded` | Corporate account monthly spend cap crossed | Flag `low`, informational, sale not blocked (§5.10) |

### 11.2 Manager overrides

Every fraud flag supports **manager override with mandatory reason**, same pattern as §8.4 — overrides are themselves audit-logged, so an owner reviewing the fraud dashboard sees both the flag and its resolution history, never a silent bypass.

### 11.3 Relationship to existing fraud detection

This is additive to, not a replacement for, `v25_suite.py`'s general cashier-level fraud scoring (void/comp/refund/discount-size rates) — a cashier who both discounts heavily *and* triggers loyalty flags on the same transactions is a stronger combined signal than either system alone; the reporting dashboard (§10.4) should cross-reference both by `cashierId`.

### 11.4 Account lockout

`confirmed_abuse` on a `high` severity flag sets `loyalty_accounts.locked: true` — subsequent `/redeem` calls return `LOYALTY_ACCOUNT_LOCKED` until an owner/manager clears it (`PUT /fraud-flags/{id}` with `status: reviewed_ok`).

---

## 12. AI Automation — Ash Integration

This section registers new capabilities on NUA POS's **existing** agent framework (`nua_agent.py`, `nua_tools.py`, `nua_trust.py`, `approval_service.py`) rather than proposing a parallel AI system.

### 12.1 New/extended Ash tools

| Tool | Risk tier | Approval | Maps to brief |
|---|---|---|---|
| `predict_return_visit` (extends `nua_intelligence.predict_customer_churn`) | read-only | none | "Predict return visits" |
| `trigger_quiet_period_boost` | medium | queued (`approval_service`) | "Trigger double points in quiet periods" |
| `recommend_personalised_reward` (extends existing `personalisation` logic, §5.8/§7.4) | read-only | none | "Recommend personalised rewards" |
| `detect_loyalty_abuse` (wraps §11.1 rules) | read-only (flag creation only; reversal is a separate, higher-risk tool) | none for flagging; `reverse_loyalty_transaction` is high-risk, always queued | "Detect loyalty abuse" |
| `issue_winback_offer` (extends existing `issue_voucher`) | medium | queued | "Recover inactive customers" |
| `upgrade_customer_tier` **(existing tool, behavior changed)** | medium | queued | must now call `loyalty_service.evaluate_tier()` / `adjust()` instead of `$set`-ing `membershipTier` directly — closes the bypass noted in §2.7 |

### 12.2 Scheduled triggers

Reusing `nua_scheduler.py` and the existing `POST /api/agent/tick` cadence: daily birthday/anniversary reward issuance (§5.5/5.6), weekly quiet-period detection, monthly subscription benefit grants (§5.12), nightly fraud-rule sweep populating `loyalty_fraud_flags`.

### 12.3 Trust/approval

No new trust framework is introduced — every new tool above is registered in the existing `db.ash_tool_config` catalog with a risk tier, and gated through `approval_service.enqueue_or_execute()` exactly like `add_wallet_credit`/`issue_voucher`/`upgrade_customer_tier` are today. As the business owner's trust in Ash's loyalty decisions grows (NUA POS's existing graduated-autonomy concept), specific tools can be promoted from "always queued" to "auto-execute under threshold" without any loyalty-specific code change — that promotion mechanism already exists in `nua_trust.py`.

---

## 13. Multi-Tenancy & Data Isolation

Minimum required scoping for this spec to be safe to ship (closing §2.6's gap, scoped narrowly to loyalty rather than reopening the general tenant-isolation decision):

- Every collection in §6 carries a required `businessId`.
- Every query in `loyalty_service.py` and every route in §7 filters by the actor's `businessId` (sourced from `middleware/actor_context.py`, already propagated on every authenticated request — this is wiring existing plumbing into a new module, not building new plumbing).
- Compound indexes lead with `businessId` on every collection (`{businessId, customerId}`, `{businessId, idempotencyKey}`, etc.) both for correctness and query performance.
- Corporate/Family accounts are inherently single-business by construction (§6.7) — this is the concrete case that makes loyalty-level scoping non-optional even though general tenant isolation was previously deprioritized.
- Cross-business customer records (a customer who visits two locations owned by the same operator) are **out of scope** for this version — each business's `loyalty_accounts` is independent. A future "loyalty account linking across businesses" feature is called out as an open question (§17).

---

## 14. UI Wireframes (Text/Structural)

Each entry lists: screen name, purpose, component list top-to-bottom, key states.

### 14.1 POS — Owner Configuration (`/settings/loyalty`) — replaces `LoyaltyConfig.jsx` + `LoyaltyEvents.jsx`'s tier/reward tabs

```
[Header: "Loyalty Engine" | Save button]
[Tab bar: Programs | Tiers | Rewards Catalog | Badges & Challenges | Corporate/Family | Fraud Flags]

-- Programs tab --
[Program list, one card per active/inactive program]
  Card: [Toggle: on/off] [Program type icon + name] [Enrolled count] [Edit >]
  Empty state: "No programs configured — Add your first program"
  [+ Add Program] → opens type picker (12 types, per §5) → type-specific config form

-- Tiers tab --
[Ordered list of tier rows: name, threshold basis dropdown, threshold value, benefits summary]
[Drag handle to reorder rank]
[Downgrade policy toggle + grace days input]
[+ Add Tier]

-- Rewards Catalog tab --
[Table: Name | Cost (pts) | Type | Status | Actions]
[+ Add Reward] → form: name, description, cost, type (discount/free_item/experience), value

-- Fraud Flags tab --
[Filter: status = Open]
[Table: Rule | Severity | Customer | Date | Actions (Review)]
[Review drawer: evidence detail, Resolve buttons (OK / Confirmed Abuse / Reverse)]
```

### 14.2 POS — Checkout Loyalty Chip & Redemption Sheet

```
[Cart header, existing checkout screen]
  <before customer attached>
  [🔍 Add Loyalty] button
  <after customer attached>
  [Avatar/initials] [Name] [Tier badge] [Points: 1,240] [Chevron >]

[Tapping chip opens Redemption Sheet — bottom sheet]
  [Customer summary header]
  [Section: Points]  balance, redeemable value, [amount input] [Apply]
  [Section: Punch Cards]  progress bars per card, [Redeem] if complete
  [Section: Vouchers & Rewards]  list of available codes/catalog items, [Apply]
  [Section: Manager Override]  (collapsed, requires PIN to expand)
  [Footer: Pending redemption summary — "−$12.40 applied" | Clear | Done]
```

### 14.3 POS — Customer Lookup/Resolve

```
[Search bar: "Phone, email, membership ID..."]
[Scan QR/NFC button]
[Results list: Name | Phone | Tier badge | Points]
[No match footer: + New Customer quick-add (Name, Phone required)]
```

### 14.4 Customer App/Portal — Home

```
[Header: Business name/logo]
[Balance hero: large points number, tier badge, progress bar to next tier]
[Bucket chips: Store Credit $X | Cashback $X | Gift Card $X]
[Punch cards row: horizontal scroll of progress rings]
[Section: Available Rewards]  card grid, [Redeem] → QR code modal
[Section: Activity]  ledger feed, newest first, icon per entryType
[Bottom nav: Home | Rewards | Referrals | Family/Corporate (if applicable) | Profile]
```

### 14.5 Customer App/Portal — Family/Corporate Management

```
[Header: Account name, type badge]
[Shared balance summary]
[Member list: Avatar | Name | Contribution this month | [Remove] (primary holder only)]
[+ Add Member] → invite by phone/email → "Pending invite" state until accepted
[Corporate only: Monthly statement download, Spend cap progress bar]
```

### 14.6 Owner Reporting Dashboard (`/reports/loyalty`)

```
[Tab bar: Overview | Program Performance | Liability | Tiers & Cohort | Fraud | AI Activity]

-- Overview --
[KPI row: Total active accounts | Points liability $ | Redemption rate | Open fraud flags]
[Chart: Points issued vs redeemed, trailing 90 days]

-- Program Performance --
[Table: Program | Enrolled | Redemption Rate | Breakage $ | Avg Time-to-Redeem]

-- Liability --
[Chart: Liability by bucket over time]
[Table: Expiring soon (if pointsExpiryDays configured)]

-- Fraud --
[Same table as 14.1's Fraud Flags tab, read-only summary + link to full queue]

-- AI Activity --
[Table: Date | Tool | Action | Approval status | Outcome]
```

---

## 15. Migration Plan

Sequenced so each phase ships independently and nothing user-facing breaks mid-migration.

1. **Phase 0 — Schema & service scaffolding.** Create `loyalty_accounts`, `loyalty_ledger` (target shape), `loyalty_programs`, `corporate_accounts`, `family_accounts`, `loyalty_subscriptions`, `loyalty_fraud_flags`. Build `loyalty_service.py`. No traffic yet.
2. **Phase 1 — Backfill.** One-time script maps every `customers` document into a `loyalty_accounts` document per §6.10's field table; every `loyalty_ledger` (System B), wallet `LedgerEntry` (System D), and `loyalty_awards` (System D) document is replayed into the target `loyalty_ledger` with `sourceType` preserved, in chronological order, so `balanceAfter` values reconcile. Reconciliation report compares backfilled balances against each legacy system's current balance for every customer; discrepancies are logged, not auto-corrected, for manual owner review before cutover.
3. **Phase 2 — Dual-write shim.** Legacy routes (`loyalty.py`, `loyalty_engine.py`, `loyalty_v2.py`, `commerce_v29.py`'s loyalty endpoints) are modified to call `loyalty_service.py` internally instead of writing to their own collections, while keeping their existing response shapes (no frontend changes required yet). This is the point at which the "one writer" invariant (§3.1) becomes true in production.
4. **Phase 3 — Checkout cutover.** `transactions.py` switches from its embedded hardcoded tier-discount/points calculation to calling `loyalty_service.earn()`/`redeem()` synchronously (§8.3). `POSTerminal.jsx`'s separate `loyaltyEngineAPI.redeem()` call is deleted. This is the phase that fixes the point-duplication bug and should be treated as the highest-priority phase if the plan needs to be split further.
5. **Phase 4 — New API surface + frontend migration.** Roll out `/api/v3/loyalty/*`, migrate `LoyaltyConfig.jsx`/`LoyaltyProgress.jsx`/`LoyaltyEvents.jsx`/`CustomerWalletPanel.jsx`/`GuestWalletDialog.jsx` to the new endpoints and the consolidated screens in §14, retire the legacy `/api/loyalty/*` and `/api/loyalty/v2/*` route files once nothing references them.
6. **Phase 5 — Net-new programs.** Ship Corporate, Family, Subscription (§5.10–5.12), which have no legacy equivalent and no migration risk.
7. **Phase 6 — Fraud & AI.** Ship `fraud_service.check_loyalty_event()` and register the new/extended Ash tools (§12).
8. **Phase 7 — Voucher consolidation.** Retire the duplicate voucher-issuing paths in `members.py`/`v26_commerce.py`, routing everything through `vouchers/{code}/redeem` (§7.3); confirm `nua_tools.py`'s `db.commerce_vouchers` reference is updated to the single canonical collection.

Each phase should ship behind its own PR with its own CI-green verification, matching this codebase's established workflow.

---

## 16. Non-Functional Requirements

### 16.1 Audit

Every `loyalty_ledger` write and every `loyalty_programs`/`loyalty_tiers` config change must go through `entity_service.stamped_insert/update` and `audit_service.log_event()` — no direct `insert_one`/`update_one` calls from route handlers, closing the inconsistent-application gap noted in §2.7 for this domain specifically.

### 16.2 Idempotency

`{businessId, idempotencyKey, entryType}` unique index (§6.2) is the enforcement mechanism, not just a convention — a duplicate `/earn` or `/redeem` call with the same key returns the original result (`LOYALTY_DUPLICATE_IDEMPOTENCY_KEY` is informational, not an error state to the caller) rather than double-applying. This is the concrete fix underlying §2.5/§8.3.

### 16.3 Consistency & atomicity

`/earn` and `/redeem` must use MongoDB transactions (multi-document ACID, already available given NUA POS's Mongo version if replica-set-backed — verify deployment topology) around the ledger-insert + account-balance-update pair, so a crash between the two never leaves a ledger entry with no corresponding balance change or vice versa.

### 16.4 Performance

`loyalty_accounts` balances are a cached projection specifically so hot-path reads (POS lookup, app home screen) never need to aggregate the ledger live; ledger aggregation is only for reconciliation/reporting (§10) and admin recompute tools, which can tolerate higher latency.

### 16.5 Backward compatibility during migration

Per §15 Phase 2–4, legacy endpoints keep their existing response shapes until frontend migration is complete — this spec is additive/consolidating at the data layer first, UI-breaking only at the very end of the migration.

---

## 17. Open Questions (require an owner decision before/around Phase 5+)

1. **Points expiry**: not present in any legacy system. Recommended (`pointsExpiryDays` on `loyalty_programs.config`) but needs an owner decision on default policy and whether it's retroactive to existing balances.
2. **Tier downgrade**: legacy systems only ever upgrade. §5.4 makes downgrade explicit and configurable, but the default (`downgradeOnThresholdLoss: false`) needs owner confirmation as it's a customer-experience-sensitive choice.
3. **Cross-business account linking**: explicitly out of scope (§13) — confirm this is acceptable for the current single-operator-multi-location use case or needs to be pulled into an earlier phase.
4. **Corporate invoice billing**: §5.10/§6.7 models the loyalty side only; actual invoicing/payment collection integration is a separate spec this document assumes exists or is forthcoming.
5. **Subscription payment provider**: §5.12 assumes an external recurring-billing integration; needs to be named before Phase 5 implementation can start.
