"""Webhook delivery, NUA -> partner. Fire-and-forget from the request path;
deliveries land in an outbox and a background worker pushes them with retries,
so a partner's slow endpoint never slows a booking down."""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

from database import db

logger = logging.getLogger("bookings.webhooks")

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = [2, 8, 30]

# Test hook: when set (by the test suite), deliveries are appended here
# instead of leaving the process over HTTP.
CAPTURE: Optional[list] = None


async def emit(partner: dict, event: str, payload: dict) -> None:
    doc = {
        "id": f"WHK-{uuid.uuid4().hex[:10].upper()}",
        "partner_id": partner["id"],
        "url": partner.get("webhook_url"),
        "event": event,
        "payload": payload,
        "status": "pending",
        "attempts": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.webhook_outbox.insert_one(dict(doc))
    if CAPTURE is not None:
        CAPTURE.append({"event": event, "payload": payload, "partner_id": partner["id"]})
        await db.webhook_outbox.update_one({"id": doc["id"]}, {"$set": {"status": "delivered"}})
        return
    if not doc["url"]:
        await db.webhook_outbox.update_one({"id": doc["id"]}, {"$set": {"status": "skipped_no_url"}})
        return
    asyncio.create_task(_deliver(doc))


async def _deliver(doc: dict) -> None:
    for attempt in range(MAX_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(doc["url"], json={
                    "id": doc["id"], "event": doc["event"], "created_at": doc["created_at"],
                    "data": doc["payload"],
                })
            if 200 <= r.status_code < 300:
                await db.webhook_outbox.update_one(
                    {"id": doc["id"]},
                    {"$set": {"status": "delivered", "attempts": attempt + 1}},
                )
                return
            logger.warning("webhook %s attempt %d got HTTP %s", doc["id"], attempt + 1, r.status_code)
        except Exception as exc:  # network errors — retry
            logger.warning("webhook %s attempt %d failed: %s", doc["id"], attempt + 1, exc)
        if attempt < MAX_ATTEMPTS - 1:
            await asyncio.sleep(BACKOFF_SECONDS[attempt])
    await db.webhook_outbox.update_one(
        {"id": doc["id"]},
        {"$set": {"status": "failed", "attempts": MAX_ATTEMPTS}},
    )
