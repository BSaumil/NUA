"""
Actor / device / IP / tenant context — carried through the request lifecycle
via a `contextvars.ContextVar`, populated by a Starlette middleware and read
by `stamped_insert` / `stamped_update` when a route doesn't have the user
object directly in scope.

Design notes
────────────
• Never crashes if no context is set → helpers just skip stamping.
• Never overwrites an explicit `createdBy` passed by the caller.
• Auth is not required to enter the middleware — public routes still get
  device/IP/tenant, just no actor.
"""
from __future__ import annotations
from contextvars import ContextVar
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

_actor_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar("nua_actor_ctx", default=None)


def get_actor_context() -> Dict[str, Any]:
    """Read the actor context. Returns an empty dict when unset."""
    return _actor_ctx.get() or {}


def set_actor_context(ctx: Dict[str, Any]) -> None:
    _actor_ctx.set(ctx)


class ActorContextMiddleware(BaseHTTPMiddleware):
    """Populates the contextvar from request headers + JWT.

    Order matters: this runs BEFORE endpoint dependencies, so route handlers
    that call `stamped_insert(...)` without passing `user=` explicitly will
    still get the correct createdBy from the JWT.
    """

    async def dispatch(self, request, call_next):
        # Extract device + IP + tenant from headers
        device = request.headers.get("user-agent") or None
        client = request.client.host if request.client else None
        # X-Forwarded-For (Kubernetes ingress) takes precedence
        xff = request.headers.get("x-forwarded-for")
        ip = xff.split(",")[0].strip() if xff else client
        business_id = request.headers.get("x-tenant-id") or request.headers.get("x-business-id")
        location_id = request.headers.get("x-location-id")

        # Attempt to decode JWT quickly without triggering auth failures.
        # This is best-effort — protected routes still enforce auth normally.
        email = None
        role = None
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
            try:
                import jwt
                import os
                secret = os.environ.get("JWT_SECRET") or "nua-fallback-please-set-jwt-secret"
                data = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_exp": False})
                email = data.get("email") or data.get("sub")
                role = data.get("role")
            except Exception:
                pass  # Auth will handle its own error on the route

        ctx = {
            "email": email,
            "role": role,
            "device": (device[:200] if device else None),
            "ip": ip,
            "businessId": business_id,
            "locationId": location_id,
        }
        token = _actor_ctx.set(ctx)
        try:
            return await call_next(request)
        finally:
            _actor_ctx.reset(token)
