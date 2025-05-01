from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.leave_policy import LeavePolicy, AccrualFrequencyEnum
from app.schemas.leave_policy import LeavePolicyCreate, LeavePolicyRead
from typing import List
import uuid

router = APIRouter()

@router.post("/", response_model=LeavePolicyRead, tags=["leave-policy"])
def create_leave_policy(policy: LeavePolicyCreate, db: Session = Depends(get_db)):
    db_policy = LeavePolicy(**policy.dict())
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy

@router.get("/", response_model=List[LeavePolicyRead], tags=["leave-policy"])
def list_leave_policies(db: Session = Depends(get_db)):
    return db.query(LeavePolicy).all()

@router.get("/{policy_id}", response_model=LeavePolicyRead, tags=["leave-policy"])
def get_leave_policy(policy_id: uuid.UUID, db: Session = Depends(get_db)):
    policy = db.query(LeavePolicy).filter(LeavePolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy
