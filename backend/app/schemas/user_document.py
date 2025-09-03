from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class UserDocumentBase(BaseModel):
    name: str = Field(..., description="Document name/title")
    description: Optional[str] = Field(None, description="Optional document description")
    document_type: Optional[str] = Field(None, description="Document category (contract, certificate, etc.)")
    send_email_notification: bool = Field(True, description="Whether to send email notification to user")


class UserDocumentCreate(UserDocumentBase):
    user_id: uuid.UUID = Field(..., description="Target user ID")


class UserDocumentUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Document name/title")
    description: Optional[str] = Field(None, description="Document description")
    document_type: Optional[str] = Field(None, description="Document category")


class UserDocumentRead(UserDocumentBase):
    id: uuid.UUID
    user_id: uuid.UUID
    file_path: str
    file_name: str
    file_type: str
    file_size: Optional[str]
    email_sent_at: Optional[datetime]
    created_by: uuid.UUID
    updated_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool
    
    # Related data
    user_name: Optional[str] = Field(None, description="Target user's name")
    user_email: Optional[str] = Field(None, description="Target user's email")
    creator_name: Optional[str] = Field(None, description="Creator's name")
    updater_name: Optional[str] = Field(None, description="Updater's name")

    class Config:
        from_attributes = True


class UserDocumentListItem(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    file_name: str
    file_type: str
    file_size: Optional[str]
    document_type: Optional[str]
    user_id: uuid.UUID
    user_name: str
    user_email: str
    email_sent_at: Optional[datetime]
    created_by: uuid.UUID
    creator_name: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class MyDocumentListItem(BaseModel):
    """Schema for user's own documents list"""
    id: uuid.UUID
    name: str
    description: Optional[str]
    file_name: str
    file_type: str
    file_size: Optional[str]
    document_type: Optional[str]
    created_at: datetime
    creator_name: str

    class Config:
        from_attributes = True


class UserDocumentStats(BaseModel):
    """Statistics for user documents"""
    total_documents: int
    documents_by_type: dict
    recent_uploads: int  # Last 30 days
    total_users_with_documents: int

    class Config:
        from_attributes = True