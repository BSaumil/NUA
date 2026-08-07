from pydantic import BaseModel
from typing import Optional

class Discount(BaseModel):
    type: str  # percentage, fixed, custom
    value: float
    reason: Optional[str] = None

class DiscountCreate(BaseModel):
    type: str
    value: float
    reason: Optional[str] = None
