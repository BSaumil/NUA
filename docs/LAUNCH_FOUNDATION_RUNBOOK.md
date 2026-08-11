# Foundation Day runbook — pilot venue go-live

One-time steps to run against the pilot venue's database before handing it
over, in order. All three endpoints are owner-only and idempotent — safe to
re-run if a step is interrupted.

## 1. Multi-tenant backfill

Stamps `businessId="default"` onto any pre-existing document that predates
tenant tagging, and assigns a storefront slug to any business missing one.
Run once, right after the pilot venue's real data (menu, staff) has been
entered and before the venue starts taking live orders.

```
POST /api/business/backfill-tenant
Authorization: Bearer <owner token>
```

Response: `{"backfilled": {<collection>: <rows modified>, ...}, "total": N}`.

**Verify:** `total` should be `0` on a second call (nothing left to
backfill). If it isn't, something is still writing untagged rows — stop and
find the write path before going live, don't just re-run this repeatedly.

## 2. License enforcement — decision: leave OFF for Aug 15

`LICENSE_ENFORCEMENT_ENABLED` stays unset (defaults to `false`).

Why: `LicenseEnforcementMiddleware` only does anything once a
`tenant_licenses` document exists for the tenant (`middleware/license_middleware.py:85`
— no license row means "allow all", regardless of the flag). The Aug 15
launch is one pilot venue that isn't going through subscription billing yet,
so no license row will exist and flipping the flag on would be a pure no-op
today — except for the added per-request DB lookup, and the risk that a
stray `tenant_licenses` row (leftover test data, a manual DB edit) puts the
tenant into a non-`active` state and silently blocks `/api/transactions` —
i.e. breaks checkout — on the one day it must not break.

Turn it on later, deliberately, as part of the real multi-tenant billing
rollout: once there's a tested onboarding flow that creates the license row
on purpose, and a test confirming an `active` license still allows POS
sales end-to-end.

## 3. Purge demo data

Deletes every row the startup seeders created (`seed_demo_customers`,
`seed_alcohol_catalog`) — the 5 sample guests and their generated
reservations/transactions/feedback, plus the starter alcohol catalog
(categories, products, stock units, sell variants). Run this last, after
the pilot venue's real menu and any real customer data have been entered
(purge only removes rows tagged `isDemo: true` at seed time — it can't
touch anything the venue entered themselves).

```
POST /api/business/purge-demo-data
Authorization: Bearer <owner token>
Content-Type: application/json

{"confirm": "PURGE"}
```

Response: `{"purged": {<collection>: <rows deleted>, ...}, "total": N}`.
Missing/wrong `confirm` value returns `400` and deletes nothing — the
explicit token exists so this can't fire from a bare POST or a UI
misclick. Never touches `businesses`, `auth_users` (admin/staff),
`changelog`, or `chart_of_accounts` — none of those are seeder-tagged.

Covered by `backend/tests/inprocess/test_demo_purge.py`.
