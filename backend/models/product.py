from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid

class ModifierOption(BaseModel):
    id: str
    name: str
    price: float = 0.0

class ProductModifier(BaseModel):
    id: str
    name: str
    type: str
    required: bool = False
    options: List[ModifierOption]

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    price: float
    cost: float
    stock: int
    sku: str
    image: str
    gstRate: float = 10.0
    modifiers: List[ProductModifier] = []
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    category: str
    price: float
    cost: float
    stock: int
    sku: str
    image: str
    gstRate: float = 10.0

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    stock: Optional[int] = None
    sku: Optional[str] = None
    image: Optional[str] = None
    gstRate: Optional[float] = None
