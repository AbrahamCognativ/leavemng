from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

class OrgUnitBase(BaseModel):
    name: str
    parent_unit_id: Optional[UUID] = None

class OrgUnitCreate(OrgUnitBase):
    pass

class OrgUnitRead(OrgUnitBase):
    id: UUID
    children: Optional[List['OrgUnitRead']] = None

    class Config:
        orm_mode = True
        from_attributes = True
