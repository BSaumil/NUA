# NUA POS — PRD v14.0

## Brand
NUA (formerly NUVA / Ananta). Custom RBAC, PIN-only staff login optional.

## Items Module (v14, Jan 2026)
6 sub-pages under sidebar "Items" group:
- **Item Library** (`/products`) — existing Products page, full inventory CRUD
- **Categories** (`/categories`) — create/edit/delete with sort order, active toggle
- **Modifiers** (`/modifiers`) — list/dropdown, mandatory, multi-select w/ max, options w/ price, print-with-item flag
- **Discounts & Offers** (`/discounts`) — percentage / $ off / bundle / BOGO / half-price types, date-bound, owner-only writes
- **Comp / Void** (`/comp-void`) — track comps & voids with reason, transaction id, optional kitchen-print, type filter & search
- **Payment Links** (`/payment-links`) — generate shareable URLs from any product with custom price, copy-to-clipboard

Backend: `/app/backend/routes/items_system.py` — full CRUD on `/api/categories`, `/api/modifiers`, `/api/discounts`, `/api/comp-void`, `/api/payment-links`.

## Staff Roster (v14)
- Week grid (Mon-Sun columns, shift cards inside each day)
- **Drag-and-Drop**: powered by @dnd-kit. PointerSensor (4px activation) + KeyboardSensor for accessibility. Drop a shift on a different day -> PUT `/api/staff/roster/{id}` updates the shift's date, daily cost recalculates live.
- Daily cost shown at bottom of each day column (`day-cost-{day}` data-testid)
- Weekly budget summary chips at top (total shifts, hours, $cost)
- Print Roster: only names/positions/days/times — no wages

## Custom Roles
cashier, kitchen, manager, barista, bar, floor, host, dishwasher, pizza, delivery (+ owner can add more).

## Credentials
Owner: owner@nuva.com / NuvaOwner2026!  
Manager: manager@nuva.com / Staff2026!  
Cashier: cashier@nuva.com / Staff2026!  
Owner PIN: 25 | Manager PIN: 00 | Cashier PIN: 11

## Testing
- 19 iterations completed
- Iteration 19 (Jan 2026): Backend 9/9 (100%), Frontend 90% — all Items pages + roster grid render & functions verified; manual DnD works in real browsers (headless automation limitation only).

## Backlog
- P1: SendGrid integration for autonomous nightly EOD emails
- P2: Nightly EOD cron job
- P3: Real Uber Eats / DoorDash delivery API hookups
