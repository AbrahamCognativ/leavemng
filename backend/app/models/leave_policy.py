import uuid
from sqlalchemy import Column, Numeric, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum

class AccrualFrequencyEnum(enum.Enum):
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"
    one_time = "one_time"

class LeavePolicy(Base):
    __tablename__ = "leave_policies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_unit_id = Column(UUID(as_uuid=True), ForeignKey("org_units.id"), nullable=False)
    leave_type_id = Column(UUID(as_uuid=True), ForeignKey("leave_types.id"), nullable=False)
    allocation_days_per_year = Column(Numeric, nullable=False)
    accrual_frequency = Column(Enum(AccrualFrequencyEnum), nullable=False)
    accrual_amount_per_period = Column(Numeric, nullable=True)

