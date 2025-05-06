from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: EmailStr
    role_band: str
    role_title: str
    passport_or_id_number: str
    gender: str  # Required: 'male' or 'female'
    profile_image_url: Optional[str] = None
    manager_id: Optional[UUID] = None
    org_unit_id: Optional[UUID] = None
    extra_metadata : Optional[Any] = None

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
