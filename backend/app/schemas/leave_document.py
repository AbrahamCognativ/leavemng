from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class LeaveDocumentBase(BaseModel):
    request_id: UUID
    file_path: str
    file_name: str
    uploaded_at: datetime

class LeaveDocumentCreate(LeaveDocumentBase):
    pass

class LeaveDocumentRead(LeaveDocumentBase):
    id: UUID

    class Config:
        orm_mode = True
        from_attributes = True
