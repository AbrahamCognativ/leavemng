from pydantic import BaseModel, Field
from uuid import UUID
from datetime import date, datetime
from enum import Enum
from typing import Optional


class LeaveStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class LeaveRequestBase(BaseModel):
    leave_type_id: UUID
    start_date: date
    end_date: date
    comments: Optional[str] = None


class LeaveRequestCreate(LeaveRequestBase):
    total_days: float
    comments: str = Field(..., min_length=40, description="Comments must be at least 40 characters long")


class LeaveRequestUpdate(LeaveRequestBase):
    status: Optional[LeaveStatusEnum] = None
    applied_at: Optional[datetime] = None
    user_id: Optional[UUID] = None
    total_days: Optional[float] = None
    decision_at: Optional[datetime] = None
    decided_by: Optional[UUID] = None


class LeaveRequestPartialUpdate(BaseModel):
    comments: Optional[str] = Field(None, min_length=40, description="Comments must be at least 40 characters long")


class LeaveRequestRead(LeaveRequestBase):
    id: UUID
    status: LeaveStatusEnum
    applied_at: datetime
    total_days: float
    user_id: UUID
    decided_at: Optional[datetime] = None
    decision_at: Optional[datetime] = None
    decided_by: Optional[UUID] = None
    comments: Optional[str] = None

    model_config = {"from_attributes": True}
