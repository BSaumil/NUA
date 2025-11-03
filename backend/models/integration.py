from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class Integration(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # quickbooks, xero, shopify, etc.
    displayName: str
    enabled: bool = False
    apiKey: Optional[str] = None
    apiSecret: Optional[str] = None
    config: Dict[str, Any] = {}
    lastSync: Optional[datetime] = None
    status: str = "inactive"  # inactive, active, error
    errorMessage: Optional[str] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)

class IntegrationCreate(BaseModel):
    name: str
    displayName: str
    enabled: bool = False
    apiKey: Optional[str] = None
    apiSecret: Optional[str] = None
    config: Dict[str, Any] = {}

class IntegrationUpdate(BaseModel):
    enabled: Optional[bool] = None
    apiKey: Optional[str] = None
    apiSecret: Optional[str] = None
    config: Optional[Dict[str, Any]] = None

class SyncRequest(BaseModel):
    integrationName: str
    dataType: str  # sales, inventory, customer, order
    data: Dict[str, Any]
