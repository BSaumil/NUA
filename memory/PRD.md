# NUVA POS — PRD v10.0

## Architecture: 22 backend route files, React + FastAPI + MongoDB

## Sidebar (Grouped Dropdowns)
- Dashboard (owner/manager only) | Pre-Shift | Command Center | POS Terminal
- **Reservations** > Bookings, Floor Plan, Waitlist, Table Layout & Combinations, Settings & Rules, Schedule, Experience, Clubmember
- Kitchen
- **Menu Engineering** > Menu Matrix, What-If, Products, Inventory, AI Smart Pantry, Forecasting, Quarterly Review
- **Team** > Staff, Roster & Payrun, Leaderboard, Tip Management
- **Customers** > Customer List, Loyalty & Events, Email Marketing
- Automation
- **Accounting** > Transactions, BAS/GST, End of Day, Integrations
- Settings (Theme, Receipt, Print Routing, Permissions, Surcharges, Hardware, Training, Locations, Staff, Business Hours + Google Sync)

## Staff Access Rules
- Cashier/Kitchen → land on POS (not Dashboard)
- Staff cannot see Dashboard, revenue, or financial data
- Owner controls granular permissions (26 items)

## Credentials
Owner: owner@nuva.com / NuvaOwner2026! | Manager: manager@nuva.com / Staff2026! | Cashier: cashier@nuva.com / Staff2026!

## Testing: 15 iterations, all pass
## Backlog: P1 SendGrid | P2 Nightly EOD cron | P3 Delivery APIs
