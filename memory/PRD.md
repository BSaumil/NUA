# NUA POS — PRD v17.0 (Loyalty + Ash Agent + Voice-Everywhere)

## v17 (Feb 2026) — Iteration 23

### Backend (`routes/loyalty_engine.py`)
- `GET/PUT /api/loyalty/config` — earnRate, redeemRate, minRedeem, categoryMultipliers
- `POST /api/loyalty/earn` — credits points with category multipliers (idempotent by txnId)
- `POST /api/loyalty/redeem` — burns points at checkout, returns face value
- `GET /api/loyalty/balance/{customerId}` — current balance + canRedeem flag
- `GET /api/loyalty/ledger/{customerId}` — full audit ledger
- `GET /api/agent/decisions` — Ash's autonomous action log
- `GET /api/agent/segments` — VIP / regular / at-risk / first-timer
- `POST /api/agent/tick` — run all autonomous rules once
- `POST /api/agent/voice-command` — text or audio → GPT-5.2 intent → instruction
- `GET /api/agent/voice-catalog` — supported voice phrases per section

### Frontend
- `pages/LoyaltyConfig.jsx` (`/loyalty-config`) — owner sets category multipliers
- `pages/AgentDashboard.jsx` (`/agent`) — Ash decisions + segment counters + "Run Cycle"
- `components/VoiceCommandCatalog.jsx` — modal listing voice commands per section
- POSTerminal updates:
  - Customer selection auto-loads loyalty balance + tier badge
  - **Points & Pay block** appears when balance >= minRedeem (default 50)
  - Live redemption-discount line in cart totals
  - Transaction commit now records ledger (redeem first, then earn on net spend)
- BottomDock splash: new "Analytics & AI" group includes Ash Agent + Audit + Anomalies + Heatmap + Cohort + Swaps + Security
- "Customers" splash group adds "Loyalty Config"

### Math example (verified via curl)
- Cart: 2× Latte ($5 in Beverages) + 1× Croissant ($4 in Bakery)
- Multipliers: Beverages 2x, Bakery 1.5x
- Earned: (10 × 1 × 2) + (4 × 1 × 1.5) = **26 points** ✅
- Balance 26 pts = $0.26 value, canRedeem = false (< 50 min)

### Ash auto-decision rules
1. At-Risk flag (no visit > 60 days)
2. Birthday vouchers (next 7 days)
3. Low-stock reorder alert (stock ≤ 5)
4. Inventory anomaly detection (sales-velocity spike > 30%)
5. Tonight blast suggestion (bookings today < 5 → suggest VIP outreach)

## Credentials
Owner: owner@nuva.com / NuvaOwner2026!  
Manager: manager@nuva.com / Staff2026!  
Cashier: cashier@nuva.com / Staff2026!  
Kitchen: kitchen@nuva.com / Staff2026!  
2FA demo: `123456`

## Testing (Iteration 23)
- curl-verified: loyalty config CRUD, earn (26 pts with multipliers), balance, agent tick (1 decision + 4 first-timers), voice command ("open dashboard" → navigate intent)
- Playwright-verified: /loyalty-config + /agent + /pos with Voice btn all render

## Backlog
- Phase B (user keys): WhatsApp · Twilio · Stripe Tap-to-Pay · Crypto USDC · Xero/QB · Uber Eats · DoorDash · Google Reserve · TikTok Shop
- Phase E: deeper autonomy + voice per section (auto-publish AI roster, auto-confirm SMS, auto-tag VIPs, voice "void last item")
- Phase F (Nomni gap): AI Phone Agent · auto-PO generation · live menu A/B · guest predictive ordering · dynamic surge pricing · AI cost coach
- Phase G: split POSTerminal.jsx · structured routes · real TOTP · WebSocket real-time
- Phase H: SOC2 audit log retention · IP allowlists · consent ledger · WCAG 2.2 AA
