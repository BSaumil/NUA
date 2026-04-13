# NUVA POS — Product Requirements Document

## Original Problem Statement
Full-featured Square POS clone with comprehensive restaurant management, evolved into an all-in-one hospitality platform. Includes EatClub-style member marketing, AI-powered supply chain, staff RBAC, multi-business support, table-side QR ordering, integrations hub, email marketing, tip management, training mode, end-of-day reports, transaction receipts/refunds, and desktop/mobile builds.

## Tech Stack
- Frontend: React.js, Tailwind CSS, Shadcn UI, qrcode.react, PWA
- Backend: FastAPI (Python), 16 modular route files
- Database: MongoDB (AsyncIOMotorClient)
- Payments: Stripe (emergentintegrations)
- AI: GPT 5.2 (emergentintegrations)
- Auth: JWT + bcrypt, role-based access control
- Desktop: Electron (Windows .exe)
- Mobile: Capacitor (Android APK)

## Architecture (v5.1.0)
```
/app/backend/routes/
  auth.py             — JWT auth, RBAC, staff CRUD, owner reports, seeding
  products.py         — Products, Categories, Modifiers, Stock Adjustment
  transactions.py     — Transactions (detail+refunds), Promotions CRUD, Gift Cards, Refunds
  customers.py        — Customers, CRM, Feedback
  reservations.py     — Reservations, Floor Plans, Waitlist
  kitchen.py          — Kitchen Display, Prep Management
  analytics.py        — Pre-Shift, Command Center, Menu Engineering, Forecasting, Roster
  automation.py       — Automation Rules & Alerts
  settings.py         — Locations CRUD, Users, Printers, Offline, EFTPOS, Staff
  loyalty.py          — Loyalty Rewards, Events, QR Menu
  public.py           — Booking Portal, QR/UPI/Split Payments
  table_ordering.py   — Table-Side QR Ordering
  integrations.py     — 18 Integrations Hub + Stripe Checkout
  ai_pantry.py        — AI Smart Pantry (GPT 5.2)
  members.py          — EatClub-style Member Portal, Vouchers, Social Sharing
  multi_tenant.py     — Multi-Business Management
  advanced_features.py — Tips, Training Mode, EOD Reports (comprehensive), Email Marketing, Business Settings
```

## Completed Phases
- Phase 1-5: Core POS, Reservations, CRM, KDS, Analytics, Loyalty, PWA
- Phase 6: Booking Portal, QR/UPI/Split Payments, Backend Refactoring
- Phase 7: Table-Side QR Ordering, 18 Integrations Hub, Stripe
- Phase 8: Staff Auth & RBAC, AI Smart Pantry, Member Portal, Multi-Business
- Phase 9: Email Marketing, Tip Management, Training Mode, EOD Reports, APK/EXE Builds
- Phase 10 (Current): Major Bug Fixes — Products/Promotions CRUD, Inventory Stock Adjustment, Forecasting fix, Settings real API, Accounting with Receipts/Refunds, Comprehensive EOD Reports

## Phase 10 Bug Fixes & Enhancements

### Products & Promotions (Fixed)
- Add/Edit/Delete products with full dialog forms
- Add/Edit/Delete promotions with dialog forms
- Search products by name

### Inventory (Fixed)
- Replaced mockData with real API data
- Stock Adjustment dialog per product (add/remove with reason tracking)

### Forecasting (Fixed)
- Fixed field name mismatches between frontend and backend
- Handles both old and new API response formats gracefully

### Settings (Fixed)
- Locations tab: real API data with Add/Edit/Delete (was using mockData)
- Staff tab: real API data showing actual seeded users with Edit/Add/Delete (owner only)
- Business Info tab: saves to database (was non-functional)
- Training Mode tab: toggle works

### Accounting & Transactions (Enhanced)
- Transaction table with search
- Transaction detail dialog (items, subtotal, GST, discount, total, refunds)
- Receipt preview dialog with Print and Email buttons
- Refund dialog (amount, reason, refund method)

### End-of-Day Reports (Enhanced)
- Period selector: Today, Yesterday, This Week, This Month, This Quarter, Custom Range
- 5 section tabs: Overview, Item Sales, Categories, Customers, Hourly
- Overview: Gross/Net Sales, Avg Ticket, GST, Payment Methods, Refunds, Tips
- Item Sales: Product-level qty sold and revenue
- Categories: Category breakdown with visual bars
- Customers: Covers, walk-ins, new vs returning, avg spend, top spenders
- Hourly: Sales by hour with visual bars

## Auth Credentials
- Owner: owner@nuva.com / NuvaOwner2026!
- Manager: manager@nuva.com / Staff2026!
- Cashier: cashier@nuva.com / Staff2026!
- Kitchen: kitchen@nuva.com / Staff2026!

## Testing: 9 iterations, all 100% pass (42 backend tests in latest)

## Backlog
- P2: AI insights integration for EOD reports (autonomous nightly analysis)
- P3: Real email sending via SendGrid/SES integration
- P3: Real Uber Eats/DoorDash API integrations when keys available
- P3: Receipt email delivery (currently shows toast only)
