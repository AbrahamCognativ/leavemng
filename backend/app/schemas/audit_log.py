from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any
from datetime import datetime

class AuditLogBase(BaseModel):
    user_id: UUID
    action: str
    resource_type: str
    resource_id: int
    timestamp: datetime
    extra_metadata : Optional[Any] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogRead(AuditLogBase):
    id: UUID

    model_config = {"from_attributes": True}
