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
    categoryId: Optional[str] = None
    price: float
    cost: float
    stock: int
    sku: str
    image: str
    gstRate: float = 10.0
    modifiers: List[ProductModifier] = []
    # IDs of modifiers (from /api/modifiers) attached to this product.
    # A product can have multiple modifiers.
    modifierIds: List[str] = []
    # Enhanced fields
    locations: List[str] = ["Main"]
    onlineChannels: List[str] = []  # uber_eats, doordash, website, etc.
    seoDescription: str = ""
    description: str = ""
    # 86 (out-of-stock) flag set by /api/v25/products/{id}/86
    active: bool = True
    eightySixed: bool = False
    eightySixedAt: Optional[datetime] = None
    eightySixedBy: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

class ProductCreate(BaseModel):
    name: str
    category: str
    categoryId: Optional[str] = None
    price: float
    cost: float
    stock: int
    sku: str
    image: Optional[str] = ""
    gstRate: float = 10.0
    modifiers: List[ProductModifier] = []
    modifierIds: List[str] = []
    locations: List[str] = ["Main"]
    onlineChannels: List[str] = []
    seoDescription: str = ""
    description: str = ""

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    categoryId: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    stock: Optional[int] = None
    sku: Optional[str] = None
    image: Optional[str] = None
    gstRate: Optional[float] = None
    modifiers: Optional[List[ProductModifier]] = None
    modifierIds: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    onlineChannels: Optional[List[str]] = None
    seoDescription: Optional[str] = None
    description: Optional[str] = None
