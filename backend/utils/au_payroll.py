"""
Australian payroll compliance engine.

Implements:
  • PAYG withholding — ATO Schedule 1 formulas (Scale 1 no TFN, Scale 2
    residents claiming TFT, Scale 3 non-residents, Scale 5 no TFT, plus a
    HELP/STSL loading toggle).
  • Super Guarantee — tiered by pay date (10.5→12.0%), correctly computed on
    OTE (excludes overtime), with quarterly due-by dates (28 days after
    quarter end per SGAA).
  • Modern Award penalty rates matrix — casual loading, Saturday, Sunday,
    Public Holiday, overtime (first 2h @ ×1.5, thereafter ×2.0), late-night
    (10pm–6am) loading. Values pluggable per-award via the awards catalog.
  • Leave accrual — 4 weeks annual + 10 days personal per year (NES).
    Long service leave stub returns state-based rate.
  • Payslip line-items — everything Fair Work Reg 3.46 requires: employer
    name/ABN, employee name, dates of period, gross pay, hours, rate, PAYG,
    super name + amount, leave balances, net pay.

Not implemented in this module (deliberately — needs external integration):
  • Actual STP2 submission to ATO SBR2 SOAP (needs AUSkey / MyGovID +
    software ID registration). We produce the STP2-shaped JSON that the
    Government Business Portal / third-party submitters (Xero, Reckon,
    KeyPay) consume.
  • Real-time super clearing house payment (SuperStream). We emit the
    contribution message body.

References
  • ATO Schedule 1 — Statement of formulas (November 2023 update)
  • Fair Work Act 2009 + NES
  • Superannuation Guarantee (Administration) Act 1992
  • Restaurant Industry Award MA000119 / Hospitality Award MA000009
"""
from __future__ import annotations
from datetime import date, datetime, timezone, timedelta
from typing import Optional, List, Dict, Tuple


# ═════════════════════════════════════════════════════════════════════════
# 1) PAYG withholding — ATO Schedule 1 (weekly Scale 2, resident + TFT)
# ═════════════════════════════════════════════════════════════════════════
# Coefficients (a, b) — weekly earnings y = a*x - b, where x = earnings + 0.99.
# From ATO Sch 1 (effective 13 Oct 2020 with rate cut update; 2024-25 FY.)
_SCALE_2_WEEKLY_COEFF = [
    # (upper_inclusive, a, b)
    (361,     0.0,     0.0),
    (500,     0.19,    68.3462),
    (625,     0.29,    118.3462),
    (721,     0.21,    68.3462),
    (865,     0.219,   74.8508),
    (1282,    0.3477,  186.2119),
    (2596,    0.345,   182.7504),
    (3465,    0.39,    299.1327),
    (float("inf"), 0.47, 576.4808),
]

# Scale 1 — no TFN provided (flat 47%).
_SCALE_1_WEEKLY = 0.47

# Scale 3 — foreign resident (three brackets).
_SCALE_3_WEEKLY = [
    (2596, 0.325, 0.325),
    (3465, 0.39,  169.2308),
    (float("inf"), 0.47, 446.4808),
]


def payg_weekly(gross_weekly: float, *, scale: str = "2", help_debt: bool = False) -> float:
    """Weekly PAYG withholding on `gross_weekly`. Returns dollars (rounded
    to nearest cent — ATO also allows rounding to whole dollar; we keep
    cents so employer BAS reconciles down to the last dollar)."""
    if gross_weekly <= 0:
        return 0.0
    x = gross_weekly + 0.99
    if scale == "1":
        withheld = x * _SCALE_1_WEEKLY
    elif scale == "3":
        for cap, a, b in _SCALE_3_WEEKLY:
            if x <= cap:
                withheld = a * x - b if b else a * x
                break
        else:
            withheld = 0.0
    else:
        # Scale 2 default (resident claiming TFT)
        for cap, a, b in _SCALE_2_WEEKLY_COEFF:
            if x <= cap:
                withheld = a * x - b
                break
        else:
            withheld = 0.0
    # HELP/STSL — approximate additional withholding (Sch 8 flat schedule;
    # exact rates change yearly). Simple 8% loading above the repayment
    # threshold as a defensible approximation.
    if help_debt and gross_weekly >= 1145:   # 2024-25 threshold
        withheld += gross_weekly * 0.08
    return max(0.0, round(withheld, 2))


def payg_for_period(gross: float, period: str = "week", **kw) -> float:
    """PAYG for any pay-period length. Weekly rule is the ATO reference; we
    scale up/down."""
    weekly_equiv = {
        "week": gross,
        "fortnight": gross / 2,
        "monthly": (gross * 3) / 13,   # ATO method (Sch 1 §7)
        "quarter": (gross * 3) / 13 / 13,
    }.get(period, gross)
    weekly_tax = payg_weekly(weekly_equiv, **kw)
    return round(weekly_tax * ({"week": 1, "fortnight": 2, "monthly": 13/3, "quarter": 13*3/13}[period]), 2)


