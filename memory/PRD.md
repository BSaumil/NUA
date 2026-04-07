# Ananta POS - Product Requirements Document

## Original Problem Statement
Build the ultimate all-in-one restaurant management platform. No external software needed. Includes POS, OpenTable-like reservations, Guest CRM, Kitchen Display, AI analytics, automation, loyalty, events, forecasting, and mobile deployment.

## Architecture
- **Frontend**: React.js + Tailwind CSS + Shadcn UI + PWA (Service Worker)
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Desktop**: Electron (Windows .exe)
- **Mobile**: Capacitor (Android .apk - structure ready)

## 19 Pages Implemented
1. Dashboard
2. Pre-Shift Brief
3. AI Command Center
4. POS Terminal
5. Reservations
6. Floor Plan
7. Waitlist
8. Kitchen (KDS)
9. Menu Engineering
10. What-If Simulator
11. Products
12. Customers (Guest CRM)
13. Loyalty & Events
14. Inventory
15. Forecasting
16. Automation
17. Accounting
18. BAS/GST
19. Settings

## Features Implemented (All Tested)

### Core POS
- Fast checkout, products, categories, modifiers
- Gift cards, refunds, split bills, tipping
- EFTPOS integration, offline sync, LAN printing

### Reservation & Table Management
- Full CRUD + seat/complete/no-show/auto-assign
- Interactive SVG floor plan, multi-section
- Waitlist with wait-time tracking

### Guest CRM (360°)
- Dining history, dietary restrictions, allergies, preferences
- VIP tagging, segmentation, feedback with star ratings
- Profile tabs: Overview, Reservations, Feedback, Transactions

### Kitchen Display System
- Kanban board (New/Preparing/Ready)
- Rush/VIP priority, course management, auto-refresh

### Intelligence Suite
- Pre-Shift Brief: VIP alerts, dietary alerts, special requests
- AI Command Center: Revenue, food cost %, labor %, AI insights
- Menu Engineering: Star/Puzzle/Workhorse/Dog classification
- What-If Simulator: Price change → profit impact with demand elasticity

### Loyalty & Events
- 4-tier membership (Bronze/Silver/Gold/Platinum) with multipliers
- Rewards system (free items, discounts, experiences)
- Events & Experiences with ticketing

### Forecasting & Optimization
- 7-day demand forecast with busy levels
- Table turn-time optimization
- Smart rostering (AI staff suggestions)

### Automation Engine
- Rule-based triggers (low stock, kitchen backlog, no-show, margin drop)
- Live alerts from real-time data
- Toggle/CRUD rules

### Predictive Customer Matching
- Match orders to likely customers based on order history patterns
- Auto-link orders for loyalty point earning

### PWA
- Service worker for offline caching
- Installable web app manifest

## Key API Endpoints (50+)
Full CRUD for: reservations, floor-plans, waitlist, kitchen/orders, feedback, automation/rules, loyalty/rewards, events
Analytics: pre-shift/today, analytics/command-center, analytics/menu-engineering, analytics/what-if, analytics/demand-forecast, analytics/table-turns, staff/smart-roster
Intelligence: orders/predict-customer, orders/link-customer, menu/qr-data

## Testing
- 4 iterations, all 100% pass rate
- 111+ backend tests passed
- All 19 frontend pages verified working
