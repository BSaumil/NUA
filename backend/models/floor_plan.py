from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid


class FloorTable(BaseModel):
    id: str = ""
    number: str = ""
    capacity: int = 4
    shape: str = "rectangle"  # rectangle, circle, square
    x: float = 0
    y: float = 0
    width: float = 80
    height: float = 60
    rotation: float = 0
    section: str = "main"
    status: str = "available"  # available, occupied, reserved, cleaning
    currentOrderId: Optional[str] = None
    currentReservationId: Optional[str] = None
    serverId: Optional[str] = None
    minCovers: int = 1
    maxCovers: int = 4
    isActive: bool = True

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = f"TBL-{str(uuid.uuid4())[:8].upper()}"


class FloorSection(BaseModel):
    id: str = ""
    name: str = "Main"
    color: str = "#3B82F6"
    serverId: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = f"SEC-{str(uuid.uuid4())[:8].upper()}"


class FloorPlanCreate(BaseModel):
    name: str = "Main Floor"
    locationId: Optional[str] = None
    tables: List[dict] = []
    sections: List[dict] = []
    width: int = 1000
    height: int = 600
    isActive: bool = True


class FloorPlanUpdate(BaseModel):
    name: Optional[str] = None
    tables: Optional[List[dict]] = None
    sections: Optional[List[dict]] = None
    width: Optional[int] = None
    height: Optional[int] = None
    isActive: Optional[bool] = None


class FloorPlan(BaseModel):
    id: str = ""
    name: str = "Main Floor"
    locationId: Optional[str] = None
    tables: List[dict] = []
    sections: List[dict] = []
    width: int = 1000
    height: int = 600
    isActive: bool = True
    createdAt: str = ""
    updatedAt: str = ""

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = f"FP-{str(uuid.uuid4())[:8].upper()}"
        now = datetime.utcnow().isoformat()
        if not self.createdAt:
            self.createdAt = now
        if not self.updatedAt:
            self.updatedAt = now