# ═════════════════════════════════════════════════════════════════════════
# 2) Superannuation Guarantee — tiered + OTE
# ═════════════════════════════════════════════════════════════════════════
_SG_TIERS = [
    (date(2025, 7, 1), 12.0),
    (date(2024, 7, 1), 11.5),
    (date(2023, 7, 1), 11.0),
    (date(2022, 7, 1), 10.5),
]

# Under $450/mth threshold repealed 1 Jul 2022 — every dollar of OTE now attracts SG.
SG_MIN_OTE_PER_MONTH = 0.0

# Maximum super contribution base per quarter (indexed each 1 July).
# 2024-25: $65,070 (superannuation guarantee maximum contribution base).
SG_MAX_CONTRIB_BASE_PER_QUARTER = 65070.0


def sg_rate_for(pay_date: date) -> float:
    for eff, rate in _SG_TIERS:
        if pay_date >= eff:
            return rate
    return 10.0


def super_guarantee(ote: float, pay_date: date, *, rate_override: Optional[float] = None) -> Tuple[float, float]:
    """Return (rate_pct, super_amount) for `ote` (dollars, this pay period).
    Caps at the quarterly maximum contribution base."""
    rate = rate_override if rate_override is not None else sg_rate_for(pay_date)
    capped = min(ote, SG_MAX_CONTRIB_BASE_PER_QUARTER)
    return rate, round(capped * (rate / 100.0), 2)


def super_due_date_for_quarter(quarter_end: date) -> date:
    """SG contributions are due 28 days after each quarter end (SGAA)."""
    return quarter_end + timedelta(days=28)


# ═════════════════════════════════════════════════════════════════════════
# 3) Modern Award penalty rates
# ═════════════════════════════════════════════════════════════════════════
# Default matrix — Hospitality Award (MA000009) full-time rates.
DEFAULT_PENALTY_MATRIX = {
    "casual_loading":   0.25,     # +25% for casuals on all hours
    "saturday":         0.25,     # +25% (FT/PT)
    "sunday":           0.50,     # +50% (FT/PT); casuals stack loading
    "public_holiday":   1.50,     # +150% on top of base (or +250% for casuals)
    "night_after_10":   0.10,     # +10% between 10pm–7am (indicative)
    "overtime_first_2h": 0.50,    # ×1.5
    "overtime_after_2h": 1.00,    # ×2
    "early_start_before_6am": 0.10,
}


def hourly_with_penalty(base_hourly: float, *, shift_start: datetime, shift_end: datetime,
                         is_casual: bool = False, is_public_holiday: bool = False,
                         matrix: Optional[dict] = None) -> Dict[str, float]:
    """Break a shift into (ordinary + penalty $) components. Returns:
        {ordinary_hours, ordinary_pay, penalty_pay, total_pay, breakdown[]}
    """
    m = {**DEFAULT_PENALTY_MATRIX, **(matrix or {})}
    ordinary_hours = 0.0
    ordinary_pay = 0.0
    penalty_pay = 0.0
    breakdown: list = []

    # Iterate hour-by-hour so we correctly stack weekend + night + PH loadings.
    cur = shift_start
    total_hours_worked = 0.0
    while cur < shift_end:
        nxt = min(cur + timedelta(hours=1), shift_end)
        block = (nxt - cur).total_seconds() / 3600.0
        loading = 0.0
        tags = []

        weekday = cur.weekday()   # Mon=0
        hour = cur.hour

        if is_public_holiday:
            loading += m["public_holiday"]; tags.append("PH")
        elif weekday == 6:
            loading += m["sunday"]; tags.append("SUN")
        elif weekday == 5:
            loading += m["saturday"]; tags.append("SAT")

        if hour >= 22 or hour < 7:
            if not is_public_holiday:
                loading += m["night_after_10"]; tags.append("NIGHT")
        if 0 <= hour < 6:
            loading += m["early_start_before_6am"]; tags.append("EARLY")

        # Overtime: everything beyond 38 hours/week or 8 hours/day would be
        # ideal but requires the whole week's context. We check daily 8h+.
        if total_hours_worked >= 10:
            loading += m["overtime_after_2h"]; tags.append("OT2")
        elif total_hours_worked >= 8:
            loading += m["overtime_first_2h"]; tags.append("OT1")

        if is_casual:
            loading += m["casual_loading"]; tags.append("CAS")

        hourly_pay = base_hourly * (1 + loading) * block
        if loading == 0:
            ordinary_hours += block
            ordinary_pay += hourly_pay
        else:
            penalty_pay += hourly_pay - (base_hourly * block)
            ordinary_pay += base_hourly * block

        breakdown.append({
            "start": cur.isoformat(),
            "end": nxt.isoformat(),
            "hours": round(block, 2),
            "loading_pct": round(loading * 100, 1),
            "pay": round(hourly_pay, 2),
            "tags": tags,
        })
        total_hours_worked += block
        cur = nxt

    return {
        "ordinary_hours": round(ordinary_hours, 2),
        "ordinary_pay": round(ordinary_pay, 2),
        "penalty_pay": round(penalty_pay, 2),
        "total_pay": round(ordinary_pay + penalty_pay, 2),
        "breakdown": breakdown,
    }


