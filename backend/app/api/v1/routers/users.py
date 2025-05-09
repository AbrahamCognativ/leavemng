from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserRead, UserCreate
from app.utils.password import hash_password
from app.models.user import User
from app.models.leave_balance import LeaveBalance
from app.models.leave_type import LeaveType
from app.models.leave_request import LeaveRequest
from app.db.session import get_db
from uuid import UUID

router = APIRouter()

from app.deps.permissions import get_current_user, require_role

@router.delete("/{user_id}", tags=["users"], status_code=204, dependencies=[Depends(require_role(["HR", "Admin"]))])
def delete_user(user_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return None

@router.patch("/{user_id}/softdelete", tags=["users"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def soft_delete_user(user_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is already inactive (soft-deleted)")
    user.is_active = False
    db.commit()
    return {"detail": f"User {user.email} soft-deleted (marked as inactive)."}

@router.get("/", tags=["users"], response_model=list[UserRead], dependencies=[Depends(require_role(["Manager", "HR", "Admin"]))])
def list_users(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    HR/Admin: See all users.
    Manager: See only users whose manager_id == current_user.id.
    """
    if current_user.role_band in ("HR", "Admin") or current_user.role_title in ("HR", "Admin"):
        users = db.query(User).all()
    else:
        users = db.query(User).filter(User.manager_id == current_user.id).all()
    return [UserRead.model_validate(user) for user in users]

@router.post("/", tags=["users"], response_model=UserRead, dependencies=[Depends(require_role(["HR", "Admin"]))])
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(**user.model_dump(exclude={"password"}), hashed_password=hash_password(user.password))
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except Exception as e:
        db.rollback()
        if hasattr(e, 'orig') and hasattr(e.orig, 'diag') and 'unique' in str(e.orig).lower():
            raise HTTPException(status_code=400, detail="passport_or_id_number already exists")
        raise HTTPException(status_code=500, detail="Internal server error")
    # Audit: log user creation
    from app.deps.permissions import log_permission_denied
    log_permission_denied(db, db_user.id, "create_user", "user", db_user.id)
    return UserRead.model_validate(db_user)

@router.get("/{user_id}", tags=["users"], response_model=UserRead)
def get_user(user_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # IC can view self, Manager can view direct reports, HR/Admin can view any
    if (str(current_user.id) != str(user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
        and str(user.manager_id) != str(current_user.id)):
        from app.deps.permissions import log_permission_denied
        log_permission_denied(db, current_user.id, "get_user", "user", str(user_id), message="Insufficient permissions to view user", http_status=403)
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return UserRead.model_validate(user)

@router.get("/{user_id}/leave", tags=["users"])
def get_user_leave(user_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Permissions: IC can view self, Manager can view direct, HR/Admin can view all
    if (
        current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
        and user.id != current_user.id
        and (user.manager_id != current_user.id)
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    # Get leave balances
    balances = db.query(LeaveBalance).filter(LeaveBalance.user_id == user.id).all()
    leave_types = {lt.id: lt.code.value for lt in db.query(LeaveType).all()}
    leave_balance = {}
    gender = getattr(user, 'gender', None)
    from datetime import date, timedelta
    leave_balance = {}
    today = date.today()
    join_date = user.created_at.date() if hasattr(user.created_at, 'date') else user.created_at
    accrual_year_start = join_date.replace(year=today.year)
    if accrual_year_start > today:
        accrual_year_start = join_date.replace(year=today.year-1)
    accrual_year_end = accrual_year_start.replace(year=accrual_year_start.year+1)
    # Gather all leave requests for calculations
    all_requests = db.query(LeaveRequest).filter(LeaveRequest.user_id == user.id, LeaveRequest.status == 'approved').all()
    # Annual leave
    if 'annual' in leave_types.values():
        taken = [r for r in all_requests if leave_types.get(r.leave_type_id) == 'annual' and accrual_year_start <= r.start_date < accrual_year_end]
        entitlement = 19
        carry_forward = 5
        # Carry forward logic: if previous year balance > 5, only 5 carried
        # For simplicity, assume balance is up-to-date in DB
        taken_days = sum(r.total_days for r in taken)
        leave_balance['annual'] = max(entitlement - taken_days, 0)
    # Sick leave
    if 'sick' in leave_types.values():
        taken = [r for r in all_requests if leave_types.get(r.leave_type_id) == 'sick' and accrual_year_start <= r.start_date < accrual_year_end]
        SICK_FULL_DAYS = 30
        SICK_HALF_DAYS = 15
        SICK_TOTAL = SICK_FULL_DAYS + SICK_HALF_DAYS * 0.5
        taken_days = sum(r.total_days for r in taken)
        leave_balance['sick'] = max(SICK_TOTAL - taken_days, 0)
    # Paternity
    if 'paternity' in leave_types.values() and gender == 'male':
        PATERNITY_DAYS = 14
        taken = [r for r in all_requests if leave_types.get(r.leave_type_id) == 'paternity' and accrual_year_start <= r.start_date < accrual_year_end]
        taken_days = sum(r.total_days for r in taken)
        leave_balance['paternity'] = max(PATERNITY_DAYS - taken_days, 0)
    # Maternity
    if 'maternity' in leave_types.values() and gender == 'female':
        MATERNITY_DAYS = 90
        taken = [r for r in all_requests if leave_types.get(r.leave_type_id) == 'maternity' and accrual_year_start <= r.start_date < accrual_year_end]
        taken_days = sum(r.total_days for r in taken)
        leave_balance['maternity'] = max(MATERNITY_DAYS - taken_days, 0)
    # Compassionate leave: 10 days per quarter
    if 'compassionate' in leave_types.values():
        quarter = (today.month - 1) // 3 + 1
        quarter_start = date(today.year, 3 * (quarter - 1) + 1, 1)
        if quarter == 4:
            quarter_end = date(today.year, 12, 31)
        else:
            quarter_end = date(today.year, 3 * quarter + 1, 1) - timedelta(days=1)
        taken = [r for r in all_requests if leave_types.get(r.leave_type_id) == 'compassionate' and quarter_start <= r.start_date <= quarter_end]
        taken_days = sum(r.total_days for r in taken)
        leave_balance['compassionate'] = max(10 - taken_days, 0)
    # Add any static leave types from balances
    for bal in balances:
        code = leave_types.get(bal.leave_type_id)
        if code not in leave_balance:
            leave_balance[code] = float(bal.balance_days)
    # Get leave requests
    requests = db.query(LeaveRequest).filter(LeaveRequest.user_id == user.id).all()
    leave_request = [
        {
            'id': str(r.id),
            'leave_type': leave_types.get(r.leave_type_id),
            'start_date': r.start_date,
            'end_date': r.end_date,
            'total_days': float(r.total_days),
            'status': r.status.value,
            'applied_at': r.applied_at,
            'decision_at': r.decision_at,
            'decided_by': str(r.decided_by) if r.decided_by else None,
            'comments': r.comments
        }
        for r in requests
    ]
    # Compose response
    resp = {
        'name': user.name,
        'email': user.email,
        'role_band': user.role_band,
        'role_title': user.role_title,
        'passport_or_id_number': getattr(user, 'passport_or_id_number', None),
        'profile_image_url': getattr(user, 'profile_image_url', None),
        'manager_id': str(user.manager_id) if user.manager_id else None,
        'org_unit_id': str(user.org_unit_id) if user.org_unit_id else None,
        'extra_metadata': user.extra_metadata,
        'id': str(user.id),
        'created_at': user.created_at,
        'leave_balance': [
    {'leave_type': code, 'balance_days': int(-(-days//1))} for code, days in leave_balance.items()
],
        'leave_request': leave_request
    }
    return resp

from app.schemas.user import UserUpdate

@router.put("/{user_id}", tags=["users"], response_model=UserRead)
def update_user(user_id: UUID, user_update: UserUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # IC can edit self, HR/Admin can edit any
    if (str(current_user.id) != str(user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")):
        from app.deps.permissions import log_permission_denied
        log_permission_denied(db, current_user.id, "update_user", "user", str(user_id))
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    update_data = user_update.model_dump(exclude_unset=True)
    if 'email' in update_data:
        raise HTTPException(status_code=400, detail="Email cannot be updated.")
    for k, v in update_data.items():
        if k == "password":
            user.hashed_password = hash_password(v)
        else:
            setattr(user, k, v)
    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update user")
    # Audit: log user update
    from app.deps.permissions import log_permission_denied
    log_permission_denied(db, current_user.id, "update_user", "user", str(user_id))
    return UserRead.model_validate(user)
