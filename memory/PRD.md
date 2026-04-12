# Ananta POS - Product Requirements Document

## Original Problem Statement
Full-featured Square POS clone with comprehensive restaurant management, evolved into an all-in-one hospitality platform eliminating 3rd-party dependencies. Now includes EatClub-style member marketing, AI-powered supply chain, staff RBAC, and multi-business support.

## Tech Stack
- Frontend: React.js, Tailwind CSS, Shadcn UI, qrcode.react, PWA
- Backend: FastAPI (Python), 16 modular route files
- Database: MongoDB (AsyncIOMotorClient)
- Payments: Stripe (emergentintegrations)
- AI: GPT 5.2 (emergentintegrations)
- Auth: JWT + bcrypt, role-based access control

## Architecture (v4.0.0)
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
```

## Completed Phases
- Phase 1-5: Core POS, Reservations, CRM, KDS, Analytics, Loyalty, PWA
- Phase 6: Booking Portal, QR/UPI/Split Payments, Backend Refactoring
- Phase 7: Table-Side QR Ordering, 18 Integrations Hub, Stripe
- Phase 8 (Current): Staff Auth & RBAC, AI Smart Pantry, Member Portal, Multi-Business

## Phase 8 Details

### Staff Auth & RBAC
- JWT auth with httpOnly cookies + Bearer tokens
- 4 roles: Owner (full access), Manager (no pay rates), Cashier (POS only), Kitchen (KDS only)
- Brute force protection (5 attempts, 15min lockout)
- Staff management (add/edit/delete)
- Owner-only financial reports (Revenue, COGS, Roster Cost, P&L)
- Sidebar dynamically filters based on role

### AI Smart Pantry
- GPT 5.2 analyzes menu descriptions, sales data, and reservations
- Generates weekly ordering list with quantities and costs
- Wastage insights and recommendations
- History of previous generations
- Owner/Manager access only

### EatClub-Style Member Portal (/join)
- Public signup with welcome bonus (50 points + 15% voucher)
- Member login and dashboard
- Voucher system (percentage/fixed/free item)
- Referral codes with social sharing (WhatsApp, Facebook, Twitter)
- Tier system (Bronze/Silver/Gold/Platinum)

### Multi-Business
- Create and manage multiple businesses
- Per-business data export
- Business summary stats
- Owner-only access

## Auth Credentials
- Owner: owner@ananta.com / AnantaOwner2026!
- Manager: manager@ananta.com / Staff2026!
- Cashier: cashier@ananta.com / Staff2026!
- Kitchen: kitchen@ananta.com / Staff2026!

## Testing: 7 iterations, all 100% pass

## Backlog
- P2: Android APK via Capacitor
- P3: Email marketing campaign builder
- P3: Real API integrations for Uber Eats/DoorDash when keys available