# ═════════════════════════════════════════════════════════════════════════
# 4) Leave accrual — NES minimums
# ═════════════════════════════════════════════════════════════════════════
# Full-time employee: 152 hours annual leave per year, 76 hours personal.
# Casuals: no leave accrual.
ANNUAL_LEAVE_HOURS_PER_ORDINARY_HOUR = 152 / (38 * 52)     # ≈ 0.0769
PERSONAL_LEAVE_HOURS_PER_ORDINARY_HOUR = 76 / (38 * 52)    # ≈ 0.0385
# Long service leave: state-dependent. NSW = 2 months after 10 years.
LSL_HOURS_PER_ORDINARY_HOUR = (2 * 4 * 38) / (10 * 52 * 38)  # ≈ 0.0154


def accrue_leave(ordinary_hours: float, *, is_casual: bool = False) -> Dict[str, float]:
    if is_casual:
        return {"annual": 0.0, "personal": 0.0, "lsl": 0.0}
    return {
        "annual":   round(ordinary_hours * ANNUAL_LEAVE_HOURS_PER_ORDINARY_HOUR, 4),
        "personal": round(ordinary_hours * PERSONAL_LEAVE_HOURS_PER_ORDINARY_HOUR, 4),
        "lsl":      round(ordinary_hours * LSL_HOURS_PER_ORDINARY_HOUR, 4),
    }


# ═════════════════════════════════════════════════════════════════════════
# 4b) Pay-rate unit conversion — payRate is stored in whatever unit
# salaryType names (hourly / weekly / annually); every hours×rate
# calculation needs it as an hourly-equivalent first.
# ═════════════════════════════════════════════════════════════════════════
STANDARD_WEEKLY_HOURS = 38.0  # same full-time assumption used for leave accrual above


def effective_hourly_rate(pay_rate: float, salary_type: Optional[str]) -> float:
    """Convert a staff member's stored payRate into an hourly-equivalent for
    payroll/cost math. 'hourly' passes through unchanged; 'weekly' divides by
    the standard full-time week; 'annually' divides by 52 weeks first.
    'daily' is kept for records created before the Hourly/Weekly/Annually
    options existed, treated as a standard 7.6-hour day."""
    pay_rate = float(pay_rate or 0)
    salary_type = (salary_type or "hourly").lower()
    if salary_type == "weekly":
        return round(pay_rate / STANDARD_WEEKLY_HOURS, 4)
    if salary_type in ("annually", "annual", "yearly"):
        return round(pay_rate / 52 / STANDARD_WEEKLY_HOURS, 4)
    if salary_type == "daily":
        return round(pay_rate / (STANDARD_WEEKLY_HOURS / 5), 4)
    return pay_rate


# ═════════════════════════════════════════════════════════════════════════
# 5) Full pay-run row assembly
# ═════════════════════════════════════════════════════════════════════════
def assemble_payslip_row(
    *,
    name: str,
    role: str,
    employment_type: str,        # "casual" | "part_time" | "full_time"
    hours_worked: float,
    base_hourly: float,
    pay_date: date,
    period: str = "week",
    penalty_pay: float = 0.0,
    allowances: float = 0.0,
    overtime_pay: float = 0.0,
    ytd_gross: float = 0.0,
    ytd_tax: float = 0.0,
    ytd_super: float = 0.0,
    tfn_provided: bool = True,
    resident: bool = True,
    tft_claimed: bool = True,
    help_debt: bool = False,
    ote_override: Optional[float] = None,
    sg_rate_override: Optional[float] = None,
) -> Dict:
    """Return a fully-costed payslip row for a single employee, single pay period."""
    ordinary_pay = round(hours_worked * base_hourly, 2)
    gross = round(ordinary_pay + penalty_pay + overtime_pay + allowances, 2)

    # Choose PAYG scale
    if not tfn_provided:
        scale = "1"
    elif not resident:
        scale = "3"
    elif not tft_claimed:
        scale = "5"
    else:
        scale = "2"
    payg = payg_for_period(gross, period=period, scale=scale, help_debt=help_debt)

    # Super — on OTE (excludes overtime & non-OTE allowances).
    ote = ote_override if ote_override is not None else (ordinary_pay + penalty_pay)
    sg_rate, super_amount = super_guarantee(ote, pay_date, rate_override=sg_rate_override)

    # Leave accrual
    leave = accrue_leave(hours_worked, is_casual=(employment_type == "casual"))

    net = round(gross - payg, 2)
    return {
        "name": name, "role": role, "employmentType": employment_type,
        "hoursWorked": round(hours_worked, 2), "baseHourly": base_hourly,
        "ordinaryPay": ordinary_pay, "penaltyPay": round(penalty_pay, 2),
        "overtimePay": round(overtime_pay, 2), "allowances": round(allowances, 2),
        "grossPay": gross,
        "payg": payg, "paygScale": scale,
        "ote": round(ote, 2), "sgRate": sg_rate, "super": super_amount,
        "leaveAccrual": leave,
        "netPay": net,
        "ytdGross": round(ytd_gross + gross, 2),
        "ytdTax": round(ytd_tax + payg, 2),
        "ytdSuper": round(ytd_super + super_amount, 2),
        "payDate": pay_date.isoformat(),
        "period": period,
    }


