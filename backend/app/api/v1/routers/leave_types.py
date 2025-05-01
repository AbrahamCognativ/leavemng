from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.leave_type import LeaveType
from app.models.leave_policy import LeavePolicy
from app.db.session import get_db
from app.schemas.leave_type import LeaveTypeCreate, LeaveTypeRead
from app.schemas.leave_policy import LeavePolicyCreate, LeavePolicyRead
from typing import List

from app.deps.permissions import require_role

router = APIRouter()

@router.post("/types", response_model=LeaveTypeRead, tags=["leave-types"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def create_leave_type(leave_type: LeaveTypeCreate, db: Session = Depends(get_db)):
    db_leave_type = LeaveType(**leave_type.dict())
    db.add(db_leave_type)
    db.commit()
    db.refresh(db_leave_type)
    return db_leave_type

@router.get("/types", response_model=List[LeaveTypeRead], tags=["leave-types"], dependencies=[Depends(require_role(["HR", "Admin", "Manager", "IC"]))])
def list_leave_types(db: Session = Depends(get_db)):
    return db.query(LeaveType).all()

@router.put("/types/{leave_type_id}", response_model=LeaveTypeRead, tags=["leave-types"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def update_leave_type(leave_type_id: str, update: LeaveTypeCreate, db: Session = Depends(get_db)):
    leave_type = db.query(LeaveType).filter(LeaveType.id == leave_type_id).first()
    if not leave_type:
        raise HTTPException(status_code=404, detail="Leave type not found")
    for k, v in update.dict().items():
        setattr(leave_type, k, v)
    db.commit()
    db.refresh(leave_type)
    return leave_type

@router.post("/policies", response_model=LeavePolicyRead, tags=["leave-policies"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def create_leave_policy(policy: LeavePolicyCreate, db: Session = Depends(get_db)):
    db_policy = LeavePolicy(**policy.dict())
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy

@router.get("/policies", response_model=List[LeavePolicyRead], tags=["leave-policies"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def list_leave_policies(db: Session = Depends(get_db)):
    return db.query(LeavePolicy).all()

@router.put("/policies/{policy_id}", response_model=LeavePolicyRead, tags=["leave-policies"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def update_leave_policy(policy_id: str, update: LeavePolicyCreate, db: Session = Depends(get_db)):
    policy = db.query(LeavePolicy).filter(LeavePolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Leave policy not found")
    for k, v in update.dict().items():
        setattr(policy, k, v)
    db.commit()
    db.refresh(policy)
    return policy
