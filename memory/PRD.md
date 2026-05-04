# NUVA POS — PRD v12.0

## Architecture: 22 backend routes, React + FastAPI + MongoDB + GPT-5.2

## Roster Enhancement (v12)
- **Add Week Roster**: Select staff + position (Barista/Bar/Floor/Kitchen/Register/Manager/Host/Dishwasher) + select days (Mon-Sun) with individual time ranges → creates all shifts at once
- **Budget Summary**: Total Shifts, Total Hours, Weekly Budget (hours × payRate)
- **Print Roster**: Opens formatted print window with ONLY staff names, positions, days, times — NO wages, NO tips, NO costs
- **Position Column**: Each shift shows assigned position (Badge)
- **Cost Column**: Owner/Manager only — calculates hours × payRate per shift

## Credentials
Owner: owner@nuva.com / NuvaOwner2026! | Manager: manager@nuva.com / Staff2026! | Cashier: cashier@nuva.com / Staff2026!

## Testing: 17 iterations, all pass
## Backlog: P1 SendGrid | P2 Nightly EOD cron | P3 Delivery APIs
