# NUA POS — PRD v15.0

## Brand
NUA. Custom RBAC, PIN-only staff login optional, JWT login.

## Navigation (v15, Feb 2026)
- **Sidebar removed** entirely from layout.
- **BottomDock** is now the primary navigation, fixed at the bottom of every authenticated page.
  - Role-based quick actions (4 per role): Owner: POS · Dashboard · Bookings · Items. Manager: POS · Bookings · Kitchen · Roster. Cashier: POS · Bookings · Customers · Loyalty. Kitchen: Kitchen · Pre-Shift · Inventory · AI Pantry. Barista: POS · Drinks · Customers · Loyalty.
  - **More** button opens a fullscreen splash modal grouping every feature the user can access (Operations, Reservations, Items, Menu Engineering, Team, Customers, Accounting, System).
  - Logout button on dock (right side).
- **Default landing**: `/pos` for ALL roles (owner included). Dashboard moved to `/dashboard` and is reachable via owner's dock or splash.

## POS Terminal (v15)
- Smaller product cards (h-16 image, 3-6 column compact grid).
- Category-wise sections when "All" is selected (sticky headers per category, populated dynamically from `/api/categories`).
- Bigger 440px cart panel (white card, rounded shadow).
- **Swipe gestures on cart items**:
  - **Left swipe (>80px)** → DELETE the item (red bg revealed).
  - **Right swipe (>80px)** → REPEAT the item, qty +1 (green bg revealed).
- Quantity ± buttons preserved with `data-no-swipe` zone so they don't conflict with swipe.
- Hint text: "← swipe delete · repeat swipe →" on each cart item.
- Image fallback: `https://placehold.co/...` when product image is empty.

## Items Module (v14)
6 sub-pages: Item Library, Categories, Modifiers, Discounts & Offers, Comp/Void, Payment Links.
- **Payment Links**: now includes a **QR Code** modal (data-testid `qr-modal`) per link with download SVG + copy URL — perfect for instagram bios, table tents, shop windows.

## Roster (v14)
- @dnd-kit drag-and-drop on weekly grid; daily cost recalculates live.
- PUT `/api/staff/roster/{id}` persists day moves.

## Credentials (Seed-healed)
Owner: `owner@nuva.com / NuvaOwner2026!`  
Manager: `manager@nuva.com / Staff2026!` (Sarah Manager — role auto-healed to `manager` on startup)  
Cashier: `cashier@nuva.com / Staff2026!` (Tom Cashier)  
Kitchen: `kitchen@nuva.com / Staff2026!` (Chef Kim)  
PINs: 25 owner · 00 manager · 11 cashier · 22 kitchen

## Testing
21 iterations completed. Iteration 21: 100% on UX refactor — swipe gestures, role-based dock, splash modal, default-to-POS routing, Payment Link QR all verified working in Playwright automation.

## Backlog
- P1: SendGrid integration for autonomous nightly EOD emails
- P2: Nightly EOD cron job
- P3: Real Uber Eats / DoorDash delivery API hookups
- P4: Optional — split POSTerminal.jsx (746 lines) into sub-files (Cart, Payment dialogs, etc.)
