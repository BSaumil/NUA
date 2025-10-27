from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    role: str  # Admin, Cashier, Accountant
    locations: List[str] = []
    status: str = "active"

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    role: str
    locations: List[str] = []
