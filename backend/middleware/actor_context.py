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


def tenant_scope_filter(business_id: Optional[str] = None) -> Dict[str, Any]:
    """A Mongo filter clause that scopes a query to one business, WITHOUT
    ever hiding data that predates tenant stamping.

    Pass the caller's businessId explicitly (from `user.get("businessId")`)
    when you have it in scope, or omit it to read from the actor context.
    Matches documents tagged for this business, plus any document that has
    no businessId at all (missing field or null) — the untagged case is the
    normal state for every document written before the tenant-stamping fix,
    and for collections `routes/multi_tenant.py`'s `/business/backfill-tenant`
    hasn't been pointed at yet. Once a business's data is fully backfilled
    there's nothing left to match the untagged branch, so this quietly
    becomes a strict filter with no further code change needed.

    Returns {} (no-op — matches everything) when no businessId is known at
    all, e.g. an old token issued before businessId was embedded in it. An
    empty filter is the safe default: never hide data because the *signal*
    for whose data it is happens to be missing.
    """
    biz = business_id or get_actor_context().get("businessId")
    if not biz:
        return {}
    return {"$or": [{"businessId": biz}, {"businessId": None}, {"businessId": {"$exists": False}}]}


def tenant_owns(doc_business_id: Optional[str], business_id: Optional[str] = None) -> bool:
    """Single-resource counterpart to tenant_scope_filter() — for a GET-by-id
    route that fetches one document (a customer's wallet, their loyalty
    ledger) rather than a list. Same safe defaults: an unknown caller
    businessId or an untagged document both mean "allow", so this only ever
    starts rejecting once both sides of the comparison are real values that
    actually disagree."""
    biz = business_id or get_actor_context().get("businessId")
    if not biz or not doc_business_id:
        return True
    return doc_business_id == biz


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
        header_business_id = request.headers.get("x-tenant-id") or request.headers.get("x-business-id")
        location_id = request.headers.get("x-location-id")

        # Attempt to decode JWT quickly without triggering auth failures.
        # This is best-effort — protected routes still enforce auth normally.
        email = None
        role = None
        jwt_business_id = None
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
            try:
                import jwt
                import os
                secret = os.environ["JWT_SECRET"]
                data = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_exp": False})
                email = data.get("email") or data.get("sub")
                role = data.get("role")
                jwt_business_id = data.get("businessId")
            except Exception:
                pass  # Auth will handle its own error on the route

        # Authenticated JWT membership is authoritative — a logged-in staff
        # member's own businessId always wins, full stop. The header used to
        # win whenever present, which meant any logged-in user of Business A
        # could send X-Business-Id: <business-B-id> and have writes/reads
        # tagged/scoped as Business B (confirmed exploitable via
        # commerce_v29.py's voucher and wallet-ledger writes, which read this
        # contextvar for tenant tagging). There's currently no per-user
        # multi-business membership list in this codebase (each auth_users
        # doc carries exactly one businessId), so "a business the actor is
        # authorised to access" is that single value — nothing else to
        # select among yet. If/when real multi-business membership exists,
        # this is where a header would validate against that membership set
        # rather than being trusted outright.
        #
        # The header still matters for the case it was originally built for:
        # a partner/integration caller with no bearer token at all (no JWT
        # to derive a businessId from).
        business_id = jwt_business_id or header_business_id

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
