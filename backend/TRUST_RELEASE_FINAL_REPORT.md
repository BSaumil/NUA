# NUA POS Trust Release — Final Report

**Date:** 2026-09-14
**Branch:** `trust-release/p0-security-foundation` (50 commits, all pushed to origin — none merged to `main`)
**Verdict: CONDITIONAL-GO.** Every phase the original directive named (P0 security foundation, P0.3 tenant isolation, Phase 3-5 feature work, Phase 6-7 reliability/docs) is complete, tested, and pushed. This is not the same claim as "no security issues exist" — it's an honest account of what was audited, what was found, what was fixed with a regression test behind it, and what remains a documented, deliberate gap. Read the conditions in §7 before treating any part of this platform as cleared for a real multi-tenant deployment carrying real customer data.

This supersedes `TRUST_RELEASE_INTERIM_STATUS.md` (which reported a **NO-GO** interim checkpoint, written mid-effort when 24+ of the original 34 audited files were still completely unscoped and Phase 3-5 hadn't started). That document is left in place as the historical record of how this effort progressed; this one is the closing account.

---

## 1. What "done" means here

Every fix described below was validated the same way, without exception: full backend test suite (`cd backend && python -m pytest tests/inprocess -q`) run and green **before** every commit, never a partial run against just the touched files. Suite size grew from **469 tests** (pre-Trust-Release baseline) to **613 passing** now — every fix added its own regression test, not just a manual check. mongomock-motor backs the whole suite; no live database or real customer data was ever touched. No credentials, certifications, or regulatory approvals were fabricated or implied anywhere in this work.

---

## 2. P0 — security & safety foundation

| Item | Status | Evidence |
|---|---|---|
| **P0.1 — CI restored & strengthened** | DONE | `.github/workflows/ci.yml`: flake8, mypy (reporting), pip-audit (reporting), gitleaks secret-scan, npm audit, e2e-tests job. |
| **P0.2 — Unsafe secret fallbacks removed** | DONE | 7 files (`auth.py`, `licensing.py`, `finalize.py`, `commerce_v29.py`, `guest_session.py`, `middleware/actor_context.py`, `services/connect/credentials.py`) now fail closed instead of trusting a hardcoded default key. |
| **P0.4 — Webhooks fail closed** | DONE | Stripe billing (`licensing.py`) and checkout (`integrations.py`) webhooks reject unsigned/misconfigured payloads (503/400) instead of accepting them or silently swallowing signature failures into a 200. Coinbase's webhook confirmed already correct. |
| **P0.5 — Ash (AI agent) tool-execution safety** | DONE, residual gaps documented | Owner-only audited kill switch enforced at every entry point (including the approval-execute bypass that used to skip it entirely); high/critical-risk tools can no longer be set to auto-execute; every blocked/rejected attempt is now audited; idempotency-key support wired through chat/planner/direct-API; rollback added for the directive's 7 named action types. Found and fixed a real functional bug along the way: `mark_dish_86` wrote to a field nothing in the app ever read — it silently 86'd nothing, anywhere, since the feature was built. Residual: rollback for ~15 lower-risk tools, true concurrent-race testing, whether manager-level approval of high-risk actions should require owner instead. Full detail: `ASH_SAFETY_REMAINING_WORK.md`. |
| **P0.6/P0.7/P0.8 — Financial & offline integrity** | DONE, residual gaps documented | Cumulative refund cap made atomic (was read-then-write, exploitable by two concurrent requests); online-order status transitions atomic with 409-on-conflict; stock floor added; offline-queue replay dedup end-to-end (`clientOpId`, sparse-unique index, wired into the frontend's `offlineQueue.js`). Two genuine-concurrency tests (`ThreadPoolExecutor`, real HTTP requests in flight). Residual: Stripe/Coinbase checkout-session idempotency, crypto refunds don't exist at all, no fully-atomic online-order transition, no Playwright offline E2E. Full detail: `FINANCIAL_OFFLINE_INTEGRITY_REMAINING_WORK.md`. |
| **Dependency vulnerability debt** | PARTIAL | `pip-audit` wired into CI. 11 low-risk packages bumped (PyJWT, urllib3, requests, python-multipart, etc.), full suite re-verified green. 152 advisories remain, concentrated in `starlette`, `cryptography`, `aiohttp`, `pymongo` — deliberately not bumped blind (real breaking-change risk, need their own dedicated pass). Full detail: `SECURITY_DEPENDENCY_DEBT.md`. |

## 3. P0.3 — tenant isolation, the largest single effort

The original audit found **38 of 58 backend route files with zero `businessId` scoping**. Two root causes were found and fixed first, each explaining a large fraction of everything downstream:

1. **`middleware/actor_context.py`** — `ActorContextMiddleware` let a client-supplied `X-Tenant-Id`/`X-Business-Id` header override the JWT-derived businessId on write. JWT membership is now authoritative.
2. **`services/entity_service.py`'s `_stamp_new()`** — used `doc.setdefault("businessId", ...)`, a no-op against a key that already exists with value `None`, which every `BaseEntity`-derived model (Product included) declares as a real field. **Every product ever created via `POST /api/products` was stamped `businessId=None`, regardless of who created it** — every business's entire catalogue (cost, stock, pricing) was visible to every other business on the deployment. Arguably the single highest-impact fix in the whole effort, found by a cross-tenant test for an unrelated file failing for a reason that didn't match what it was testing.

**The original 34-file list is now fully closed — 0 remaining.** 32 files fixed, 2 (`table_ordering.py`, the guest-facing portion of `public.py`) deliberately deferred — both are genuinely public-by-design endpoints with no business-resolution signal reachable in their current request shape; fixing them is a real feature-level addition (a `?business=` param, the pattern `online_orders.py`'s public storefront already uses), not a mechanical scoping fix, and neither corrupts data cross-tenant, only mixes read visibility.

Beyond the 34-file list, **two escalated findings**, each bigger than the entire original list combined, discovered mid-pass and given their own dedicated fix cycles:

- **`services/accounting_service.py` + `routes/accounting.py`** (1,511 lines) — the entire double-entry general-ledger system (chart of accounts, journal postings, P&L/balance-sheet/cash-flow/trial-balance/general-ledger reports, AP/AR, deposits, bank reconciliation, budgets) had zero businessId scoping. Every business's real financial statements were computed from every business's transactions. Fixed at the root (`post_entry()`, the single choke point every posting funnels through) with the same actor-context-default pattern used throughout; chart of accounts re-keyed to `(code, businessId)`. New test file: `test_accounting_tenant_isolation.py`.
- **`routes/ops.py` + `services/backup.py`** — `GET /ops/backup` (owner-gated, no tenant check of its own) let **any owner account on the deployment download a complete `.tar.gz` of every business's data** — customers, transactions, refunds, kitchen orders, reservations, vouchers, loyalty accounts, and `auth_users` password hashes. Fixed: scoped to the caller's own business.

**Nine-plus confirmed zero-authentication endpoints** (reachable with no credential at all, or by any authenticated user regardless of role/business) were found across `bill_split.py` (3 endpoints), `awards.py` (6), `reservations.py`'s floor-plan and waitlist CRUD, `channel_menus.py` (2), `loyalty.py` (4), and `loyalty_engine.py`'s reports. Several **cross-tenant live-data-corruption bugs** beyond simple missing filters: `table_states` (two businesses seating a same-numbered table silently overwrote each other's live course/guest data), `ash_insights`/`ash_briefings`/`ash_plans` (same-day/same-key collisions across businesses), `db.awards` (uninstalling a Fair Work award for one business uninstalled it for every business sharing that award code), a live WebSocket feed (`/ws/live`) that broadcast every business's sales/roster/gift-card activity to every connected client regardless of business, and an automation-rules engine (`emit_event()`) that ran every business's active rules against every other business's events, not just the triggering business's own.

Full, file-by-file citations with exact fix descriptions: `TENANT_ISOLATION_REMAINING_WORK.md` (187 lines — the source of truth this report summarizes rather than duplicates).

### 3a. Found during Phase 3-5 feature work (not part of the original 34, found by building on top of them)

Consistent pattern across all four: building a new feature surfaced a severe, previously-undiscovered gap in the code the feature depended on. Each was fixed before the feature was built on top of it, not worked around.

- **`routes/loyalty_v2.py`** ("Loyalty 2.0") — badge/milestone catalogs seeded once globally (every business after the first got no catalog of its own), seasonal challenges/referrals/leaderboard had zero scoping, `GET /progress/{id}`/`POST /evaluate/{id}` had no ownership check.
- **`routes/reservations.py`'s waitlist API** — the entire staff-facing waitlist had no auth dependency at all.
- **`routes/loyalty_engine.py`'s reports + `loyalty_ledger`** — the liability/locked-accounts/fraud-flags reports were fully unscoped, and the root cause underneath them: `loyalty_ledger` (every points earn/redeem event) was never stamped with `businessId` at any real write site, making the reports' scoping a no-op even once added.
- **`routes/reservations.py`'s core reservation CRUD — the entire booking system.** `models/reservation.py` had no `businessId` field at all; `GET /reservations`'s own pre-existing `tenant_scope_filter` call had been a complete no-op since it was written. Most single-reservation endpoints (`GET/PUT/DELETE /{id}`, seat, complete, no-show, auto-assign, ai-assign-table, guest-lookup, guest-intel, day-counts, blackouts, walk-in seating) had zero auth dependency at all — carrying direct guest PII (name, phone, email, dietary/allergy notes). This is on par with the `_stamp_new` and accounting findings in severity.

## 4. Phase 3-5 — Voice POS, Loyalty 3.0, Booking 3.0

Scope for this phase was inferred, not handed down verbatim (the original spec text is not in this session's context) — proposed to and confirmed by the user before building, per the session's own record.

- **Voice POS.** The `/agent/voice-command` router existed and was wired into the UI (`AgentDashboard`), but its target endpoint had been deleted — the mic button silently did nothing. Rebuilt end-to-end (`VoiceCommandButton.jsx`, real `MediaRecorder` capture, a real POST to `/api/agent/voice-command`) and **verified in a real browser** — a standalone uvicorn instance + a real `craco` dev server + Playwright with a fake audio device, screenshots confirming the mic button renders across pages, recording state toggles, and a real request fires on stop. The AI Phone Agent's "order" intent now creates a real kitchen ticket via `services/channel_orders.py` (with tenant-scoped product matching) instead of only logging what it heard.
- **Loyalty 3.0.** A unified guest-facing loyalty passport (points, tier, badges, milestones, active subscription status) is what surfaced the `loyalty_v2.py` finding above. Tier perks are now enforced for real: a Silver+ member joining the waitlist is matched by phone against the business's own customers and jumps the queue (never ahead of an earlier-joined fellow member) — both in staff's ordering and the guest-facing "ahead of you" count. A redemption-cost-vs-incremental-spend ROI report was added, explicit in both its docstring and its JSON response's `methodology` field that it's a same-business snapshot comparison, not a causal cohort study (this codebase doesn't reliably capture per-visit spend timestamped against a loyalty join date, so a real cohort study isn't possible from data that exists today).
- **Booking 3.0.** Deposits are now collected through a real Stripe Checkout session (`POST /reservations/{id}/request-deposit`, same pattern `online_orders.py`'s checkout already established), not a staff-ticked checkbox. `mark_no_show` forfeits a deposit only when it was actually collected through a real session (`depositPaid` AND `depositSessionId` both set) — never a bare flag; the response says plainly whether a fee was actually captured. A per-business cancellation-policy engine (`services/cancellation_policy.py`, configurable free-cancellation cutoff, default 24h, genuinely per-business from day one unlike `loyalty_config`) decides refund-in-full vs. forfeit-as-fee on cancellation. `cancel`/`restore` both attempt a real Stripe refund via the existing `refund_stripe_payment` helper, best-effort. The waitlist's "Notify" button (`Waitlist.jsx`) used to just flip a status label with a toast claiming "Guest notified" — now fires a real `utils.notifications.send_sms`.

  **Honest scope limit, stated in the code:** NUA has no saved-card / off-session-charge capability — only Stripe's one-time hosted Checkout redirect (confirmed: `emergentintegrations.payments.stripe.checkout`'s `StripeCheckout`/`CheckoutSessionRequest` is used everywhere in this codebase, never a `SetupIntent` + later off-session `PaymentIntent`). A walk-in/phone/online booking that never had a deposit collected in advance still can't be charged a no-show fee after the fact. Building real saved-card capture is a materially larger, separate feature (PCI-relevant card-vaulting), not attempted here.

  Also untestable end-to-end in this sandbox: `STRIPE_API_KEY` isn't configured, so `request_deposit` always exercises its graceful `{"configured": False}` degradation path rather than a real Checkout session — the test suite covers exactly that path honestly, not a simulated real charge.

## 5. Phase 6-7 — reliability & documentation

- **Reliability.** `services/observability.py` (structured request logging, unhandled-exception capture to `db.error_log` with a request id surfaced to the client, a deep `/api/health` check covering Mongo + scheduler liveness) predates this Trust Release effort and needed no new infrastructure. What this phase actually found: `routes/reservations.py`'s status-changing endpoints wrote their audit-log entry **unguarded**, after the real state change had already succeeded — a transient Mongo hiccup on that write would 500 an otherwise-successful cancel/no-show/approve/reject/restore. Fixed with the codebase's own established `utils.errors.log_and_continue` best-effort pattern across all 7 call sites, with 2 new regression tests proving a broken audit log no longer fails the real operation.
- **Documentation.** `README.md` updated: a new changelog entry for this whole effort, corrected test-running instructions (`tests/inprocess` is the fast mongomock suite this whole effort was validated against; the flat `tests/test_iteration*.py` files need a live server and were never part of this loop), the current 613-test count, new API surface entries, and — the change that matters most for honesty — a new roadmap section listing the still-open P0 gaps (remaining settings singletons, no saved-card capability, `table_ordering.py`/`public.py`'s deferred scoping) instead of only shipped features. This report and `TENANT_ISOLATION_REMAINING_WORK.md` are linked directly from the README's header, ahead of the word "production-ready" that predates this whole audit.

## 6. Everything still open, in one place

| Area | What's open | Where it's tracked |
|---|---|---|
| Tenant isolation | `table_ordering.py` and `public.py`'s guest-facing portion (no business-resolution signal reachable yet); several `db.settings`/`loyalty_config` singleton documents shared by every business; a handful of collections (`timecards`/`shifts`/`roster_shifts`, `course_events`) with no `businessId` field on the schema itself | `TENANT_ISOLATION_REMAINING_WORK.md` |
| Ash agent safety | Rollback for ~15 lower-risk tools; true concurrent-race testing; whether manager-level approval of high-risk actions should require owner instead | `ASH_SAFETY_REMAINING_WORK.md` |
| Financial/offline integrity | Stripe/Coinbase checkout-session idempotency (double-click can create two live sessions); crypto refunds don't exist at all; online-order status transition isn't fully atomic (409-on-conflict closes the concrete race, not every theoretical one); no Playwright offline E2E | `FINANCIAL_OFFLINE_INTEGRITY_REMAINING_WORK.md` |
| Dependency debt | 152 advisories remain; `starlette`/`cryptography`/`aiohttp`/`pymongo` need a dedicated, careful bump-and-regress pass each | `SECURITY_DEPENDENCY_DEBT.md` |
| Payments | No saved-card/off-session-charge capability at all — caps what "charge a no-show fee" or a future subscription auto-renew can do | This report, §4 |

## 7. Conditions for an unqualified GO

This is a CONDITIONAL-GO, not a GO, because the items in §6 are real and, in two cases, non-trivial:

1. **Before onboarding a second real business onto a shared deployment**, resolve or explicitly accept the `db.settings`/`loyalty_config` singleton gap — right now two businesses sharing a deployment would share one loyalty program configuration, one set of business hours/print-routing settings, and (for `table_ordering.py`/`public.py`) one mixed guest-facing product/event listing.
2. **Before processing real payments at any meaningful volume**, close the Stripe/Coinbase checkout-session idempotency gap (§6) — a double-click can currently create two live charges for one cart.
3. **Before relying on this for real accounting/compliance output**, note that the accounting/tenant-isolation fix (§3) was validated against the in-process test suite only, never against a real multi-business production dataset — recommend a manual spot-check of a real (or realistic staging) multi-tenant deployment's P&L/balance-sheet output before trusting it for statutory reporting.
4. **Schedule the deferred dependency bumps** (`starlette`, `cryptography`, `aiohttp`, `pymongo`) rather than leaving 152 known advisories open indefinitely — none block this verdict today (no known-exploitable path to any of them was found in this audit), but they're real, tracked debt.

None of the above are reasons to discard this work — they're the honest, specific, actionable list of what "done" doesn't yet cover, which is the entire point of writing this report rather than declaring victory.

---

*No credentials, certifications, or regulatory approvals have been fabricated or implied anywhere in this work. No live customer data was touched — all testing ran against the in-process mongomock test database. All 50 commits are on `trust-release/p0-security-foundation`, pushed to `origin`, not merged to `main`.*
