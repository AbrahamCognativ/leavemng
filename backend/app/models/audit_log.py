import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(
            as_uuid=True),
        ForeignKey("users.id"),
        nullable=False)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    # Nullable: can be None for system/global actions
    resource_id = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True))
    extra_metadata = Column(JSON, nullable=True)
