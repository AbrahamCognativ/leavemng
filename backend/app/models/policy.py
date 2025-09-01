import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Policy(Base):
    __tablename__ = "policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, doc, ppt, etc.
    file_size = Column(String, nullable=True)  # Store as string for display
    
    # Organization relationship
    org_unit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("org_units.id"),
        nullable=True  # Null means applies to all org units
    )
    
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
    org_unit = relationship("OrgUnit", backref="policies")
    creator = relationship("User", foreign_keys=[created_by], backref="created_policies")
    updater = relationship("User", foreign_keys=[updated_by], backref="updated_policies")