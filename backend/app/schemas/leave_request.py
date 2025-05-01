from pydantic import BaseModel
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
    user_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    total_days: float
    status: LeaveStatusEnum
    applied_at: datetime
    decision_at: Optional[datetime] = None
    decided_by: Optional[UUID] = None
    comments: Optional[str] = None

class LeaveRequestCreate(LeaveRequestBase):
    pass

class LeaveRequestRead(LeaveRequestBase):
    id: UUID

    class Config:
        orm_mode = True
        from_attributes = True
