# Ananta POS - Product Requirements Document

## Original Problem Statement
Build a pixel-perfect clone of a Square POS system with comprehensive accounting capabilities, including direct BAS and GST filing. Extended to include ALL OpenTable Pro/Advanced features, SevenRooms CRM, and full restaurant management intelligence. The goal: NO external software needed for any cafe or restaurant business. Also requires Windows .exe and Android .apk builds.

## Core Architecture
- **Frontend**: React.js + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (AsyncIOMotorClient)
- **Desktop**: Electron wrapper for Windows .exe
- **Mobile**: Capacitor (planned) for Android .apk

## What's Been Implemented

### Core POS (Complete - Previous Sessions)
- Dashboard, POS Terminal, Products, Categories, Modifiers
- Customer directory, Inventory, Suppliers, Expenses
- Accounting (P&L), BAS/GST reporting
- Gift cards, Refunds, Staff shifts/commissions
- EFTPOS integration, Offline sync, LAN printer
- Electron wrapper + Windows build scripts

### Phase 1 - Reservation & Table Management (Complete - Feb 2026)
- Reservations CRUD + seat/complete/no-show/auto-assign
- Interactive SVG Floor Plan with drag-drop tables, multi-section
- Waitlist Management with walk-in queue & wait times

### Phase 2 - Guest CRM & 360° Profiles (Complete - Feb 2026)
- 360° Guest Profiles with dining history, preferences, allergies
- Guest Tags & Segmentation (VIP, Corporate, Birthday Month, etc.)
- Feedback System with star ratings + response management

### Phase 3 - Kitchen Display System (Complete - Feb 2026)
- Kanban Board (New → Preparing → Ready to Serve)
- Priority System (Rush/VIP), Course Management
- Auto-Refresh, New Order Creation

### Phase 4 - Intelligence & Automation (Complete - Feb 2026)
- **Pre-Shift Dashboard**: VIP arrivals, dietary alerts, special requests, service timeline
- **AI Command Center**: Revenue/cost/profit metrics, food cost %, labor %, AI insights
- **Menu Engineering**: Star/Puzzle/Workhorse/Dog classification, category P&L
- **Automation Engine**: Rule-based triggers, live alerts, toggle on/off

## Pages (16 total)
1. Dashboard
2. Pre-Shift Brief
3. AI Command Center
4. POS Terminal
5. Reservations
6. Floor Plan
7. Waitlist
8. Kitchen (KDS)
9. Menu Engineering
10. Products
11. Customers (Guest CRM)
12. Inventory
13. Automation
14. Accounting
15. BAS/GST
16. Settings

## Key API Endpoints
- `/api/pre-shift/today` - Pre-shift briefing data
- `/api/analytics/command-center` - AI Command Center metrics
- `/api/analytics/menu-engineering` - Menu performance analysis
- `/api/automation/rules` - CRUD + toggle automation rules
- `/api/automation/alerts` - Real-time alerts
- `/api/kitchen/prep-list` - Dynamic prep list
- `/api/reservations` - Full CRUD + seat/complete/no-show/auto-assign
- `/api/floor-plans` - CRUD + table status + section assignment
- `/api/waitlist` - CRUD + seat/notify
- `/api/customers/{id}/profile` - 360° guest profile
- `/api/feedback` - CRUD + respond
- `/api/kitchen/orders` - CRUD + start/ready/served/cancel/priority/fire-course

## Prioritized Backlog

### P0 - Mobile Deployment
- Capacitor Android APK (WebView wrapper)
- PWA (Progressive Web App)

### P1 - Communications & Loyalty
- Automated reservation confirmations
- Direct messaging (staff-to-guest)
- Email campaign builder
- Loyalty/Membership tiers
- Events & Experiences with ticketing

### P2 - Enhanced Intelligence
- Predictive analytics (weather, events, seasonality)
- Table turn-time optimization
- Revenue per guest/table/daypart
- Cash flow prediction
- Demand forecasting
- Smart rostering (auto roster builder based on demand)

### P3 - Integration Layer
- Unified order dashboard (dine-in + delivery)
- Order throttling
- Multi-location sync
- QR code menu generator
- Online ordering page
- Customer-facing display

## Testing Status
- 3 test iterations, all 100% pass rate
- Backend: 69/69 total tests passed
- Frontend: All 16 pages working
- Test files: iteration_1.json, iteration_2.json, iteration_3.json
