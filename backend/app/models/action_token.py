import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
import enum


class ActionTypeEnum(enum.Enum):
    wfh_approve = "wfh_approve"
    wfh_reject = "wfh_reject"
    leave_approve = "leave_approve"
    leave_reject = "leave_reject"


class ActionToken(Base):
    __tablename__ = "action_tokens"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_type = Column(String, nullable=False)  # "wfh_request" or "leave_request"
    resource_id = Column(PG_UUID(as_uuid=True), nullable=False)  # ID of the request
    approver_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    action_type = Column(Enum(ActionTypeEnum), nullable=False)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    approver = relationship("User")