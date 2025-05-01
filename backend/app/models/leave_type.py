import uuid
from sqlalchemy import Column, String, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum

class LeaveCodeEnum(enum.Enum):
    annual = "annual"
    sick = "sick"
    unpaid = "unpaid"
    compassionate = "compassionate"
    maternity = "maternity"
    paternity = "paternity"
    custom = "custom"
    # Add more as needed

"""
Leave Types Example:
- annual: 21 days/year, accrued monthly (1.75/month)
- compassionate: one-time, as per policy
- maternity: 3 months (90 days), one-time per event, only for women
- paternity: 2 weeks (14 days), yearly, only for men
"""

class LeaveType(Base):
    __tablename__ = "leave_types"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(Enum(LeaveCodeEnum), nullable=False)
    description = Column(String, nullable=False)
    default_allocation_days = Column(Integer, nullable=False)
    custom_code = Column(String, nullable=True)
