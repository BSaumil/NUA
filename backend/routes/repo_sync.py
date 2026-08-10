"""Repo auto-sync endpoints — visibility and manual trigger for the daily
GitHub sync. All routes are owner-only."""
from fastapi import APIRouter, Request, HTTPException
from routes.auth import get_current_user
from services import repo_sync_scheduler

router = APIRouter(prefix="/repo-sync", tags=["repo-sync"])


def _owner_only(user: dict) -> None:
    if user.get("role") not in ("owner",):
        raise HTTPException(403, "Owner only")


@router.get("/status")
async def get_status(request: Request, limit: int = 10):
    user = await get_current_user(request)
    _owner_only(user)
    return await repo_sync_scheduler.sync_status(limit=limit)


@router.post("/run")
async def run_now(request: Request):
    user = await get_current_user(request)
    _owner_only(user)
    return await repo_sync_scheduler.force_sync_now()
