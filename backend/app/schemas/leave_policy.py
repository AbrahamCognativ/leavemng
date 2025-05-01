import uuid
from enum import Enum
from pydantic import BaseModel
from typing import Optional

class AccrualFrequencyEnum(str, Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"
    one_time = "one_time"

class LeavePolicyBase(BaseModel):
    org_unit_id: uuid.UUID
    leave_type_id: uuid.UUID
    allocation_days_per_year: float
    accrual_frequency: AccrualFrequencyEnum
    accrual_amount_per_period: Optional[float]

class LeavePolicyCreate(LeavePolicyBase):
    pass

class LeavePolicyRead(LeavePolicyBase):
    id: uuid.UUID

    class Config:
        orm_mode = True
