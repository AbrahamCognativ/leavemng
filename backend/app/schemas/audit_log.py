from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, Any, List
from datetime import datetime

class AuditLogBase(BaseModel):
    user_id: UUID
    action: str
    resource_type: str
    resource_id: str  # Changed from UUID to str to handle non-UUID resource IDs
    timestamp: Optional[datetime] = None  # Made optional to handle NULL values in database
    extra_metadata: Optional[Any] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLogRead(AuditLogBase):
    id: UUID
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    resource_name: Optional[str] = None
    resource_details: Optional[dict] = None

    model_config = {"from_attributes": True}

class AuditLogResponse(BaseModel):
    data: AuditLogRead

class AuditLogListResponse(BaseModel):
    data: List[AuditLogRead]
    total: int
    skip: int
    limit: int
