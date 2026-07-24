"""
Live-sync layer for the Owner Dashboard app — a plain FastAPI WebSocket, not
a third-party realtime vendor. The whole stack is already self-hosted (own
Mongo, own auth), so pushing sale/roster/alert events through a native
socket authenticated with the same JWT avoids adding a new vendor, a new AU
data-residency question, and duplicated auth logic for something this small.

This is a "nice to have instantly" layer, never the source of truth — every
client that uses it (see frontend/src/hooks/useLiveFeed.js) keeps its normal
polling running underneath. A dropped socket (regional connectivity, a proxy
that blocks WS upgrades) just means events arrive a little later via the
next poll instead of instantly; nothing breaks.
"""
from __future__ import annotations
from typing import Any, Dict, Set
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

# No multi-tenant partitioning yet (this deployment model is one business per
# backend) — a single in-memory set is enough. If/when multi-tenant lands,
# key this dict by tenant id the same way the rate limiter does.
_connections: Set[WebSocket] = set()


async def register(ws: WebSocket) -> None:
    _connections.add(ws)


def unregister(ws: WebSocket) -> None:
    _connections.discard(ws)


async def broadcast(event: Dict[str, Any]) -> None:
    """Best-effort fan-out. Never let a dead/slow socket affect the caller —
    this is called inline after a sale/roster write, not queued."""
    dead = []
    for ws in list(_connections):
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.discard(ws)


def connection_count() -> int:
    return len(_connections)
