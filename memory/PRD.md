# NUA POS — PRD v18.0 (Phase E + F)

## v18 (Feb 2026) — Iteration 24

### Backend (`routes/phase_ef.py`)
- `GET/PUT /api/agent/autonomy` — owner toggles for auto-publish-roster, auto-confirm-SMS, A/B testing, VIP thresholds, reorder threshold
- `GET /api/comms/sms-queue` · `POST /api/comms/auto-confirm/{resId}` — auto SMS confirmation queue
- `POST /api/agent/voice-extended` — extended voice intents: void_last_item · price_change · eighty_six
- `POST /api/agent/auto-publish-roster` — generates + commits AI weekly shifts within budget cap
- `GET /api/phone-agent/calls` · `POST /api/phone-agent/simulate` — AI Phone Agent (GPT-5.2 classifier, auto-creates reservation, queues confirmation SMS)
- `GET /api/purchase-orders` · `POST /api/purchase-orders/generate` · `POST /api/purchase-orders/{id}/{approve,send,receive,cancel}` — auto-PO generation, receive auto-increments stock
- `GET/POST /api/ab-tests` · `POST /api/ab-tests/{id}/{exposure,conversion,conclude}` — live menu A/B testing with winner auto-pick
- `GET /api/customers/{id}/your-usual` — top-3 frequent items from last-20 transactions
- `POST /api/agent/tick-extended` — runs auto-VIP + auto-SMS + auto-PO rules in one shot

### Frontend
- `pages/PhoneAgent.jsx` (`/phone-agent`) — call log + simulate inbound call
- `pages/PurchaseOrders.jsx` (`/purchase-orders`) — supplier-grouped POs with workflow buttons
- `pages/MenuABTesting.jsx` (`/ab-tests`) — variant pair creator, exposure/conversion table, winner trophy
- `pages/AgentAutonomy.jsx` (`/agent-autonomy`) — owner toggle panel + threshold inputs + "Run Extended Tick"
- POSTerminal: **Your Usual** strip when known customer selected
- VoiceOrderButton now hands off transcript to `voice-extended` for void/price/86 commands
- BottomDock splash: 4 new tiles added under Analytics & AI group

## Curl-verified
- Voice "raise espresso by 50 cents" → $5.70 → $6.20 ✅
- Voice "drop latte by 1 dollar" → Product not found (handled gracefully) ✅
- Phone agent "book for 4 Saturday 7pm" → reservation auto-created + SMS queued ✅
- Auto-PO: seeded 3 low-stock products with supplier "Acme Wholesale" → 1 PO created ✅
- Auto-VIP: Sarah Johnson with spend=1500, visits=25 → tier auto-promoted from Gold to VIP ✅
- Your Usual: customer with 2 past orders → 2 most-frequent items returned ✅

## Frontend Playwright-verified
- `/phone-agent`, `/purchase-orders`, `/ab-tests`, `/agent-autonomy` all render ✅
- `/pos` with Sarah Johnson selected → Your Usual block visible ✅

## Credentials
Owner: owner@nuva.com / NuvaOwner2026!  
Manager: manager@nuva.com / Staff2026!  
Cashier: cashier@nuva.com / Staff2026!  
Kitchen: kitchen@nuva.com / Staff2026!  
2FA demo: 123456

## Backlog
- Phase B (user keys): WhatsApp · Twilio Voice/SMS · Stripe Tap-to-Pay · Crypto USDC · Xero/QB · Uber Eats · DoorDash · Google Reserve · TikTok Shop
- Phase E next wave: auto-upsell in cart · auto-price-tune · auto-overbooking guardrails · auto-swap-finder · auto-EOD-email
- Phase F next wave: AI cost coach · predictive labor forecasting · dynamic surge pricing · voice-to-recipe · live kitchen-load balancing
- Refactor: Split POSTerminal.jsx (900+ lines), structured react-router config, real TOTP via pyotp, WebSocket real-time
