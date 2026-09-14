# Tenant isolation — remaining work

Tracks progress against the audit's finding that 38 of 58 backend route files had zero `businessId` scoping. This file exists so the remaining gap is recorded precisely rather than silently left implicit — per the Trust Release directive, "record the exact blocker and continue."

## Fixed in this pass

| File | What was fixed |
|---|---|
| `middleware/actor_context.py` | The root cause: `ActorContextMiddleware` let a client-supplied `X-Tenant-Id`/`X-Business-Id` header override the JWT-derived businessId. JWT membership is now authoritative; the header is only consulted when there's no JWT at all (the original partner-integration use case). |
| `routes/commerce_v29.py` | Voucher creation no longer trusts a client-supplied `businessId` in the request body over the authenticated caller's own. |
| `routes/kitchen.py` + `models/kitchen_order.py` | Added `businessId` to the `KitchenOrder` model; every read/write endpoint (list, create, start/ready/served/cancel, hold/fire/ready/serve-course, timings, priority, prep-list) now scopes or stamps by it. `fire_course_internal` takes an optional `business_id` used by both the HTTP route and the scheduler/auto-fire callers (`services/coursing_scheduler.py`, `routes/coursing.py`). |
| `routes/payroll.py` | `calculate_payrun`/`commit_payrun`/`payroll_register`/`payroll_ytd`/`payslip_pdf`/`roster_compliance` all scoped — previously a payroll run for one business pulled in *every* business's active staff and wages. `timecards`/`shifts` don't carry their own `businessId` (schema gap, see below) so those are filtered transitively through this business's own staff list; `payruns`/`payrun_rows` now get `businessId` stamped going forward. |
| `routes/gamification.py` | `compute_staff_performance` (leaderboard), `smart_distribute_tips`, `quarterly_review` all scoped — same "one tenant's data mixed into another's" pattern as payroll, now fixed the same way. |
| `routes/finalize.py` (partial) | Customer wallet lookups (`guest_wallet`, `lookup_by_token`, `_resolve_wallet_context` → Apple/Google wallet passes) were the highest-risk finding in this file — any authenticated staff member of *any* business could pull *any* customer's name/points/store-credit balance by customer_id with no ownership check. Fixed. `preshift_briefing`'s product/promotion/roster/timecard queries also scoped. |

Full backend suite re-verified green after every file above (`python -m pytest tests/inprocess -q`).

## A deeper, separate finding surfaced while fixing payroll/gamification/preshift

`timecards`, `shifts`, and `roster_shifts` documents don't carry a `businessId` field at all — not just unfiltered queries, the schema itself has no tenant tag on these three collections. The fix applied here (filter transitively through the calling business's own `auth_users` staff list) closes the isolation gap without a migration, but it's worth flagging as its own item: any *other* code path that queries these three collections directly by some key other than a pre-filtered staffId list would still need the same transitive-filter treatment, since there's no `businessId` on the document itself to scope by directly.

`db.business_settings` and `db.settings` (used for e.g. print-routing config) are **singleton documents** (`{"key": "main"}` / `{"key": "print_routing"}`) with no per-tenant scheme whatsoever — every business on this deployment currently shares one ABN/business-name/GST-settings record and one print-routing config. This is a real architectural gap, but re-keying these collections by businessId touches enough call sites (business_settings alone is read in `payroll.py`, `advanced_features.py`, and elsewhere) that it deserves its own dedicated migration task rather than a rider on this pass.

## NOT yet scoped — 34 files, by the audit's original count

`advanced_features.py`, `ai_pantry.py`, `approvals.py`, `awards.py`, `bill_split.py`, `bookings_inbox.py`, `changelog.py`, `channel_menus.py`, `coursing.py`, `crypto_payments.py`, `guest_session.py`, `hq.py`, `identity.py`, `licensing.py`, `loyalty.py`, `measured_inventory.py`, `menu_features.py`, `notifications.py`, `nua.py`, `ops.py`, `phase_ef.py`, `phase_ef_wave2.py`, `public.py`, `realtime.py`, `repo_sync.py`, `reservation_features.py`, `rules_engine.py`, `social_media.py`, `super.py`, `table_courses.py`, `table_ordering.py`, `temperature.py`, `v25_suite.py`, `voice_calls.py`.

Plus the remaining endpoints in `routes/finalize.py` itself: booking day-rules, channel state/schedule, low-stock PDF/XLSX export, AI-pantry order-sheet PDF, automation triggers.

Some of these are legitimately public/unauthenticated by design (`public.py`, parts of `guest_session.py`) where "tenant scoping" means something different (scoping by the resource being looked up, not by a staff JWT) — those need a case-by-case read, not a mechanical copy of the `tenant_scope_filter` pattern used above.

**Recommended order for the next pass**, ranked by the same "real PII/financial data first" logic used for this one: `bill_split.py` and `identity.py` (guest PII), `measured_inventory.py`/`awards.py` (stock/cost data — margin-sensitive), `reservation_features.py`/`table_courses.py`/`table_ordering.py` (booking/guest data, same family as the kitchen.py fix), `hq.py` (explicitly a cross-location feature — needs care to scope "correctly restricted" without breaking its actual purpose), then the rest.
