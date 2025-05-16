from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.leave_type import LeaveType
from app.models.leave_policy import LeavePolicy
from app.db.session import get_db
from app.schemas.leave_type import LeaveTypeCreate, LeaveTypeRead
from app.schemas.leave_policy import LeavePolicyCreate, LeavePolicyRead
from typing import List
import datetime

from app.deps.permissions import require_role

from app.models.leave_type import LeaveType, LeaveCodeEnum

router = APIRouter()

@router.post("/", response_model=LeaveTypeRead, tags=["leave-types"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def create_leave_type(leave_type: LeaveTypeCreate, db: Session = Depends(get_db)):
    if leave_type.code in [
        LeaveCodeEnum.annual,
        LeaveCodeEnum.sick,
        LeaveCodeEnum.compassionate,
        LeaveCodeEnum.unpaid,
        LeaveCodeEnum.maternity,
        LeaveCodeEnum.paternity
    ]:
        if db.query(LeaveType).filter(LeaveType.code == leave_type.code).first():
            raise HTTPException(status_code=400, detail="Leave type already exists")
        leave_type.custom_code = None
    db_leave_type = LeaveType(**leave_type.model_dump())
    db.add(db_leave_type)
    db.commit()
    db.refresh(db_leave_type)

    # Create LeaveBalance for all active users
    from app.models.user import User
    from app.models.leave_balance import LeaveBalance
    active_users = db.query(User).filter(User.is_active == True).all()
    for user in active_users:
        # Avoid duplicate balances
        exists = db.query(LeaveBalance).filter(LeaveBalance.user_id == user.id, LeaveBalance.leave_type_id == db_leave_type.id).first()
        if not exists and (
            db_leave_type.code != LeaveCodeEnum.maternity or user.gender != "male"
        ) and (
            db_leave_type.code != LeaveCodeEnum.paternity or user.gender != "female"
        ):
            balance = LeaveBalance(
                user_id=user.id,
                leave_type_id=db_leave_type.id,
                balance_days=db_leave_type.default_allocation_days,
                updated_at=datetime.datetime.now(datetime.timezone.utc)
            )
            db.add(balance)
    db.commit()
    return db_leave_type

@router.get("/", response_model=List[LeaveTypeRead], tags=["leave-types"], dependencies=[])
def list_leave_types(db: Session = Depends(get_db)):
    return db.query(LeaveType).all()

@router.put("/{leave_type_id}", response_model=LeaveTypeRead, tags=["leave-types"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def update_leave_type(leave_type_id: str, update: LeaveTypeCreate, db: Session = Depends(get_db)):
    leave_type = db.query(LeaveType).filter(LeaveType.id == leave_type_id).first()
    if not leave_type:
        raise HTTPException(status_code=404, detail="Leave type not found")

    if leave_type.code != LeaveCodeEnum.annual and update.default_allocation_days != leave_type.default_allocation_days:
        balances_to_update = db.query(LeaveBalance).filter(
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.balance_days == leave_type.default_allocation_days
        ).all()
        for balance in balances_to_update:
            balance.balance_days = update.default_allocation_days

    for k, v in update.model_dump().items():
        setattr(leave_type, k, v)
    leave_type.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(leave_type)
    return leave_type

