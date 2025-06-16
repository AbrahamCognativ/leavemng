import uuid
from sqlalchemy import Column, Numeric, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id"), nullable=False)
    balance_days = Column(Numeric, nullable=False)
    updated_at = Column(DateTime(timezone=True))

