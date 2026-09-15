"""Per-business scoping for the `db.settings` singleton-document pattern
used all over this codebase: `{"key": "<name>", "value": {...}}`, one
document per settings type, shared by every business on the deployment.

Found during the Trust Release pre-merge risk closure: 19+ distinct
settings keys (booking rules, email config, print routing, surcharge/
gratuity config, receipt config, POS session, wallet offers, 2FA policy,
custom roles, business theme, POS layout, training mode, auto-report
config, today's targets, trust settings, venue subscription, and more)
were all read/written with a bare `{"key": "..."}` filter — no
`businessId` anywhere — so every business on a shared deployment reads
and writes the exact same document. Business A changing its print
routing changes Business B's too.

Same safe-default philosophy as `middleware.actor_context.tenant_scope_filter`
used everywhere else in this codebase: a business that has never set its
own copy of a setting falls back to the legacy untagged document (so
existing single-business deployments and pre-migration data keep working
unchanged) rather than seeing nothing. The FIRST business to write its
own value for a key gets its own tagged document from then on; every
other business keeps reading the shared untagged one until it, too,
writes its own — exactly how `tenant_scope_filter`'s "missing businessId
= visible to everyone, until this document gets tagged" default already
works for every other collection in this codebase.

One deliberate exception, NOT migrated to this helper: `ash_kill_switch`
(services/nua_tools.py) stays a genuine platform-wide singleton — an
emergency stop is not a per-tenant setting, this was an explicit
architectural decision recorded in TENANT_ISOLATION_REMAINING_WORK.md
before this pass, not an oversight.
"""
from __future__ import annotations
from typing import Any, Optional

from database import db
from middleware.actor_context import get_actor_context


async def get_setting(key: str, business_id: Optional[str] = None) -> Optional[Any]:
    """This business's own value for `key` if it has ever set one, else the
    legacy untagged document, else None. Mirrors tenant_scope_filter's own
    "missing/None businessId matches everyone" default."""
    biz = business_id or get_actor_context().get("businessId")
    if biz:
        own = await db.settings.find_one({"key": key, "businessId": biz}, {"_id": 0})
        if own is not None:
            return own.get("value")
    legacy = await db.settings.find_one(
        {"key": key, "businessId": {"$exists": False}}, {"_id": 0}
    )
    return legacy.get("value") if legacy is not None else None


async def set_setting(key: str, value: Any, business_id: Optional[str] = None) -> None:
    """Writes THIS business's own copy — never the shared legacy document,
    even if that's what this business happened to be reading before its
    first write. Two businesses editing the same key can never collide
    once both have written at least once."""
    biz = business_id or get_actor_context().get("businessId")
    await db.settings.update_one(
        {"key": key, "businessId": biz},
        {"$set": {"key": key, "businessId": biz, "value": value}},
        upsert=True,
    )


async def get_scoped_singleton(collection, match: dict, business_id: Optional[str] = None) -> Optional[dict]:
    """Same pattern as get_setting, generalized to any single-conceptual-
    document collection keyed by something other than `key` (e.g.
    `db.loyalty_config`'s `{"id": "default"}`, `db.agent_autonomy`'s same
    shape). `match` identifies the singleton's own key fields, unrelated
    to which business owns which copy of it."""
    biz = business_id or get_actor_context().get("businessId")
    if biz:
        own = await collection.find_one({**match, "businessId": biz}, {"_id": 0})
        if own is not None:
            return own
    legacy = await collection.find_one({**match, "businessId": {"$exists": False}}, {"_id": 0})
    return legacy


async def set_scoped_singleton(collection, match: dict, doc: dict, business_id: Optional[str] = None) -> None:
    biz = business_id or get_actor_context().get("businessId")
    await collection.update_one(
        {**match, "businessId": biz},
        {"$set": {**doc, **match, "businessId": biz}},
        upsert=True,
    )
