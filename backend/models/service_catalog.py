from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid


class ServiceCreate(BaseModel):
    name: str
    category: str = ""
    durationMinutes: int = 30
    price: float = 0.0
    # Which staff (auth_users ids) can perform this service — an empty list
    # means "anyone," matching how a small salon actually works before an
    # owner bothers assigning specialties.
    staffIds: List[str] = []
    description: str = ""


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    durationMinutes: Optional[int] = None
    price: Optional[float] = None
    staffIds: Optional[List[str]] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class Service(BaseModel):
    id: str = Field(default_factory=lambda: f"SVC-{str(uuid.uuid4())[:8].upper()}")
    name: str
    category: str = ""
    durationMinutes: int = 30
    price: float = 0.0
    staffIds: List[str] = []
    description: str = ""
    active: bool = True
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
    businessId: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        now = datetime.utcnow().isoformat()
        if not self.createdAt:
            self.createdAt = now
        if not self.updatedAt:
            self.updatedAt = now
