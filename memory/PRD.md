# NUVA POS — Product Requirements Document

## Original Problem Statement
Full-featured Square POS clone evolved into an enterprise-grade all-in-one hospitality platform with AI-powered features, comprehensive staff management, granular permissions, and advanced POS capabilities.

## Tech Stack
- Frontend: React.js, Tailwind CSS, Shadcn UI, qrcode.react, PWA
- Backend: FastAPI (Python), 20 modular route files
- Database: MongoDB (AsyncIOMotorClient)
- Payments: Stripe (emergentintegrations)
- AI: GPT 5.2 (emergentintegrations) — Menu Import, Pantry, EOD Insights
- Auth: JWT + bcrypt + PIN login, granular permission RBAC
- Desktop: Electron (Windows .exe) | Mobile: Capacitor (Android APK)

## Completed Features (v7.0.0)

### Core POS
- Product grid with search, categories, cart
- Payment: Card, Cash (denominations), QR, UPI, Stripe, Split
- Cash flow: Exact/Round/$5-$100/Custom + change display
- Training Mode, Ghost Discount/Void (owner secret)
- Auto surcharging (weekend + public holiday)
- Smart kiosk upsells (AI-powered)

### Products & Menu
- Full CRUD with locations, online channels, SEO description
- Online channels: Website, Uber Eats, DoorDash, Menulog, Deliveroo, Google Food
- AI Menu Import (PDF/JPEG → auto-create products)
- Bulk Price Adjustment (category, percentage/fixed, inflation)
- Enhanced Promotions (date range, day selection, time window)

### Staff Management
- PIN Login (2-4 digit) + Email/Password
- Timecards (Clock In/Out with break tracking)
- Staff Roster scheduling
- Payrun (gross, super 11.5%, tax, net → auto-logs to Accounting)
- Staff Reports (weekly/monthly/quarterly/yearly)
- 26 Granular Permissions (owner assigns per staff member)

### Analytics & Reporting
- Live Sales Dashboard (real-time)
- End-of-Day Reports (6 periods, 6 sections incl. AI insights)
- Automated Reporting config (daily/weekly/monthly, itemised/category/detailed)
- Profit-Cost Reporting
- Menu Engineering (Stars/Puzzles/Workhorses/Dogs)
- What-If Simulator (manual quantity projections)

### Settings
- Theme, Receipt (logo/QR toggles), Permissions, Surcharges, Hardware, Training Mode, Locations, Staff, Business

### Hardware
- Any printer integration (USB/Network/Bluetooth)
- Any scanner integration (Barcode/QR)

### Other
- 18+ Integrations Hub, Reservations, Floor Plans, KDS, Booking Portal, Member Portal, Table-Side QR Ordering, Multi-tenant, Email Marketing, Tip Management

## Auth Credentials
- Owner: owner@nuva.com / NuvaOwner2026!
- Manager: manager@nuva.com / Staff2026!
- Cashier: cashier@nuva.com / Staff2026!
- Kitchen: kitchen@nuva.com / Staff2026!

## Testing: 12 iterations, all pass

## Backlog
- P1: SendGrid integration for real email delivery (user will provide key later)
- P2: Autonomous nightly EOD cron job
- P3: Real Uber Eats/DoorDash API integrations
