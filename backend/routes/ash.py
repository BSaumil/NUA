"""
Ash — the autonomous operating layer endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from database import db
from deps import get_user, require_owner_or_manager
from services import ash_intelligence

router = APIRouter(prefix="/ash")


@router.get("/insights")
async def list_insights(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    include_resolved: bool = False,
    limit: int = 200,
    _: dict = Depends(get_user),
):
    q = {}
    if category: q["category"] = category
    if severity: q["severity"] = severity
    if not include_resolved:
        q["resolvedAt"] = None
    rows = await db.ash_insights.find(q, {"_id": 0}).sort("createdAt", -1).limit(limit).to_list(limit)
    return rows


@router.get("/insights/summary")
async def insights_summary(_: dict = Depends(get_user)):
    """Grouped counts for the dashboard."""
    pipeline = [
        {"$match": {"resolvedAt": None}},
        {"$group": {"_id": {"category": "$category", "severity": "$severity"}, "count": {"$sum": 1}}},
    ]
    rows = await db.ash_insights.aggregate(pipeline).to_list(200)
    by_cat = {}
    for r in rows:
        c = r["_id"]["category"]; s = r["_id"]["severity"]
        by_cat.setdefault(c, {"info": 0, "notice": 0, "warning": 0, "high": 0})
        by_cat[c][s] = by_cat[c].get(s, 0) + r["count"]
    total = sum(sum(v.values()) for v in by_cat.values())
    high = sum(v.get("high", 0) for v in by_cat.values())
    warning = sum(v.get("warning", 0) for v in by_cat.values())
    return {"total": total, "high": high, "warning": warning, "byCategory": by_cat}


@router.post("/run")
async def run(include_summary: bool = False, _: dict = Depends(require_owner_or_manager)):
    """Manually trigger a full Ash pass — normally run on a cadence."""
    return await ash_intelligence.run_all_insights(include_summary=include_summary)


@router.post("/summary/weekly")
async def weekly_summary(_: dict = Depends(require_owner_or_manager)):
    doc = await ash_intelligence.generate_weekly_summary()
    if doc:
        await db.ash_insights.update_one(
            {"category": doc["category"], "key": doc["key"]},
            {"$set": doc, "$setOnInsert": {"firstSeenAt": doc["createdAt"]}},
            upsert=True,
        )
    return doc


@router.post("/insights/{iid}/dismiss")
async def dismiss_insight(iid: str, _: dict = Depends(require_owner_or_manager)):
    from datetime import datetime, timezone
    r = await db.ash_insights.update_one({"id": iid}, {"$set": {"resolvedAt": datetime.now(timezone.utc).isoformat(), "resolvedBy": "manual"}})
    if r.matched_count == 0:
        raise HTTPException(404, "Insight not found")
    return {"dismissed": True}


@router.get("/capabilities")
async def capabilities(_: dict = Depends(get_user)):
    """Enumerate what Ash watches for — used by the intro dashboard card."""
    return {
        "capabilities": [
            {"key": "staffing",         "label": "Predict staffing shortages"},
            {"key": "theft",            "label": "Detect theft"},
            {"key": "fraud",            "label": "Detect fraud"},
            {"key": "pricing",          "label": "Recommend pricing"},
            {"key": "promotion",        "label": "Suggest promotions"},
            {"key": "waste",            "label": "Predict food waste"},
            {"key": "labour",           "label": "Detect unusual labour costs"},
            {"key": "menu",             "label": "Detect menu underperformance"},
            {"key": "weather",          "label": "Forecast weather impact"},
            {"key": "demand",           "label": "Forecast public holiday demand"},
            {"key": "purchasing",       "label": "Recommend purchasing"},
            {"key": "roster",           "label": "Recommend roster changes"},
            {"key": "burnout",          "label": "Predict staff burnout"},
            {"key": "churn",            "label": "Predict customer churn"},
            {"key": "menu_engineering", "label": "Recommend menu engineering"},
            {"key": "summary",          "label": "Auto-write weekly business summary"},
        ],
    }
