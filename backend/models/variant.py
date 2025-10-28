from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

class ProductVariant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # e.g., "Small Red"
    sku: str
    price: float
    cost: float
    stock: int
    attributes: dict  # {"size": "Small", "color": "Red"}

class ProductWithVariants(BaseModel):
    id: str
    name: str
    category: str
    basePrice: float
    baseCost: float
    hasVariants: bool = False
    variants: List[ProductVariant] = []
    variantAttributes: List[str] = []  # ["size", "color"]
