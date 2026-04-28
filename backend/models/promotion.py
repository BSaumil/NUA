from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class Promotion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # bundle or category
    products: Optional[List[str]] = None
    category: Optional[str] = None
    originalPrice: Optional[float] = None
    discountedPrice: Optional[float] = None
    discount: float
    active: bool = True
    schedule: str = ""
    # Enhanced scheduling
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    activeDays: List[str] = []  # ["Monday","Tuesday",...]
    startTime: Optional[str] = None  # "11:00"
    endTime: Optional[str] = None    # "14:00"
    createdAt: datetime = Field(default_factory=datetime.utcnow)

class PromotionCreate(BaseModel):
    name: str
    type: str
    products: Optional[List[str]] = None
    category: Optional[str] = None
    originalPrice: Optional[float] = None
    discountedPrice: Optional[float] = None
    discount: float
    active: bool = True
    schedule: str = ""
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    activeDays: List[str] = []
    startTime: Optional[str] = None
    endTime: Optional[str] = None
