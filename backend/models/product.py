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
    # Enhanced fields
    locations: List[str] = ["Main"]
    onlineChannels: List[str] = []  # uber_eats, doordash, website, etc.
    seoDescription: str = ""
    description: str = ""
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
    modifiers: List[ProductModifier] = []
    locations: List[str] = ["Main"]
    onlineChannels: List[str] = []
    seoDescription: str = ""
    description: str = ""

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    stock: Optional[int] = None
    sku: Optional[str] = None
    image: Optional[str] = None
    gstRate: Optional[float] = None
    modifiers: Optional[List[ProductModifier]] = None
    locations: Optional[List[str]] = None
    onlineChannels: Optional[List[str]] = None
    seoDescription: Optional[str] = None
    description: Optional[str] = None
