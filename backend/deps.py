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


def require_permission(perm_id: str):
    """Gate an endpoint on the same granular permission catalog Settings >
    Permissions already manages. Owner always passes. Anyone else needs
    `perm_id` in their effective permissions — custom override, else the
    owner's saved default for their role, else the code-level default.
    Mirrors the frontend's AuthContext.hasPermission(), so what a staff
    member can *see* in the UI and what the API actually *allows* agree."""
    async def checker(user: dict = Depends(get_user)) -> dict:
        if user.get("role") == "owner":
            return user
        from routes.auth import effective_permissions
        perms = await effective_permissions(user)
        if "*" in perms or perm_id in perms:
            return user
        raise HTTPException(
            status_code=403,
            detail=f"You don't have access to this yet — ask the owner to grant '{perm_id}' access in Settings > Permissions",
        )
    return checker
