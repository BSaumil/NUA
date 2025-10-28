from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    color: str = "#6366f1"
    icon: Optional[str] = None
    sortOrder: int = 0
    active: bool = True
    createdAt: datetime = Field(default_factory=datetime.utcnow)

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#6366f1"
    icon: Optional[str] = None
    sortOrder: int = 0
