from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class LeaveBalanceBase(BaseModel):
    user_id: UUID
    leave_type_id: UUID
    balance_days: float

class LeaveBalanceCreate(LeaveBalanceBase):
    pass

class LeaveBalanceUpdate(BaseModel):
    balance_days: float

class LeaveBalanceRead(LeaveBalanceBase):
    id: UUID
    updated_at: datetime

    model_config = {"from_attributes": True}

