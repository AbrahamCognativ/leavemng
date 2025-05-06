from pydantic import BaseModel
from uuid import UUID
from enum import Enum

class LeaveCodeEnum(str, Enum):
    annual = "annual"
    sick = "sick"
    unpaid = "unpaid"
    compassionate = "compassionate"
    maternity = "maternity"
    paternity = "paternity"
    custom = "custom"
    

class LeaveTypeBase(BaseModel):
    code: LeaveCodeEnum
    description: str
    default_allocation_days: int
    custom_code: str | None = None

class LeaveTypeCreate(LeaveTypeBase):
    pass

class LeaveTypeRead(LeaveTypeBase):
    id: UUID

    model_config = {"from_attributes": True}
