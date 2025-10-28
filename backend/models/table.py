from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

class Table(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    number: int
    name: str
    capacity: int
    location: str
    area: str  # "Indoor", "Outdoor", "Private"
    status: str = "available"  # available, occupied, reserved
    currentOrderId: Optional[str] = None

class TableCreate(BaseModel):
    number: int
    name: str
    capacity: int
    location: str
    area: str

class DineInOrder(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tableId: str
    tableNumber: int
    items: list
    status: str = "pending"  # pending, preparing, ready, served
    orderTime: datetime = Field(default_factory=datetime.utcnow)
    serverName: str
    notes: Optional[str] = None
