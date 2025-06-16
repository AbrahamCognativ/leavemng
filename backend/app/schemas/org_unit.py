from pydantic import BaseModel
from typing import Optional, List, Dict
from uuid import UUID

class OrgUnitBase(BaseModel):
    name: str
    parent_unit_id: Optional[UUID] = None

class OrgUnitCreate(OrgUnitBase):
    pass

class OrgUnitRead(OrgUnitBase):
    id: UUID
    children: Optional[List['OrgUnitRead']] = None

    model_config = {"from_attributes": True}

class ManagerInfo(BaseModel):
    id: UUID
    name: str
    email: str
    role_title: str

class OrgUnitTree(OrgUnitBase):
    id: UUID
    managers: List[ManagerInfo]
    children: List['OrgUnitTree']

    model_config = {"from_attributes": True}

