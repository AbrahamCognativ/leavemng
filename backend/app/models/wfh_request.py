import uuid
from sqlalchemy import Column, ForeignKey, Date, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum


class WFHStatusEnum(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class WFHRequest(Base):
    __tablename__ = "wfh_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(
        Enum(WFHStatusEnum),
        nullable=False,
        default=WFHStatusEnum.pending
    )
    reason = Column(Text, nullable=True)
    applied_at = Column(DateTime(timezone=True))
    decision_at = Column(DateTime(timezone=True), nullable=True)
    decided_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    comments = Column(Text, nullable=True)
    approval_note = Column(Text, nullable=True)