from pydantic import BaseModel, Field
from typing import Optional
import uuid

class PrinterConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    businessId: Optional[str] = None
    name: str
    type: str  # network, usb, bluetooth
    ipAddress: Optional[str] = None
    port: int = 9100
    paperWidth: int = 80  # mm
    autoprint: bool = False
    location: str
    status: str = "active"
    # Ticket footer — split by order source since a kitchen line likes a
    # bare ticket while a customer-facing receipt for an online order needs
    # the footer's contact/return info. Padding adds blank feed lines before
    # the cut so the paper clears the cutter on printers with a short throat.
    footerInPerson: bool = True
    footerOnline: bool = True
    paddingLines: int = 3

class PrinterConfigCreate(BaseModel):
    name: str
    type: str
    ipAddress: Optional[str] = None
    port: int = 9100
    paperWidth: int = 80
    autoprint: bool = False
    location: str
    footerInPerson: bool = True
    footerOnline: bool = True
    paddingLines: int = 3
