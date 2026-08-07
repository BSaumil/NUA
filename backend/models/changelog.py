from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid


class ChangelogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    category: str = "feature"       # feature | improvement | fix | security
    area: str = "General"           # e.g. "Loyalty", "Marketing", "EFTPOS", "Audit"
    audience: str = "owner"         # owner | staff | guest — who actually sees the change
    status: str = "shipped"         # shipped | upcoming
    releasedAt: Optional[str] = None    # ISO date; None for upcoming entries
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
