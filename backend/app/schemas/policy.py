import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PolicyBase(BaseModel):
    name: str
    description: Optional[str] = None
    org_unit_id: Optional[uuid.UUID] = None


class PolicyCreate(PolicyBase):
    pass


class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    org_unit_id: Optional[uuid.UUID] = None


class PolicyRead(PolicyBase):
    id: uuid.UUID
    file_path: str
    file_name: str
    file_type: str
    file_size: Optional[str] = None
    created_by: uuid.UUID
    updated_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    
    # Related data
    org_unit_name: Optional[str] = None
    creator_name: Optional[str] = None
    updater_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PolicyListItem(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    file_name: str
    file_type: str
    file_size: Optional[str] = None
    org_unit_name: Optional[str] = None
    creator_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}