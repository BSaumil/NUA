# Ananta POS - Product Requirements Document

## Original Problem Statement
Build a pixel-perfect clone of a Square POS system with comprehensive accounting capabilities, including direct BAS and GST filing. Core features include fast checkout, multiple payment options, split bills, tipping, digital receipts, custom promotions, offline capability, LAN printer configuration, and EFTPOS integration. Subsequently, the user requested OpenTable-like reservation/booking features and a complete restaurant management system requiring NO external software for any cafe or restaurant business. Also requested Windows .exe and Android .apk builds.

## User Personas
- **Restaurant Owner/Manager**: Manages all operations, reservations, staff, accounting
- **Host/Front-of-House**: Manages reservations, waitlist, table assignments, seating
- **Kitchen Staff**: Views and manages kitchen orders via KDS
- **Servers**: Takes orders, processes payments via POS terminal
- **Accountant**: Manages BAS/GST filing, P&L, expenses

## Core Architecture
- **Frontend**: React.js + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (AsyncIOMotorClient)
- **Desktop**: Electron wrapper for Windows .exe
- **Mobile**: Capacitor (planned) for Android .apk

## What's Been Implemented

### Phase 0 - Core POS (Complete)
- Dashboard with sales stats
- POS Terminal with fast checkout
- Products management with categories, modifiers
- Customer directory
- Inventory management
- Accounting (P&L, summary)
- BAS/GST reporting and filing
- Settings (themes, printers)
- Gift cards, refunds, suppliers, expenses
- Staff shifts and commissions
- EFTPOS integration (Linkly, Tyro, Smartpay, Windcave)
- Offline sync support
- LAN printer configuration
- Electron wrapper + Windows build scripts/guides

### Phase 1 - Reservation & Table Management (Complete - Feb 2026)
- **Reservations System**: Full CRUD, seat/complete/no-show/auto-assign, date navigation, status filtering, search, list and timeline views
- **Interactive Floor Plan**: SVG canvas, drag-drop tables, multiple shapes (rect/circle/square), sections with colors, view/edit modes, multi-floor support
- **Waitlist Management**: Walk-in queue, estimated wait times with progress bars, notify/seat/remove actions, seating preferences

### Phase 2 - Guest CRM & 360° Profiles (Complete - Feb 2026)
- **360° Guest Profiles**: Dining history, spending stats, avg spend/visit, seating preferences, favorite dishes, birthday, company
- **Dietary & Allergies**: Clickable badge selection for dietary restrictions and allergies
- **Guest Tags & Segmentation**: Auto-tags (VIP, Regular, High Spender, Corporate, Birthday Month, etc.)
- **Feedback System**: Star ratings (overall, food, service, ambience), comments, response management
- **Profile Tabs**: Overview, Reservations, Feedback, Transactions

### Phase 3 - Kitchen Display System (Complete - Feb 2026)
- **Kanban Board**: Three columns (New → Preparing → Ready to Serve)
- **Order Management**: Start, Ready, Served, Cancel actions
- **Priority System**: Rush (red pulsing) and VIP (amber highlight) indicators
- **Course Management**: Fire courses in sequence (Fire C2, C3...)
- **Auto-Refresh**: 10-second polling for real-time updates
- **New Order Creation**: Product selection, table assignment, notes, priority

## Prioritized Backlog

### P0 - Next Up
- **Capacitor Android APK**: WebView wrapper for Android deployment
- **PWA**: Service worker + manifest for installable web app

### P1 - Marketing & Communications
- Automated reservation confirmations (in-app notifications)
- Direct messaging (staff-to-guest)
- Email campaign builder with templates and segments
- Loyalty/Membership program with tiers and rewards
- Events & Experiences listing with ticketing

### P2 - Advanced Analytics & Revenue
- Pre-shift reports (today's reservations, VIP alerts, special requests)
- Table turn-time optimization
- Revenue per guest/table/daypart metrics
- Demand forecasting / predictive analytics
- Multi-location sync and cross-venue guest recognition

### P3 - Future Enhancements
- Online ordering page (customer self-service)
- SMS/Email reservation confirmations
- QR code menu generator
- Customer-facing display
- Responsive mobile/tablet UI optimization

## Key API Endpoints
- `/api/reservations` - Full CRUD + seat/complete/no-show/auto-assign
- `/api/floor-plans` - CRUD + table status + section assignment
- `/api/waitlist` - CRUD + seat/notify
- `/api/customers/{id}/profile` - 360° guest profile
- `/api/feedback` - CRUD + respond
- `/api/kitchen/orders` - CRUD + start/ready/served/cancel/priority/fire-course
- `/api/products`, `/api/transactions`, `/api/accounting/*`, `/api/bas-gst/*`

## Key Database Collections
- `reservations`, `floor_plans`, `waitlist`, `feedback`, `kitchen_orders`
- `customers`, `products`, `transactions`, `categories`, `modifiers`
- `promotions`, `gift_cards`, `refunds`, `suppliers`, `expenses`
- `staff_shifts`, `eftpos_terminals`, `eftpos_transactions`, `printers`

## Testing Status
- All features tested via automated testing agent
- Backend: 100% pass rate (50/50 tests across 2 iterations)
- Frontend: 100% working (all pages, CRUD, navigation)
- Test files: `/app/test_reports/iteration_1.json`, `/app/test_reports/iteration_2.json`
