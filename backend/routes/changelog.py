"""
What's New — a release-notes feed for the people running the business, not
the people building it. Owners/managers have no visibility into what
changed in NUA POS recently or what's coming — this is that answer,
without needing to read a commit log.

  GET  /changelog                 — shipped entries, ?window=week|month|all
  GET  /changelog/upcoming        — roadmap items not yet shipped
  GET  /changelog/summary         — counts for a "3 new this week" badge
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional
from database import db
from deps import require_owner_or_manager
from utils.mongo_safe import safe_parse_list
from models.changelog import ChangelogEntry

router = APIRouter(prefix="/changelog")

WINDOW_DAYS = {"week": 7, "month": 30}


@router.get("")
async def list_changelog(window: Optional[str] = None, _: dict = Depends(require_owner_or_manager)):
    query = {"status": "shipped"}
    days = WINDOW_DAYS.get(window)
    if days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        query["releasedAt"] = {"$gte": cutoff}
    rows = await db.changelog_entries.find(query, {"_id": 0}).sort("releasedAt", -1).to_list(500)
    return safe_parse_list(rows, ChangelogEntry, where="changelog_entries")


@router.get("/upcoming")
async def list_upcoming(_: dict = Depends(require_owner_or_manager)):
    rows = await db.changelog_entries.find(
        {"status": "upcoming"}, {"_id": 0}
    ).sort("createdAt", 1).to_list(200)
    return safe_parse_list(rows, ChangelogEntry, where="changelog_entries")


@router.get("/summary")
async def changelog_summary(_: dict = Depends(require_owner_or_manager)):
    week_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    month_cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    this_week = await db.changelog_entries.count_documents(
        {"status": "shipped", "releasedAt": {"$gte": week_cutoff}})
    this_month = await db.changelog_entries.count_documents(
        {"status": "shipped", "releasedAt": {"$gte": month_cutoff}})
    upcoming = await db.changelog_entries.count_documents({"status": "upcoming"})
    return {"thisWeek": this_week, "thisMonth": this_month, "upcoming": upcoming}
