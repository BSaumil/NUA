from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class IntakeNoteCreate(BaseModel):
    customerName: str
    customerPhone: Optional[str] = None
    customerId: Optional[str] = None
    allergies: str = ""
    skinType: str = ""
    notes: str = ""       # consultation notes — what was discussed/done this visit
    appointmentId: Optional[str] = None  # the visit this note was taken during, if any


class IntakeNote(BaseModel):
    id: str = Field(default_factory=lambda: f"INT-{str(uuid.uuid4())[:8].upper()}")
    customerName: str
    customerPhone: Optional[str] = None
    customerId: Optional[str] = None
    allergies: str = ""
    skinType: str = ""
    notes: str = ""
    appointmentId: Optional[str] = None
    staffId: Optional[str] = None
    staffName: str = ""
    createdAt: Optional[str] = None
    businessId: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.createdAt:
            self.createdAt = datetime.utcnow().isoformat()
