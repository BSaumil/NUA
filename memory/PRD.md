# NUA POS — PRD v16.0

## Brand
NUA. POS-first UX. Bottom-dock primary nav. Sidebar deprecated.

## v16 (Feb 2026) — Phase A + C + D Mega-Drop
**Backend**: New consolidated routes file `routes/v15_features.py` adds:
- `GET /api/dock/badges` — live counters (reservations/kitchen/pos/waitlist)
- `GET/POST/DELETE /api/pos/tabs` — Hold/Recall orders
- `GET/POST /api/pos/favorites` — per-user quick keys
- `PUT /api/products/{id}/variants` — variant matrix
- `POST /api/items/bulk-import` — CSV import
- `POST /api/pos/voice-order` — Whisper transcription + product matching
- `POST /api/ai/ask-nua` — natural-language analytics (GPT-5.2)
- `POST /api/items/generate-image` — Nano Banana marketing photos
- `GET /api/analytics/inventory-anomalies` — sales velocity spike detection
- `POST /api/staff/auto-roster` + `POST /api/staff/roster/commit-auto` — AI roster
- `GET/POST /api/staff/shift-swaps` + approve/reject
- `GET /api/analytics/booking-heatmap` — DOW × hour guest density
- `GET /api/analytics/cohort-retention` — month-over-month return rate
- `GET /api/audit/logs` — aggregated sensitive events
- `POST /api/auth/2fa/{setup,verify,disable}` — TOTP scaffold
- `GET /api/customers/{id}/gdpr-export` + DELETE for anonymize
- `POST /api/bas-gst/efile/{report_id}` — ATO submission record
- `GET /api/i18n/labels/{lang}` — 5-lang cart labels (en/es/fr/hi/zh)
- **Rate limit middleware**: 120 req/min per (X-Tenant-Id, IP)

**Frontend**: New components + pages:
- `components/AskNua.jsx` — chat panel + global FAB
- `components/VoiceOrderButton.jsx` — Whisper mic in POS header
- `pages/AuditLog.jsx` — sensitive events viewer
- `pages/InventoryAnomalies.jsx` — AI spike detector
- `pages/BookingHeatmap.jsx` — busy times visualization
- `pages/CohortRetention.jsx` — retention heatmap
- `pages/ShiftSwaps.jsx` — staff swap requests
- `pages/SecurityCompliance.jsx` — 2FA, dark mode, locale, GDPR
- POSTerminal additions: Voice button, Hold/Recall Tabs, Loyalty preview chip, BNPL + Crypto pay buttons, multi-lang labels
- StaffRoster: AI Auto-Roster button
- Products: CSV import button
- BottomDock: live badges polled every 30s; new splash tiles
- ThemeContext: dark mode + language state
- PWA: `manifest.json` + `service-worker.js` for offline-shell

## Credentials
Owner: owner@nuva.com / NuvaOwner2026!  
Manager: manager@nuva.com / Staff2026!  
Cashier: cashier@nuva.com / Staff2026!  
Kitchen: kitchen@nuva.com / Staff2026!  
2FA demo code: `123456`

## Testing
v16 backend curl-verified: badges, tabs, audit, Ask NUA (real GPT-5.2 reply), heatmap, i18n.  
Frontend smoke-tested: POS, voice btn, Hold/Recall, Ask NUA FAB, BottomDock, all 6 new splash tiles render.

## Pending (Phase B — requires user API keys)
WhatsApp Business · Twilio SMS · Stripe Tap-to-Pay iOS · Stripe Crypto · Xero/QB · Uber Eats/DoorDash · Google Reserve · TikTok Shop.

## Backlog
- POSTerminal.jsx 800+ lines — split into sub-files (mechanical refactor)
- WebSocket real-time orders (currently 30s polling)
- Multi-region Atlas deployment notes
- Full TOTP via pyotp (currently demo-accepts `123456`)
