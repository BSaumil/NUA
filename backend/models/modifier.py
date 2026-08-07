from pydantic import BaseModel, Field
from typing import List
import uuid

class ModifierOption(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: float = 0.0

class Modifier(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # e.g., "Size", "Add-ons", "Temperature"
    type: str  # single, multiple
    required: bool = False
    options: List[ModifierOption]

class ModifierCreate(BaseModel):
    name: str
    type: str
    required: bool = False
    options: List[ModifierOption]
