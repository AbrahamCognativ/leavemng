import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PolicyAcknowledmentBase(BaseModel):
    policy_id: uuid.UUID
    user_id: uuid.UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    signature_method: str = "click_acknowledgment"


class PolicyAcknowledmentCreate(PolicyAcknowledmentBase):
    signature_data: Optional[str] = None


class PolicyAcknowledmentUpdate(BaseModel):
    signature_data: Optional[str] = None
    signature_method: Optional[str] = None
    notification_read_at: Optional[datetime] = None


class PolicyAcknowledmentRead(PolicyAcknowledmentBase):
    id: uuid.UUID
    acknowledged_at: datetime
    signature_data: Optional[str] = None
    notification_sent_at: Optional[datetime] = None
    notification_read_at: Optional[datetime] = None
    reminder_count: str
    is_acknowledged: bool
    acknowledgment_deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Related data
    policy_name: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    model_config = {"from_attributes": True}


class PolicyAcknowledmentListItem(BaseModel):
    id: uuid.UUID
    policy_id: uuid.UUID
    user_id: uuid.UUID
    policy_name: str
    user_name: str
    user_email: str
    acknowledged_at: datetime
    signature_method: str
    acknowledgment_deadline: Optional[datetime] = None
    is_acknowledged: bool
    notification_sent_at: Optional[datetime] = None
    reminder_count: str

    model_config = {"from_attributes": True}


class PolicyNotificationRequest(BaseModel):
    policy_id: uuid.UUID
    user_ids: Optional[list[uuid.UUID]] = None  # If None, notify all users
    deadline_days: int = 5


class PolicyAcknowledmentStats(BaseModel):
    policy_id: uuid.UUID
    policy_name: str
    total_users: int
    acknowledged_count: int
    pending_count: int
    overdue_count: int
    acknowledgment_rate: float
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPolicyStatus(BaseModel):
    policy_id: uuid.UUID
    policy_name: str
    policy_description: Optional[str] = None
    file_name: str
    file_type: str
    created_at: datetime
    acknowledgment_deadline: Optional[datetime] = None
    is_acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    notification_sent_at: Optional[datetime] = None
    is_overdue: bool
    days_remaining: Optional[int] = None

    model_config = {"from_attributes": True}