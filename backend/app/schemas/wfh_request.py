from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime
from enum import Enum
from typing import Optional


class WFHStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class WFHRequestBase(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = None


class WFHRequestCreate(WFHRequestBase):
    pass


class WFHRequestUpdate(WFHRequestBase):
    status: Optional[WFHStatusEnum] = None
    applied_at: Optional[datetime] = None
    user_id: Optional[UUID] = None
    decision_at: Optional[datetime] = None
    decided_by: Optional[UUID] = None
    comments: Optional[str] = None


class WFHRequestPartialUpdate(BaseModel):
    reason: Optional[str] = None
    comments: Optional[str] = None


class WFHRequestRead(WFHRequestBase):
    id: UUID
    user_id: UUID
    status: WFHStatusEnum
    applied_at: Optional[datetime] = None
    decision_at: Optional[datetime] = None
    decided_by: Optional[UUID] = None
    comments: Optional[str] = None
    approver_name: Optional[str] = None  # Add approver name field
    working_days: Optional[int] = None  # Add working days field
    employee_name: Optional[str] = None  # Add employee name field
    employee_email: Optional[str] = None  # Add employee email field

    model_config = {"from_attributes": True}