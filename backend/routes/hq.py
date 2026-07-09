"""
HQ / Franchise scaffolding — cross-location roll-ups.

Uses the existing `businesses` collection with an optional `parentBrandId`
to define a franchise group. `X-Business-Id` and `X-Location-Id` headers
are honoured by the actor middleware; this router aggregates.
"""
from fastapi import APIRouter, Depends
from typing import Optional
from datetime import datetime, timezone, timedelta
from database import db
from deps import get_user

router = APIRouter(prefix="/hq")


@router.get("/brands")
async def brands(_: dict = Depends(get_user)):
    """List brand groups (business docs with `parentBrandId` = null)."""
    rows = await db.businesses.find({"$or": [{"parentBrandId": None}, {"parentBrandId": {"$exists": False}}]}, {"_id": 0}).to_list(100)
    return rows


@router.get("/locations")
async def locations(brand_id: Optional[str] = None, _: dict = Depends(get_user)):
    q = {"parentBrandId": brand_id} if brand_id else {}
    rows = await db.businesses.find(q, {"_id": 0}).to_list(500)
    return rows


@router.get("/kpi-roll-up")
async def kpi_roll_up(days: int = 7, _: dict = Depends(get_user)):
    """Aggregate revenue, covers, refunds by locationId across the network."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {
            "_id": {"$ifNull": ["$locationId", "$location"]},
            "revenue": {"$sum": "$total"},
            "covers": {"$sum": 1},
            "gst": {"$sum": "$gst"},
        }},
        {"$sort": {"revenue": -1}},
    ]
    rows = await db.transactions.aggregate(pipeline).to_list(200)
    total_rev = round(sum(r.get("revenue") or 0 for r in rows), 2)
    return {
        "days": days,
        "totalRevenue": total_rev,
        "locations": [
            {"location": r["_id"] or "Unassigned", "revenue": round(r.get("revenue") or 0, 2),
             "covers": r.get("covers") or 0, "gst": round(r.get("gst") or 0, 2)}
            for r in rows
        ],
    }


@router.get("/leaderboard")
async def leaderboard(_: dict = Depends(get_user)):
    """Rank locations by 30-day revenue."""
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    pipeline = [
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {"_id": {"$ifNull": ["$locationId", "$location"]}, "revenue": {"$sum": "$total"}}},
        {"$sort": {"revenue": -1}},
        {"$limit": 10},
    ]
    rows = await db.transactions.aggregate(pipeline).to_list(10)
    return [{"rank": i + 1, "location": r["_id"] or "Unassigned", "revenue": round(r.get("revenue") or 0, 2)}
             for i, r in enumerate(rows)]
