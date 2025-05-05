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
    leave_type_id: UUID
    start_date: date
    end_date: date
    comments: Optional[str] = None

class LeaveRequestCreate(LeaveRequestBase):
    pass

class LeaveRequestRead(LeaveRequestBase):
    id: UUID
    status: LeaveStatusEnum
    applied_at: datetime
    total_days: float
    decided_at: Optional[datetime] = None
    decided_by: Optional[UUID] = None
    comments: Optional[str] = None

    model_config = {"from_attributes": True}
