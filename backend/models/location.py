from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import uuid


class Location(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    address: str
    phone: str
    status: str = "active"
    # Extended profile fields (v27.7): richer store profile for public listings,
    # web, Google My Business sync, and multi-region ops.
    email: Optional[str] = None
    website: Optional[str] = None
    logoUrl: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    # Opening hours per weekday (0=Mon .. 6=Sun). Each entry: {open: str, close: str, closed: bool}
    hours: Optional[Dict[str, Dict]] = None
    # Google My Business integration
    gmbPlaceId: Optional[str] = None
    gmbSyncEnabled: bool = False
    gmbLastSyncAt: Optional[str] = None
    tags: Optional[List[str]] = None


class LocationCreate(BaseModel):
    name: str
    address: str
    phone: str
    email: Optional[str] = None
    website: Optional[str] = None
    logoUrl: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    hours: Optional[Dict[str, Dict]] = None
    gmbPlaceId: Optional[str] = None
    gmbSyncEnabled: bool = False
    tags: Optional[List[str]] = None
