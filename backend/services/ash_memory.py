"""
Ash Memory — long-term, structured, retrievable knowledge store.

Two collections back this:
  • ash_memories       — atomic facts / preferences / patterns Ash has learned
  • ash_memory_summary — periodic rollups (weekly, monthly) for cheap recall

Every memory has:
  • kind         — preference | pattern | fact | note
  • scope        — global | customer:<id> | staff:<id> | product:<id> | supplier:<id> | date
  • text         — human-readable statement
  • confidence   — 0-1 (learned facts start at 0.6, explicitly stated at 1.0)
  • source       — chat | agent | scheduler | owner
  • usageCount   — incremented on retrieval (helps decay unused)
  • createdAt / updatedAt / lastUsedAt

Design constraints
──────────────────
• Never store PII beyond what's already in the customer record.
• Retrieval is scope-first, kind-second, then most-recent, then highest confidence.
• `remember(text, scope, kind)` is the single write path.
• `recall(scope, limit)` returns compact list for LLM context injection.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from database import db
import logging
import uuid

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


VALID_KINDS = ("preference", "pattern", "fact", "note")


async def remember(
    text: str,
    *,
    scope: str = "global",
    kind: str = "fact",
    confidence: float = 0.6,
    source: str = "agent",
    tags: Optional[List[str]] = None,
    actor: Optional[str] = None,
) -> Dict[str, Any]:
    """Store a memory. Idempotent-ish: exact same (scope, text) upserts."""
    if kind not in VALID_KINDS:
        kind = "note"
    now = _now()
    existing = await db.ash_memories.find_one({"scope": scope, "text": text}, {"_id": 0})
    if existing:
        # Reinforce: bump confidence toward 1.0 and update timestamp
        new_conf = min(1.0, float(existing.get("confidence", 0.6)) + 0.1)
        await db.ash_memories.update_one(
            {"id": existing["id"]},
            {"$set": {"confidence": new_conf, "updatedAt": now, "kind": kind,
                        "tags": tags or existing.get("tags", []),
                        "source": source},
             "$inc": {"usageCount": 1}},
        )
        return {**existing, "confidence": new_conf, "reinforced": True}

    doc = {
        "id": str(uuid.uuid4()),
        "scope": scope,
        "kind": kind,
        "text": text[:600],
        "confidence": max(0.0, min(1.0, confidence)),
        "source": source,
        "tags": tags or [],
        "actor": actor,
        "usageCount": 0,
        "createdAt": now,
        "updatedAt": now,
        "lastUsedAt": now,
    }
    await db.ash_memories.insert_one(dict(doc))
    return doc


async def recall(scope: str = "global", *, limit: int = 15,
                  kind: Optional[str] = None, min_confidence: float = 0.3) -> List[Dict[str, Any]]:
    """Retrieve memories relevant to a scope, most recent + high-confidence first."""
    q: Dict[str, Any] = {"scope": scope, "confidence": {"$gte": min_confidence}}
    if kind:
        q["kind"] = kind
    rows = await db.ash_memories.find(q, {"_id": 0})\
        .sort([("confidence", -1), ("updatedAt", -1)])\
        .limit(limit).to_list(limit)
    # Mark as used
    if rows:
        ids = [r["id"] for r in rows]
        await db.ash_memories.update_many(
            {"id": {"$in": ids}},
            {"$set": {"lastUsedAt": _now()}, "$inc": {"usageCount": 1}},
        )
    return rows


async def forget(memory_id: str, *, actor: Optional[str] = None) -> bool:
    r = await db.ash_memories.delete_one({"id": memory_id})
    return r.deleted_count > 0


async def list_memories(scope: Optional[str] = None, kind: Optional[str] = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {}
    if scope: q["scope"] = scope
    if kind: q["kind"] = kind
    return await db.ash_memories.find(q, {"_id": 0})\
        .sort([("updatedAt", -1)]).limit(limit).to_list(limit)


async def scope_counts() -> Dict[str, int]:
    """Quick summary for the UI."""
    pipe = [
        {"$group": {"_id": "$scope", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 30},
    ]
    rows = await db.ash_memories.aggregate(pipe).to_list(30)
    return {r["_id"]: r["count"] for r in rows}


async def context_pack(scope: str = "global") -> str:
    """Format memories as a compact string suitable for LLM system prompts."""
    memories = await recall(scope, limit=10)
    if not memories:
        return ""
    lines = [f"- [{m['kind']} @ conf {round(m['confidence'], 2)}] {m['text']}" for m in memories]
    return "Ash long-term memory (scope=" + scope + "):\n" + "\n".join(lines)
