"""
Universal entity mixins for every top-level object in NUA.

Any new model should inherit `BaseEntity` (or `LocationEntity`). Existing
models are stamped opportunistically on the next update through the
`stamped_update` helper — we do NOT run a big-bang migration.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditFields(BaseModel):
    """The audit/history block every stamped entity carries."""
    createdBy: Optional[str] = None
    createdAt: str = Field(default_factory=_now_iso)
    updatedBy: Optional[str] = None
    updatedAt: str = Field(default_factory=_now_iso)
    deletedAt: Optional[str] = None
    deletedBy: Optional[str] = None
    device: Optional[str] = None
    ip: Optional[str] = None
    version: int = 1


class BaseEntity(AuditFields):
    """Universal identity + tenant + audit."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    businessId: Optional[str] = None


class LocationEntity(BaseEntity):
    """Same as BaseEntity but tagged with a physical outlet."""
    locationId: Optional[str] = None
