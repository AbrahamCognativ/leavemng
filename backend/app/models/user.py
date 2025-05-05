import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role_band = Column(String, nullable=False)
    role_title = Column(String, nullable=False)
    passport_or_id_number = Column(String, unique=True, nullable=False)
    profile_image_url = Column(String, nullable=True)
    manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    org_unit_id = Column(UUID(as_uuid=True), ForeignKey("org_units.id"), nullable=True)
    extra_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column("is_active", default=True, nullable=False)

    manager = relationship("User", remote_side=[id], backref="direct_reports")
    org_unit = relationship("OrgUnit", back_populates="users")
