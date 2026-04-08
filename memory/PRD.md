# Ananta POS - Product Requirements Document

## Original Problem Statement
Pixel-perfect clone of a Square POS system with comprehensive accounting capabilities, including direct BAS and GST filing. Evolved into a full restaurant management suite with OpenTable-style features, table-side ordering, and 18+ hospitality integrations.

## Core Features
- Fast checkout with 6 payment methods (Card, Cash, QR Code, UPI, Stripe, Split Payments)
- Digital receipts, custom promotions, offline capability
- LAN printer configuration, EFTPOS integration
- Full accounting with BAS/GST filing

## Tech Stack
- Frontend: React.js, Tailwind CSS, Shadcn UI, qrcode.react, PWA
- Backend: FastAPI (Python), Modular Routes Architecture (12 route files)
- Database: MongoDB (AsyncIOMotorClient)
- Payments: Stripe (emergentintegrations library)

## Architecture (v3.1.0 — Modular)
```
/app/backend/
  server.py              — Slim orchestrator
  database.py            — Shared MongoDB connection
  routes/
    products.py          — Products, Categories, Modifiers
    transactions.py      — Transactions, Promotions, Gift Cards, Refunds
    customers.py         — Customers, CRM Profiles, Feedback
    reservations.py      — Reservations, Floor Plans, Waitlist
    kitchen.py           — Kitchen Display, Prep Management
    analytics.py         — Pre-Shift, Command Center, Menu Engineering, What-If, Forecasting, Roster, Predictive
    automation.py        — Automation Rules & Alerts
    settings.py          — Locations, Users, Printers, Offline, Tables, EFTPOS, Staff
    loyalty.py           — Loyalty Rewards, Events, QR Menu
    public.py            — Public Booking Portal, QR/UPI/Split Payments
    table_ordering.py    — Table-Side QR Ordering (public, mobile-first)
    integrations.py      — Integrations Hub + Stripe Checkout
```

## Completed Phases
- Phase 1: Reservations, Floor Plan, Waitlist (DONE)
- Phase 2: Guest CRM & 360 Profiles (DONE)
- Phase 3: Kitchen Display System (DONE)
- Phase 4: Pre-Shift Dashboard, AI Command Center, Menu Engineering, Automation Engine (DONE)
- Phase 5: Loyalty, Forecasting, What-If Simulator, QR Menu, PWA (DONE)
- Phase 6: Booking Portal, QR/UPI/Split Payments, Backend Refactoring (DONE)
- Phase 7: Table-Side QR Ordering, Integrations Hub (18 apps), Stripe Payments (DONE - April 2026)

## Phase 7 Details

### Table-Side QR Ordering (/table/:tableId)
- Public page, mobile-first dark theme
- Customer scans QR on table, sees menu with categories and images
- Add items to cart, provide name/notes, place order directly to kitchen
- Live order status tracking (new → preparing → ready → served)
- Orders appear in Kitchen Display (KDS) with table number
- Staff can get QR codes for all 12 tables via API

### Integrations Hub (/integrations)
18 integrations across 8 categories:
- **Delivery**: Uber Eats, DoorDash, Menulog
- **Middleware**: Doshii (connects 20+ apps)
- **Payments**: Stripe (working), Square, CommBank Smart
- **Accounting**: Xero, MYOB, QuickBooks
- **Rostering**: Deputy, Tanda
- **Reservations**: OpenTable, ResDiary
- **In-Venue Ordering**: Mr Yum, HungryHungry
- **Loyalty & Marketing**: Marsello, Stamp Me

Connect/Disconnect/Sync workflows with API key management.

### Stripe Payment Integration
- Real Stripe Checkout via emergentintegrations library
- Creates checkout sessions, redirects to Stripe hosted page
- Payment Success page with status polling
- Payment transactions stored in MongoDB

## Testing Status
- 6 test iterations, all 100% pass rate
- Iteration 6: 21 backend + all frontend tests passing
- No known regressions

## Backlog
- P2: Android APK via Capacitor WebView wrapper (deferred)
- P3: Real API integration for Uber Eats/DoorDash when merchant keys available
