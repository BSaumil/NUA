# NUVA POS — PRD v11.0

## Architecture: 22 backend routes, React + FastAPI + MongoDB + GPT-5.2

## Sidebar (Grouped Dropdowns)
- Dashboard (owner/manager) | Pre-Shift | Command Center | POS Terminal
- **Reservations** > Bookings, Floor Plan, Waitlist, Table Layout, Settings & Rules, Experience, Clubmember, **Analytics**
- Kitchen
- **Menu Engineering** > Menu Matrix, What-If, Products, Inventory, AI Smart Pantry, Forecasting, Quarterly Review
- **Team** > Staff, Roster & Payrun, Leaderboard, Tip Management
- **Customers** > Customer List, Loyalty & Events, Email Marketing
- Automation
- **Accounting** > Transactions, BAS/GST, End of Day, Integrations
- Settings (Theme, Receipt, Print Routing, Permissions, Surcharges, Hardware, Training, Locations, Staff, Business+Google Sync)

## Key Updates (v11)
- **Booking Analytics** — No-show rates, avg party size by shift, peak booking days, covers breakdown
- **Clubmember Social Integration** — Connect Instagram/Facebook/TikTok/Twitter/Google accounts for auto-posting offers
- **Editable Loyalty Tiers** — Owner can edit name, minPoints, multiplier, perks for Bronze/Silver/Gold/Platinum
- **Editable Rewards** — Full CRUD with start/end date+time
- **Editable Events** — Full CRUD with edit button on each event card
- **Email Testing** — All test emails go to sambhatt7@gmail.com, configurable by owner
- **Staff Sidebar Fixed** — Login response now includes permissions, cashier properly restricted

## Credentials
Owner: owner@nuva.com / NuvaOwner2026! | Manager: manager@nuva.com / Staff2026! | Cashier: cashier@nuva.com / Staff2026!

## Testing: 16 iterations, all pass (30 backend tests in latest)

## Backlog
- P1: SendGrid real email delivery (user provides key later)
- P2: Autonomous nightly EOD cron
- P3: Real delivery platform APIs
