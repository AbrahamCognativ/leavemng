import uuid
from sqlalchemy import Column, Numeric, ForeignKey, Date, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum


class LeaveStatusEnum(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(
            as_uuid=True),
        ForeignKey("users.id"),
        nullable=False)
    leave_type_id = Column(
        UUID(
            as_uuid=True),
        ForeignKey("leave_types.id"),
        nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_days = Column(Numeric, nullable=False)
    status = Column(
        Enum(LeaveStatusEnum),
        nullable=False,
        default=LeaveStatusEnum.pending)
    applied_at = Column(DateTime(timezone=True))
    decision_at = Column(DateTime(timezone=True), nullable=True)
    decided_by = Column(
        UUID(
            as_uuid=True),
        ForeignKey("users.id"),
        nullable=True)
    comments = Column(Text, nullable=True)
    approval_note = Column(Text, nullable=True)
