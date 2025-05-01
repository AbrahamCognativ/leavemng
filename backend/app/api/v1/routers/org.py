from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.org_unit import OrgUnitRead, OrgUnitCreate
from app.models.org_unit import OrgUnit
from app.db.session import get_db
from uuid import UUID

router = APIRouter()

@router.get("/", response_model=list[OrgUnitRead])
def list_org_units(db: Session = Depends(get_db)):
    units = db.query(OrgUnit).all()
    return [OrgUnitRead.from_orm(unit) for unit in units]

@router.post("/", response_model=OrgUnitRead)
def create_org_unit(unit: OrgUnitCreate, db: Session = Depends(get_db)):
    db_unit = OrgUnit(**unit.dict())
    db.add(db_unit)
    try:
        db.commit()
        db.refresh(db_unit)
    except Exception as e:
        db.rollback()
        if hasattr(e, 'orig') and hasattr(e.orig, 'diag') and 'unique' in str(e.orig).lower():
            raise HTTPException(status_code=400, detail="Org unit with this name already exists")
        raise HTTPException(status_code=500, detail="Internal server error")
    return OrgUnitRead.from_orm(db_unit)

@router.get("/{unit_id}", response_model=OrgUnitRead)
def get_org_unit(unit_id: UUID, db: Session = Depends(get_db)):
    unit = db.query(OrgUnit).filter(OrgUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Org unit not found")
    return OrgUnitRead.from_orm(unit)

@router.put("/{unit_id}", response_model=OrgUnitRead)
def update_org_unit(unit_id: UUID, unit_update: OrgUnitCreate, db: Session = Depends(get_db)):
    unit = db.query(OrgUnit).filter(OrgUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Org unit not found")
    for k, v in unit_update.dict().items():
        setattr(unit, k, v)
    try:
        db.commit()
        db.refresh(unit)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update org unit")
    return OrgUnitRead.from_orm(unit)
