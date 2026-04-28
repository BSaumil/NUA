# NUVA POS — Product Requirements Document

## Original Problem Statement
Full-featured Square POS clone evolved into an all-in-one hospitality platform with AI-powered features, comprehensive staff management, and advanced POS capabilities.

## Tech Stack
- Frontend: React.js, Tailwind CSS, Shadcn UI, qrcode.react, PWA
- Backend: FastAPI (Python), 18 modular route files
- Database: MongoDB (AsyncIOMotorClient)
- Payments: Stripe (emergentintegrations)
- AI: GPT 5.2 (emergentintegrations) — Menu Import, Pantry, EOD Insights
- Auth: JWT + bcrypt + PIN login, role-based access control
- Desktop: Electron (Windows .exe)
- Mobile: Capacitor (Android APK)

## Architecture (v6.0.0)
```
/app/backend/routes/
  auth.py              — JWT auth, RBAC, staff CRUD, PIN management
  products.py          — Products CRUD, Stock Adjustment
  transactions.py      — Transactions detail/refunds, Promotions CRUD (date range/day/time)
  customers.py         — Customers, CRM, Feedback
  reservations.py      — Reservations, Floor Plans, Waitlist
  kitchen.py           — Kitchen Display, Prep
  analytics.py         — Pre-Shift, Command Center, Menu Engineering, Forecasting, Roster
  automation.py        — Automation Rules & Alerts
  settings.py          — Locations CRUD, Printers, EFTPOS, Staff legacy
  loyalty.py           — Loyalty, Events, QR Menu
  public.py            — Booking Portal, Payments
  table_ordering.py    — Table-Side QR Ordering
  integrations.py      — 18 Integrations Hub + Stripe
  ai_pantry.py         — AI Smart Pantry (GPT 5.2)
  members.py           — Member Portal, Vouchers, Social
  multi_tenant.py      — Multi-Business
  advanced_features.py — Tips, Training Mode, EOD Reports (comprehensive), Email Marketing, AI Insights, Business Settings
  staff_management.py  — PIN Login, Timecards (Clock In/Out), Roster, Payrun, Staff Reports, Receipt Settings
  menu_features.py     — AI Menu Import, Bulk Price Adjust, Ghost Discount/Void, What-If Advanced
```

## Key Features Implemented

### POS Terminal
- Full cart with product grid, categories, search
- Payment methods: Card, Cash (with denominations), QR, UPI, Stripe, Split
- Cash flow: Exact, Round Up, $5/$10/$20/$50/$100, Custom + change display
- Training Mode (simulated transactions)
- Ghost Discount/Void (owner secret, hidden from all reports)

### Staff Management
- PIN Login (2-4 digit, assigned by owner)
- Email/Password login
- Timecards (Clock In/Out with break tracking)
- Staff Roster scheduling
- Payrun calculation (gross, super 11.5%, tax, net)
- Payrun processing (auto-logs to Accounting/BAS)
- Staff Reports (weekly/monthly/quarterly/yearly)

### Menu Engineering
- AI Menu Import (PDF/JPEG → AI extracts items → creates products)
- Bulk Price Adjustment (by category, percentage or fixed, increase/decrease)
- Performance Matrix (Stars, Puzzles, Workhorses, Dogs classification)

### Promotions (Enhanced)
- Date range selection (start/end)
- Day-of-week selection (Mon-Sun, select specific days)
- Time window (start time / end time)
- Full 365-day scheduling

### Accounting & Transactions
- Transaction detail with items, receipt, refunds
- Receipt preview with Print/Email
- Refund processing (original payment/store credit/cash)
- Connected to Payrun expenses

### End-of-Day Reports
- Period: Today/Yesterday/Week/Month/Quarter/Custom
- Sections: Overview, Item Sales, Categories, Customers, Hourly, AI Insights
- AI-powered insights via GPT-5.2
- Customer analytics: covers, walk-ins, new vs returning, top spenders

### Receipt Customization
- Business logo URL
- Payment QR code (toggle on/off)
- Social Media QR code (toggle on/off)
- Promotion QR code (toggle on/off)
- Each element independently selectable

### What-If Simulator
- Manual quantity projection (Qty/Month input)
- Revenue and profit forecasting
- Multi-product simulation

## Auth Credentials
- Owner: owner@nuva.com / NuvaOwner2026!
- Manager: manager@nuva.com / Staff2026!
- Cashier: cashier@nuva.com / Staff2026!
- Kitchen: kitchen@nuva.com / Staff2026!
- PIN: Set by owner in Settings > Staff tab

## Testing: 11 iterations, all pass (28+ backend tests in latest)

## Backlog
- P2: Autonomous nightly EOD email to owner
- P3: Real email delivery via SendGrid/SES
- P3: Real Uber Eats/DoorDash API integrations
