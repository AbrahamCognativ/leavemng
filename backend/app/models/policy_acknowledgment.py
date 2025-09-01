import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class PolicyAcknowledgment(Base):
    __tablename__ = "policy_acknowledgments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Policy and User relationship
    policy_id = Column(
        UUID(as_uuid=True),
        ForeignKey("policies.id"),
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    
    # Acknowledgment details
    acknowledged_at = Column(DateTime(timezone=True), server_default=func.now())  # pylint: disable=not-callable
    ip_address = Column(String, nullable=True)  # For audit trail
    user_agent = Column(Text, nullable=True)    # For audit trail
    
    # Digital signature info (for future electronic signing)
    signature_data = Column(Text, nullable=True)  # JSON string for signature details
    signature_method = Column(String, default="click_acknowledgment")  # click_acknowledgment, digital_signature, etc.
    
    # Notification tracking
    notification_sent_at = Column(DateTime(timezone=True), nullable=True)
    notification_read_at = Column(DateTime(timezone=True), nullable=True)
    reminder_count = Column(String, default="0")  # Track how many reminders sent
    
    # Status tracking
    is_acknowledged = Column(Boolean, default=True, nullable=False)
    acknowledgment_deadline = Column(DateTime(timezone=True), nullable=True)  # 5 days from notification
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # pylint: disable=not-callable
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # pylint: disable=not-callable
    
    # Relationships
    policy = relationship("Policy", backref="acknowledgments")
    user = relationship("User", backref="policy_acknowledgments")
    
    # Unique constraint to prevent duplicate acknowledgments
    __table_args__ = (
        {'extend_existing': True}
    )