# NUA POS — PRD v19.0 (Phase E + F Wave 2)

## v19 (Feb 2026) — Iteration 25

### Diagnostic fixes (P0)
- `/api/reservations` 500 → 200: `Reservation` model now accepts legacy `customerName`/`phone` via `model_validator(mode='before')`.
- `/api/purchase-orders` 500 → 200: removed conflicting strict-schema GET in `analytics.py`; `phase_ef.py` is the canonical handler.
- `phase_ef.py` phone-agent + auto-confirm now insert/read using `guestName`/`guestPhone`.

### Backend (`routes/phase_ef_wave2.py` — new)
- `POST /api/ai/upsell` — LLM (GPT-5.2) suggests 1-3 high-margin add-ons given current cart
- `GET /api/ai/price-tune` · `POST /api/ai/price-tune/apply` — 30-day velocity vs median → recommend raise/drop with audit `priceHistory` array
- `POST /api/ai/overbooking-check` — capacity + 10% buffer (configurable via `settings.overbooking.bufferRatio`) vs existing covers in ±30 min slot
- `GET /api/ai/cost-coach` — 30-day food-cost analysis vs 32% target + LLM 3-action plan
- `GET /api/ai/labor-forecast` — 8-week pattern → 7-day hourly FOH/BOH staffing needs
- `GET /api/ai/surge-recommendations` · `POST /api/ai/surge/apply` · `GET /api/ai/surge/active` — per (day, hour) demand multipliers
- `POST /api/ai/voice-recipe` · `GET /api/ai/recipes` — chef text or voice → structured recipe spec (Whisper + GPT-5.2); validates name+ingredients before persist
- `GET /api/ai/kitchen-load` — open-ticket station load + rebalance/priority suggestions

### Frontend
- New pages: `AICostCoach.jsx` `LaborForecast.jsx` `SurgePricing.jsx` `VoiceRecipe.jsx` `KitchenLoad.jsx` `PriceTune.jsx`
- 6 new routes wired in `App.js`: `/ai-cost-coach` `/labor-forecast` `/surge-pricing` `/voice-recipe` `/kitchen-load` `/price-tune`
- `BottomDock` "More" splash — Analytics & AI group expanded with 6 new tiles
- `POSTerminal.jsx` — AI upsell strip (debounced 1.2s, LLM-driven) under cart with 1-3 high-margin pairings
- `Reservations.jsx` — overbooking guardrail dialog before reservation creation (fail-open)

### Curl + Playwright verified
- All 8 Wave 2 endpoints return 200; LLM upsell returns 3 valid suggestions referencing real productIds
- POS cart → 3-5s → "✨ AI SUGGESTS" strip with reasoned upsells ✅
- All 6 new pages render with correct titles, no console errors ✅
- testing_agent iteration_22: 13/13 backend pytest green, 6/6 frontend smoke green

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
- Real-time: WebSocket for kitchen-load auto-refresh and live A/B test exposure
- Refactor: Split POSTerminal.jsx (~950 lines) into Cart/Payment/QR sub-components, structured react-router config, real TOTP via pyotp
- Surge pricing apply to live POS prices (currently only persisted) — hook into product price calc
- Recipe → menu item: 1-click convert /voice-recipe generated spec into a product with cost-rolled-up from ingredient prices
- Auto-swap-finder + auto-EOD-email (Phase E next wave residual)
