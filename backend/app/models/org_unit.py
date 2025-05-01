import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class OrgUnit(Base):
    __tablename__ = "org_units"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    parent_unit_id = Column(UUID(as_uuid=True), ForeignKey("org_units.id"), nullable=True)

    parent = relationship("OrgUnit", remote_side=[id], backref="children")
    users = relationship("User", back_populates="org_unit")
