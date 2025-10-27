from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class Promotion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # bundle or category
    products: Optional[List[str]] = None  # for bundle type
    category: Optional[str] = None  # for category type
    originalPrice: Optional[float] = None
    discountedPrice: Optional[float] = None
    discount: float
    active: bool = True
    schedule: str
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
    schedule: str
