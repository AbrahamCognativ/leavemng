from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.org_unit import OrgUnitRead, OrgUnitCreate
from app.models.org_unit import OrgUnit
from app.db.session import get_db
from uuid import UUID

router = APIRouter()

from app.deps.permissions import get_current_user, require_role

@router.get("/", tags=["org"], response_model=list[OrgUnitRead], dependencies=[Depends(require_role(["HR", "Admin"]))])
def list_org_units(db: Session = Depends(get_db)):
    units = db.query(OrgUnit).all()
    return [OrgUnitRead.model_validate(unit) for unit in units]

@router.post("/", tags=["org"], response_model=OrgUnitRead, dependencies=[Depends(require_role(["HR", "Admin"]))])
def create_org_unit(unit: OrgUnitCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db_unit = OrgUnit(**unit.model_dump())
    db.add(db_unit)
    try:
        db.commit()
        db.refresh(db_unit)
    except Exception as e:
        db.rollback()
        if hasattr(e, 'orig') and hasattr(e.orig, 'diag') and 'unique' in str(e.orig).lower():
            raise HTTPException(status_code=400, detail="Org unit with this name already exists")
        raise HTTPException(status_code=500, detail="Internal server error")
    from app.deps.permissions import log_permission_denied
    log_permission_denied(db, current_user.id, "create_org_unit", "org_unit", str(db_unit.id), message="Org unit creation failed or duplicate", http_status=400)
    return OrgUnitRead.model_validate(db_unit)

@router.get("/{unit_id}", tags=["org"], response_model=OrgUnitRead, dependencies=[Depends(require_role(["HR", "Admin"]))])
def get_org_unit(unit_id: UUID, db: Session = Depends(get_db)):
    unit = db.query(OrgUnit).filter(OrgUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Org unit not found")
    return OrgUnitRead.model_validate(unit)

@router.put("/{unit_id}", tags=["org"], response_model=OrgUnitRead, dependencies=[Depends(require_role(["HR", "Admin"]))])
def update_org_unit(unit_id: UUID, unit_update: OrgUnitCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    unit = db.query(OrgUnit).filter(OrgUnit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Org unit not found")
    for k, v in unit_update.model_dump().items():
        setattr(unit, k, v)
    try:
        db.commit()
        db.refresh(unit)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update org unit")
    from app.deps.permissions import log_permission_denied
    log_permission_denied(db, current_user.id, "update_org_unit", "org_unit", str(unit_id), message="Org unit update failed", http_status=500)
    return OrgUnitRead.model_validate(unit)
