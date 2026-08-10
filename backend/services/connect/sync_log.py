"""Sync-run ledger — the "raw data and everything, from inbound to outbound
with reporting" surface. Every connector run (manual sync or webhook-driven)
writes one of these, with a capped sample of the actual raw provider
payloads it processed, so a real audit trail exists: not just "last synced
at 3:04pm" but *what was in the sync* and *what NUA did with it*.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database import db

MAX_RAW_SAMPLES = 25


class SyncRun:
    """Accumulates one connector run's counts + raw samples, then persists
    on finish(). Used as an async context manager so a crash mid-sync still
    gets recorded as an error run instead of vanishing silently."""

    def __init__(self, business_id: str, provider: str, sync_type: str, direction: str = "inbound"):
        self.id = f"SYNC-{uuid.uuid4().hex[:10].upper()}"
        self.business_id = business_id
        self.provider = provider
        self.sync_type = sync_type  # catalog | sales | customers | webhook
        self.direction = direction  # inbound | outbound
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.counts = {"fetched": 0, "created": 0, "updated": 0, "skipped": 0, "failed": 0}
        self.raw_samples: List[Dict[str, Any]] = []
        self.error: Optional[str] = None

    def add_sample(self, raw: Dict[str, Any]) -> None:
        if len(self.raw_samples) < MAX_RAW_SAMPLES:
            self.raw_samples.append(raw)

    def bump(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    async def __aenter__(self) -> "SyncRun":
        await db.integration_sync_runs.insert_one({
            "id": self.id, "businessId": self.business_id, "provider": self.provider,
            "syncType": self.sync_type, "direction": self.direction, "status": "running",
            "startedAt": self.started_at, "finishedAt": None,
            "counts": self.counts, "rawSamples": [], "errorMessage": None,
        })
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        status = "success"
        if exc is not None:
            status = "error"
            self.error = f"{exc_type.__name__}: {exc}"
        await db.integration_sync_runs.update_one(
            {"id": self.id},
            {"$set": {
                "status": status,
                "finishedAt": datetime.now(timezone.utc).isoformat(),
                "counts": self.counts,
                "rawSamples": self.raw_samples,
                "errorMessage": self.error,
            }},
        )
        # Swallow nothing — let the caller's exception propagate after we've
        # recorded it, so a failed sync is both logged AND visible as an error.
        return False


async def list_sync_runs(business_id: str, provider: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {"businessId": business_id}
    if provider:
        query["provider"] = provider
    return await db.integration_sync_runs.find(query, {"_id": 0}).sort("startedAt", -1).to_list(limit)


async def get_sync_run(business_id: str, run_id: str) -> Optional[Dict[str, Any]]:
    return await db.integration_sync_runs.find_one({"businessId": business_id, "id": run_id}, {"_id": 0})
