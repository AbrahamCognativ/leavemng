from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class LeaveBalanceBase(BaseModel):
    user_id: UUID
    leave_type_id: UUID
    balance_days: float

class LeaveBalanceCreate(LeaveBalanceBase):
    pass

class LeaveBalanceRead(LeaveBalanceBase):
    id: UUID
    updated_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True
