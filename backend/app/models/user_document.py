import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class UserDocument(Base):
    __tablename__ = "user_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)  # Document title
    description = Column(Text, nullable=True)  # Optional description
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)  # Original filename
    file_type = Column(String, nullable=False)  # pdf, doc, docx
    file_size = Column(String, nullable=True)  # Human readable size
    
    # Target user
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    
    # Document category/type
    document_type = Column(String, nullable=True)  # "contract", "certificate", "handbook", etc.
    
    # Email notification settings
    send_email_notification = Column(Boolean, default=True, nullable=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # pylint: disable=not-callable
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # pylint: disable=not-callable
    
    # Soft delete
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="user_documents")
    creator = relationship("User", foreign_keys=[created_by], backref="created_user_documents")
    updater = relationship("User", foreign_keys=[updated_by], backref="updated_user_documents")