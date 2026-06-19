"""
Award + Superannuation engine.
Stores award catalogues (Fair Work Australia + multi-country) and computes
super contributions from existing payruns.

Award data here is intentionally a curated seed list — the user can extend or
override per-business. Real-world deployments typically sync from Fair Work
Modern Awards API (fairwork.gov.au) and country-equivalent regulators.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from database import db
import uuid

router = APIRouter()

# --- Models ----------------------------------------------------------------
class AwardClassification(BaseModel):
    level: str                  # e.g. "Level 1", "Introductory"
    description: str = ""
    baseHourly: float           # adult full-time hourly rate
    casualHourly: Optional[float] = None
    saturdayLoading: float = 0.0   # %
    sundayLoading: float = 0.0
    publicHolidayLoading: float = 0.0
    overtime150: float = 50.0
    overtime200: float = 100.0

class Award(BaseModel):
    id: str
    code: str                    # e.g. "MA000119"
    name: str
    country: str = "AU"
    regulator: str = "Fair Work Australia"
    industry: str = ""
    superRate: float = 11.5      # % of OTE (FY25/26 default; ramps to 12% in FY26)
    classifications: List[AwardClassification] = []
    notes: str = ""
    sourceUrl: str = ""
    installed: bool = False
    installedAt: Optional[str] = None

# --- Seed catalogue --------------------------------------------------------
# Numbers below are illustrative round figures; a production system would pull
# the exact published rate from each regulator. Hourly rates are AUD (adult FT)
# / NZD for NZ / GBP for UK etc.
SEED_AWARDS: list[dict] = [
    {
        "code": "MA000119", "name": "Restaurant Industry Award", "country": "AU",
        "industry": "Restaurants", "superRate": 11.5,
        "sourceUrl": "https://www.fairwork.gov.au/employment-conditions/awards/awards-summary/ma000119-summary",
        "classifications": [
            {"level": "Introductory", "baseHourly": 23.23, "casualHourly": 29.04, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 1 (Food & Beverage)", "baseHourly": 24.10, "casualHourly": 30.13, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 2 (Cook/Server)", "baseHourly": 24.95, "casualHourly": 31.19, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 3 (Senior Cook/Bartender)", "baseHourly": 25.81, "casualHourly": 32.26, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 4 (Tradesperson Cook)", "baseHourly": 27.21, "casualHourly": 34.01, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 5 (Senior Tradesperson)", "baseHourly": 28.83, "casualHourly": 36.04, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 6 (Supervisor)", "baseHourly": 29.59, "casualHourly": 36.99, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
        ],
    },
    {
        "code": "MA000009", "name": "Hospitality Industry General Award", "country": "AU",
        "industry": "Hotels, Pubs, Clubs", "superRate": 11.5,
        "sourceUrl": "https://www.fairwork.gov.au/employment-conditions/awards/awards-summary/ma000009-summary",
        "classifications": [
            {"level": "Level 1", "baseHourly": 23.23, "casualHourly": 29.04, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 2", "baseHourly": 24.10, "casualHourly": 30.13, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 3", "baseHourly": 24.95, "casualHourly": 31.19, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 4", "baseHourly": 26.10, "casualHourly": 32.63, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 5", "baseHourly": 27.21, "casualHourly": 34.01, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 6", "baseHourly": 28.83, "casualHourly": 36.04, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
        ],
    },
    {
        "code": "MA000003", "name": "Fast Food Industry Award", "country": "AU",
        "industry": "QSR & Cafes", "superRate": 11.5,
        "sourceUrl": "https://www.fairwork.gov.au/employment-conditions/awards/awards-summary/ma000003-summary",
        "classifications": [
            {"level": "Level 1", "baseHourly": 23.23, "casualHourly": 29.04, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 2", "baseHourly": 24.10, "casualHourly": 30.13, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
            {"level": "Level 3 (Manager)", "baseHourly": 27.50, "casualHourly": 34.38, "saturdayLoading": 25, "sundayLoading": 50, "publicHolidayLoading": 225},
        ],
    },
    {
        "code": "MA000004", "name": "General Retail Industry Award", "country": "AU",
        "industry": "Retail", "superRate": 11.5,
        "sourceUrl": "https://www.fairwork.gov.au/employment-conditions/awards/awards-summary/ma000004-summary",
        "classifications": [
            {"level": "Level 1", "baseHourly": 23.85, "casualHourly": 29.81, "saturdayLoading": 25, "sundayLoading": 100, "publicHolidayLoading": 225},
            {"level": "Level 2", "baseHourly": 24.30, "casualHourly": 30.38, "saturdayLoading": 25, "sundayLoading": 100, "publicHolidayLoading": 225},
            {"level": "Level 3", "baseHourly": 24.65, "casualHourly": 30.81, "saturdayLoading": 25, "sundayLoading": 100, "publicHolidayLoading": 225},
        ],
    },
    {
        "code": "UK-NMW", "name": "UK National Minimum Wage", "country": "UK",
        "regulator": "HMRC", "industry": "All", "superRate": 3.0,
        "sourceUrl": "https://www.gov.uk/national-minimum-wage-rates",
        "classifications": [
            {"level": "Age 21+", "baseHourly": 11.44, "casualHourly": 11.44, "saturdayLoading": 0, "sundayLoading": 0, "publicHolidayLoading": 100},
            {"level": "Age 18-20", "baseHourly": 8.60, "casualHourly": 8.60, "saturdayLoading": 0, "sundayLoading": 0, "publicHolidayLoading": 100},
        ],
    },
    {
        "code": "NZ-MW", "name": "NZ Minimum Wage (Adult)", "country": "NZ",
        "regulator": "MBIE NZ", "industry": "All", "superRate": 3.0,
        "sourceUrl": "https://www.employment.govt.nz/hours-and-wages/pay/minimum-wage/",
        "classifications": [
            {"level": "Adult", "baseHourly": 23.15, "casualHourly": 23.15, "saturdayLoading": 0, "sundayLoading": 0, "publicHolidayLoading": 50},
        ],
    },
    {
        "code": "US-FED-MW", "name": "US Federal Minimum Wage", "country": "US",
        "regulator": "Department of Labor", "industry": "All", "superRate": 0.0,
        "sourceUrl": "https://www.dol.gov/agencies/whd/minimum-wage",
        "classifications": [
            {"level": "Tipped Server", "baseHourly": 2.13, "casualHourly": 2.13, "saturdayLoading": 0, "sundayLoading": 0, "publicHolidayLoading": 0},
            {"level": "Non-tipped", "baseHourly": 7.25, "casualHourly": 7.25, "saturdayLoading": 0, "sundayLoading": 0, "publicHolidayLoading": 0},
        ],
    },
]

# --- Endpoints -------------------------------------------------------------
@router.get("/awards/catalogue")
async def awards_catalogue(country: Optional[str] = None):
    """List the seed awards (available to install)."""
    out = []
    installed = {a["code"]: a async for a in db.awards.find({}, {"_id": 0})}
    for s in SEED_AWARDS:
        if country and s["country"] != country:
            continue
        i = installed.get(s["code"])
        out.append({
            **s,
            "installed": bool(i),
            "installedAt": i.get("installedAt") if i else None,
            "id": (i or {}).get("id", ""),
        })
    return out

@router.post("/awards/install")
async def install_award(body: dict):
    """Install an award by code from the seed catalogue."""
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="code is required")
    seed = next((s for s in SEED_AWARDS if s["code"] == code), None)
    if not seed:
        raise HTTPException(status_code=404, detail="Award not in catalogue")
    doc = {
        "id": str(uuid.uuid4()),
        "code": seed["code"],
        "name": seed["name"],
        "country": seed.get("country", "AU"),
        "regulator": seed.get("regulator", "Fair Work Australia"),
        "industry": seed.get("industry", ""),
        "superRate": seed.get("superRate", 11.5),
        "classifications": seed.get("classifications", []),
        "sourceUrl": seed.get("sourceUrl", ""),
        "installedAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.awards.update_one({"code": doc["code"]}, {"$set": doc}, upsert=True)
    return doc

@router.get("/awards/installed")
async def list_installed_awards():
    rows = await db.awards.find({}, {"_id": 0}).to_list(200)
    return rows

@router.delete("/awards/{code}")
async def uninstall_award(code: str):
    res = await db.awards.delete_one({"code": code})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not installed")
    return {"deleted": True}

# --- Super calc from payruns ----------------------------------------------
@router.post("/payruns/super-by-award")
async def super_by_award(body: dict):
    """Compute super contributions for each staff member in a payrun using
    the installed Award's superRate.

    Body: { period: "week" | "fortnight" | "month", awardCode: str (optional)
            payrun: { staffPayroll: [{name, role, grossPay, awardCode?, classification?}, ...] } }

    If `awardCode` is supplied at the top level it applies to everyone unless
    the row has its own awardCode. Falls back to 11.5% if no award installed.
    """
    awardCode = body.get("awardCode")
    staff = (body.get("payrun") or {}).get("staffPayroll", [])
    if not isinstance(staff, list):
        raise HTTPException(status_code=400, detail="payrun.staffPayroll must be a list")

    # Pull installed awards into a {code: doc} map
    installed = {a["code"]: a async for a in db.awards.find({}, {"_id": 0})}

    out = []
    total = 0.0
    unresolved: set[str] = set()
    for row in staff:
        gross = float(row.get("grossPay", 0) or 0)
        code = row.get("awardCode") or awardCode
        rate = 11.5
        award_name = None
        if code:
            doc = installed.get(code)
            if doc:
                rate = float(doc.get("superRate", 11.5))
                award_name = doc.get("name")
            else:
                # Referenced but not installed — surface to UI so it can prompt
                unresolved.add(code)
        contribution = round(gross * (rate / 100.0), 2)
        out.append({
            **row,
            "awardCode": code,
            "awardName": award_name,
            "superRate": rate,
            "superContribution": contribution,
        })
        total += contribution

    return {
        "totalSuper": round(total, 2),
        "staffSuper": out,
        "unresolvedAwards": sorted(unresolved),
        "computedAt": datetime.now(timezone.utc).isoformat(),
    }
