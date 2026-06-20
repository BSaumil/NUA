"""
Shared FastAPI dependencies — auth + role checks.

These are top-level dependencies so the auth check fires BEFORE Pydantic
body validation. That means anonymous POST callers get 401/403 instead of
the schema getting leaked back as a 422.
"""
from fastapi import Depends, HTTPException, Request


async def get_user(request: Request) -> dict:
    """Resolve the current user or raise 401."""
    from routes.auth import get_current_user
    return await get_current_user(request)


async def require_owner_or_manager(user: dict = Depends(get_user)) -> dict:
    if user.get("role") not in ("owner", "manager"):
        raise HTTPException(status_code=403, detail="Owner/Manager only")
    return user


async def require_owner(user: dict = Depends(get_user)) -> dict:
    if user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Owner only")
    return user
