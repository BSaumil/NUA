from pydantic import BaseModel, Field
from typing import Optional
import uuid

class Location(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    phone: str
    status: str = "active"

class LocationCreate(BaseModel):
    name: str
    address: str
    phone: str
