from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.leave_policy import LeavePolicy, AccrualFrequencyEnum
from app.schemas.leave_policy import LeavePolicyCreate, LeavePolicyRead
from typing import List
import uuid
from app.deps.permissions import require_role
from app.models.leave_type import LeaveType

router = APIRouter()

@router.post("/", response_model=LeavePolicyRead, tags=["leave-policy"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def create_leave_policy(policy: LeavePolicyCreate, db: Session = Depends(get_db)):
    # Ensure leave_type_id exists
    leave_type = db.query(LeaveType).filter(LeaveType.id == policy.leave_type_id).first()
    if not leave_type:
        raise HTTPException(status_code=400, detail="leave_type_id does not exist")
    db_policy = LeavePolicy(**policy.model_dump())
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy

@router.get("/", response_model=List[LeavePolicyRead], tags=["leave-policy"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def list_leave_policies(db: Session = Depends(get_db)):
    return db.query(LeavePolicy).all()

@router.get("/{policy_id}", response_model=LeavePolicyRead, tags=["leave-policy"])
def get_leave_policy(policy_id: uuid.UUID, db: Session = Depends(get_db)):
    policy = db.query(LeavePolicy).filter(LeavePolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy
