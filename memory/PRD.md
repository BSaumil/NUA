# Ananta POS - Product Requirements Document

## Original Problem Statement
Pixel-perfect clone of a Square POS system with comprehensive accounting capabilities, including direct BAS and GST filing. Evolved into a full restaurant management suite with OpenTable-style features, eliminating the need for any 3rd-party restaurant software.

## Core Features
- Fast checkout with multiple payment options (Card, Cash, QR Code, UPI, Split Payments)
- Digital receipts, custom promotions, offline capability
- LAN printer configuration, EFTPOS integration
- Full accounting with BAS/GST filing

## Tech Stack
- Frontend: React.js, Tailwind CSS, Shadcn UI, qrcode.react, PWA
- Backend: FastAPI (Python), Modular Routes Architecture
- Database: MongoDB (AsyncIOMotorClient)

## Architecture (v3.0.0 — Modular)
```
/app/backend/
  server.py          — 77-line orchestrator (imports all route modules)
  database.py         — Shared MongoDB connection
  routes/
    products.py       — Products, Categories, Modifiers
    transactions.py   — Transactions, Promotions, Gift Cards, Refunds
    customers.py      — Customers, CRM Profiles, Feedback
    reservations.py   — Reservations, Floor Plans, Waitlist
    kitchen.py        — Kitchen Display, Prep Management
    analytics.py      — Pre-Shift, Command Center, Menu Engineering, What-If, Forecasting, Roster, Predictive Matching
    automation.py     — Automation Rules & Alerts
    settings.py       — Locations, Users, Printers, Offline, Tables, EFTPOS, Staff
    loyalty.py        — Loyalty Rewards, Events, QR Menu
    public.py         — Public Booking Portal, QR/UPI/Split Payments
```

## Completed Phases
- Phase 1: Reservations, Floor Plan, Waitlist (DONE)
- Phase 2: Guest CRM & 360 Profiles (DONE)
- Phase 3: Kitchen Display System (DONE)
- Phase 4: Pre-Shift Dashboard, AI Command Center, Menu Engineering, Automation Engine (DONE)
- Phase 5: Loyalty, Forecasting, What-If Simulator, QR Menu, PWA (DONE)
- Phase 6: Customer Self-Service Booking Portal, QR/UPI/Split Payments, Backend Refactoring (DONE - April 2026)

## Phase 6 Details
### Customer Self-Service Booking Portal (/booking)
- Public page (no sidebar, no auth)
- 4 tabs: Reserve a Table, Join Waitlist, Events, View Menu
- Responsive mobile layout (wrapping tabs, stacked inputs, 3-col time grid)
- Complete booking flow: date/party/time → details form → confirmation

### Advanced Payment Methods (POS Terminal)
- QR Code Payment: Generates QR using qrcode.react, shows dialog with scannable code
- UPI Payment: Generates UPI deeplink QR, shows merchant UPI ID with copy button
- Split Payment: Equal or Custom mode, 2-10 splits, per-guest name/amount/method, tracks remaining balance, processes partial payments independently

### Backend Refactoring
- Refactored from 2382-line monolith to 77-line orchestrator + 10 route modules
- Zero regression — all 19+ endpoint groups verified working

## Testing Status
- 5 test iterations, all 100% pass rate
- 32 tests in iteration 5 (19 backend + 13 frontend)
- No known regressions

## Backlog
- P2: Android APK via Capacitor WebView wrapper (deferred)
