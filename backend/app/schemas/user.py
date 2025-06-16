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
    is_active: Optional[bool] = True
    extra_metadata: Optional[Any] = None

class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """
    Standard user update schema. For first-time password reset via invite, use the /reset-password-invite endpoint.
    """
    name: Optional[str] = None
    role_band: Optional[str] = None
    role_title: Optional[str] = None
    passport_or_id_number: Optional[str] = None
    gender: Optional[str] = None
    profile_image_url: Optional[str] = None
    manager_id: Optional[UUID] = None
    org_unit_id: Optional[UUID] = None
    extra_metadata: Optional[Any] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    # email is intentionally omitted to prevent editing
