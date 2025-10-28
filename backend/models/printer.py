from pydantic import BaseModel, Field
from typing import Optional
import uuid

class PrinterConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # network, usb, bluetooth
    ipAddress: Optional[str] = None
    port: int = 9100
    paperWidth: int = 80  # mm
    autoprint: bool = False
    location: str
    status: str = "active"

class PrinterConfigCreate(BaseModel):
    name: str
    type: str
    ipAddress: Optional[str] = None
    port: int = 9100
    paperWidth: int = 80
    autoprint: bool = False
    location: str
