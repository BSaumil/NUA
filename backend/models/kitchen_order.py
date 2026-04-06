from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid


class KitchenOrderItem(BaseModel):
    productId: str = ""
    productName: str = ""
    quantity: int = 1
    modifiers: List[dict] = []
    notes: Optional[str] = None
    course: int = 1  # 1=starter, 2=main, 3=dessert
    status: str = "pending"  # pending, preparing, ready


class KitchenOrderCreate(BaseModel):
    transactionId: Optional[str] = None
    reservationId: Optional[str] = None
    tableNumber: Optional[str] = None
    orderType: str = "dine_in"  # dine_in, takeaway, delivery
    items: List[dict] = []
    notes: Optional[str] = None
    priority: str = "normal"  # normal, rush, vip
    serverId: Optional[str] = None


class KitchenOrder(BaseModel):
    id: str = ""
    transactionId: Optional[str] = None
    reservationId: Optional[str] = None
    tableNumber: Optional[str] = None
    orderType: str = "dine_in"
    items: List[dict] = []
    notes: Optional[str] = None
    priority: str = "normal"
    status: str = "new"  # new, preparing, ready, served, cancelled
    serverId: Optional[str] = None
    currentCourse: int = 1
    createdAt: str = ""
    startedAt: Optional[str] = None
    readyAt: Optional[str] = None
    servedAt: Optional[str] = None
    estimatedMinutes: int = 15

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = f"KO-{str(uuid.uuid4())[:8].upper()}"
        if not self.createdAt:
            self.createdAt = datetime.utcnow().isoformat()
