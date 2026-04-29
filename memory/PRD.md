# NUVA POS — Product Requirements Document

## Original Problem Statement
Enterprise-grade all-in-one hospitality POS platform with AI-powered features, gamification, comprehensive staff management, category-wise printer routing, and advanced analytics.

## Tech Stack
- Frontend: React.js, Tailwind CSS, Shadcn UI, PWA
- Backend: FastAPI (Python), 21 modular route files
- Database: MongoDB (AsyncIOMotorClient)
- Payments: Stripe (emergentintegrations)
- AI: GPT 5.2 (emergentintegrations) — Menu Import, Pantry, EOD Insights, Quarterly Alternatives
- Auth: JWT + bcrypt + PIN login, 26 granular permissions
- Desktop: Electron (.exe) | Mobile: Capacitor (APK)

## Architecture (v8.0.0 — 21 route files)
```
/app/backend/routes/
  auth.py, products.py, transactions.py, customers.py, reservations.py, kitchen.py,
  analytics.py, automation.py, settings.py, loyalty.py, public.py, table_ordering.py,
  integrations.py, ai_pantry.py, members.py, multi_tenant.py, advanced_features.py,
  staff_management.py, menu_features.py, enterprise_features.py, gamification.py
```

## Key Features (Cumulative)

### POS Terminal
- Product grid, categories, search, cart
- Payment: Card, Cash (denominations + change), QR, UPI, Stripe, Split
- Auto surcharging (weekend + public holiday)
- Training Mode, Ghost Discount/Void
- Smart kiosk upsells, auto print routing on checkout

### Staff & Gamification
- PIN Login (2-4 digit) + Email/Password
- **Staff Leaderboard** — Performance score (sales/txns/tips/efficiency), podium top 3
- **Smart Tip Distribution** — weighted by hours worked + performance (not equal split)
- Timecards, Roster, Payrun (auto-logs to Accounting)
- Staff Reports (weekly/monthly/quarterly/yearly)
- 26 Granular Permissions (owner assigns per staff)

### Category-wise Print Routing
- 8 default routes: Beverages/Alcohol→Bar Printer, Pizza→Pizza Station, Food/Mains/etc→Kitchen
- Priority levels (P1=Rush, P2=Normal, P3=Low)
- Orders auto-route to correct printers on POS checkout
- Live print queue with Done/Complete buttons
- Configurable by owner/manager

### Quarterly Menu Review
- Top sellers / Worst sellers / Low-margin underperformers
- **AI Alternative Suggestions** (GPT-5.2) for underperforming items
- Replacement recommendations with pricing and reasoning

### Menu Engineering & Products
- AI Menu Import (PDF/JPEG → auto-create products)
- Bulk Price Adjustment (category, percentage/fixed, inflation)
- Products: locations, online channels, SEO description
- Promotions: date range, day selection, time window

### Analytics & Reporting
- Live Sales Dashboard, EOD Reports (6 periods + AI insights)
- Automated Reporting config (itemised/category/detailed)
- Profit-Cost Reporting, Menu Engineering Matrix
- What-If Simulator with manual quantity projection

### Other
- 18+ Integrations, Reservations, KDS, Floor Plans, Booking Portal, Member Portal, QR Ordering, Multi-tenant, Email Marketing, Tip Management, Hardware Integrations

## Auth Credentials
- Owner: owner@nuva.com / NuvaOwner2026!
- Manager: manager@nuva.com / Staff2026!
- Cashier: cashier@nuva.com / Staff2026!
- Kitchen: kitchen@nuva.com / Staff2026!

## Testing: 13 iterations, all pass (32 backend tests in latest)

## Backlog
- P1: SendGrid integration (user provides key later)
- P2: Autonomous nightly EOD cron job
- P3: Real delivery API integrations
