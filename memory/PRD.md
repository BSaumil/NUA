# NUVA POS — Product Requirements Document

## Original Problem Statement
Full-featured Square POS clone with comprehensive restaurant management, evolved into an all-in-one hospitality platform. Includes EatClub-style member marketing, AI-powered supply chain, staff RBAC, multi-business support, table-side QR ordering, integrations hub, email marketing, tip management, training mode, and end-of-day reports.

## Tech Stack
- Frontend: React.js, Tailwind CSS, Shadcn UI, qrcode.react, PWA
- Backend: FastAPI (Python), 16 modular route files
- Database: MongoDB (AsyncIOMotorClient)
- Payments: Stripe (emergentintegrations)
- AI: GPT 5.2 (emergentintegrations)
- Auth: JWT + bcrypt, role-based access control
- Desktop: Electron (Windows .exe)
- Mobile: Capacitor (Android APK)

## Architecture (v5.0.0)
```
/app/backend/routes/
  auth.py             — JWT auth, RBAC, staff management, owner reports, seeding
  products.py         — Products, Categories, Modifiers
  transactions.py     — Transactions, Promotions, Gift Cards, Refunds
  customers.py        — Customers, CRM, Feedback
  reservations.py     — Reservations, Floor Plans, Waitlist
  kitchen.py          — Kitchen Display, Prep Management
  analytics.py        — Pre-Shift, Command Center, Menu Engineering, Forecasting, Roster
  automation.py       — Automation Rules & Alerts
  settings.py         — Locations, Users, Printers, Offline, EFTPOS, Staff
  loyalty.py          — Loyalty Rewards, Events, QR Menu
  public.py           — Booking Portal, QR/UPI/Split Payments
  table_ordering.py   — Table-Side QR Ordering
  integrations.py     — 18 Integrations Hub + Stripe Checkout
  ai_pantry.py        — AI Smart Pantry (GPT 5.2)
  members.py          — EatClub-style Member Portal, Vouchers, Social Sharing
  multi_tenant.py     — Multi-Business Management
  advanced_features.py — Tips, Training Mode, EOD Reports, Email Marketing
```

## Completed Phases
- Phase 1-5: Core POS, Reservations, CRM, KDS, Analytics, Loyalty, PWA
- Phase 6: Booking Portal, QR/UPI/Split Payments, Backend Refactoring
- Phase 7: Table-Side QR Ordering, 18 Integrations Hub, Stripe
- Phase 8: Staff Auth & RBAC, AI Smart Pantry, Member Portal, Multi-Business
- Phase 9 (Current): Email Marketing, Tip Management, Training Mode, EOD Reports, APK/EXE Builds

## Phase 9 Details (Endgame Features)

### Email Marketing
- Campaign CRUD (create/list/send/delete)
- Target by membership tier (Bronze/Silver/Gold/Platinum) or all members
- Track recipient count, sent status, open count
- Email sending MOCKED (would use SendGrid in production)

### Tip Management (Toast-style)
- Record tips (card/cash/digital) per staff member
- Tip pooling option for shared tips
- Pool distribution: divides equally among active staff
- Summary dashboard with per-staff breakdown
- Owner-only access for summary and distribution

### Training Mode (Clover-style)
- Toggle in Settings > Training Mode tab
- When enabled, POS transactions are simulated (no real charges)
- Amber banner on POS Terminal warns staff
- Owner/Manager can toggle

### End-of-Day Reports (Square-style)
- Gross Sales, Net Sales, Avg Ticket, GST
- Breakdown by payment method
- Top selling items with qty and revenue
- Tips summary integrated
- Refunds & adjustments section

### Desktop & Mobile Builds
- Android APK via Capacitor 6 (build-android.sh)
- Windows .exe via Electron + electron-builder (build-windows.bat)
- Build guide at frontend/BUILD_GUIDE.md

## Auth Credentials
- Owner: owner@nuva.com / NuvaOwner2026!
- Manager: manager@nuva.com / Staff2026!
- Cashier: cashier@nuva.com / Staff2026!
- Kitchen: kitchen@nuva.com / Staff2026!

## Testing: 8 iterations, all 100% pass

## Backlog
- P3: Real email sending via SendGrid/SES integration
- P3: Real API integrations for Uber Eats/DoorDash when keys available