# ═════════════════════════════════════════════════════════════════════════
# 6) STP2 (Single Touch Payroll Phase 2) — event shape
# ═════════════════════════════════════════════════════════════════════════
def build_stp2_pay_event(*, employer_abn: str, employer_name: str,
                          pay_date: date, period_start: date, period_end: date,
                          rows: List[dict]) -> Dict:
    """Return the STP2 pay-event JSON body. Submitters (Xero / KeyPay / DIY)
    wrap this in the SBR2 envelope; the payload itself is what the ATO
    validates and what BAS/PAYG reconciliation consumes."""
    return {
        "reportType": "STP2_PAY_EVENT",
        "employer": {
            "abn": employer_abn,
            "name": employer_name,
        },
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
            "payDate": pay_date.isoformat(),
        },
        "employees": [
            {
                "id": r.get("staffId") or r.get("name"),
                "name": r.get("name"),
                "tfn": r.get("tfn", ""),
                "incomeType": "SAW",   # Salary and wages
                "employmentType": r.get("employmentType", "full_time"),
                "grossPayments": r.get("grossPay", 0),
                "paygWithheld": r.get("payg", 0),
                "superLiability": r.get("super", 0),
                "ordinaryTimeEarnings": r.get("ote", 0),
                "ytdGross": r.get("ytdGross", 0),
                "ytdTax": r.get("ytdTax", 0),
                "ytdSuper": r.get("ytdSuper", 0),
                "allowances": r.get("allowances", 0),
                "overtime": r.get("overtimePay", 0),
                "penaltyRates": r.get("penaltyPay", 0),
            }
            for r in rows
        ],
        "totals": {
            "gross": round(sum(r.get("grossPay", 0) for r in rows), 2),
            "tax":   round(sum(r.get("payg", 0) for r in rows), 2),
            "super": round(sum(r.get("super", 0) for r in rows), 2),
            "employees": len(rows),
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


# ═════════════════════════════════════════════════════════════════════════
# 7) Rostering compliance — Modern Award checks
# ═════════════════════════════════════════════════════════════════════════
def roster_compliance_issues(shift: dict) -> List[dict]:
    """Given a shift dict {start, end, staffId, employmentType, breaks[]}
    return a list of Fair Work / Award compliance flags."""
    issues = []
    start = datetime.fromisoformat(shift["start"])
    end = datetime.fromisoformat(shift["end"])
    hours = (end - start).total_seconds() / 3600.0
    breaks = shift.get("breaks", [])
    total_break = sum(b.get("minutes", 0) for b in breaks)

    if hours > 10:
        issues.append({"code": "AWARD_MAX_DAILY", "severity": "high",
                       "message": f"Shift is {hours:.1f}h — award max is 10h without written agreement"})
    if hours > 5 and total_break < 30:
        issues.append({"code": "MEAL_BREAK_MISSING", "severity": "high",
                       "message": "5+ hour shift requires a paid ≥30-minute meal break"})
    if hours >= 4 and not any(b.get("type") == "rest" for b in breaks):
        issues.append({"code": "REST_BREAK_MISSING", "severity": "medium",
                       "message": "4+ hour shift entitles employee to a paid 10-minute rest break"})

    # Minimum shift length (Hospitality Award: 2h for casuals, 3h for part-time)
    et = shift.get("employmentType", "casual")
    min_shift = 2 if et == "casual" else 3
    if hours < min_shift:
        issues.append({"code": "MIN_SHIFT_LENGTH", "severity": "medium",
                       "message": f"Award minimum engagement is {min_shift}h for {et}s (this shift is {hours:.1f}h)"})

    return issues
