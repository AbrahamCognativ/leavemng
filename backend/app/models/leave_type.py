import uuid
from sqlalchemy import Column, String, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum

class LeaveCodeEnum(enum.Enum):
    annual = "annual"
    sick = "sick"
    unpaid = "unpaid"
    # Add more as needed

class LeaveType(Base):
    __tablename__ = "leave_types"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(Enum(LeaveCodeEnum), nullable=False)
    description = Column(String, nullable=False)
    default_allocation_days = Column(Integer, nullable=False)
