from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserRead, UserCreate
from app.models.user import User
from app.models.leave_balance import LeaveBalance
from app.models.leave_type import LeaveType
from app.models.leave_request import LeaveRequest
from app.db.session import get_db
from uuid import UUID

router = APIRouter()

from app.deps.permissions import get_current_user, require_role

@router.get("/", tags=["users"], response_model=list[UserRead], dependencies=[Depends(require_role(["HR", "Admin"]))])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [UserRead.from_orm(user) for user in users]

@router.post("/", tags=["users"], response_model=UserRead, dependencies=[Depends(require_role(["HR", "Admin"]))])
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(**user.dict(exclude={"password"}), hashed_password=user.password)
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
    return UserRead.from_orm(db_user)

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
    return UserRead.from_orm(user)

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
    gender = None
    if hasattr(user, 'extra_metadata') and user.extra_metadata:
        import json
        try:
            meta = json.loads(user.extra_metadata)
            gender = meta.get('gender')
        except Exception:
            pass
    for bal in balances:
        code = leave_types.get(bal.leave_type_id)
        # Eligibility check
        if code == 'maternity' and gender != 'female':
            continue
        if code == 'paternity' and gender != 'male':
            continue
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

@router.put("/{user_id}", tags=["users"], response_model=UserRead)
def update_user(user_id: UUID, user_update: UserCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
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
    for k, v in user_update.dict(exclude={"password"}).items():
        setattr(user, k, v)
    user.hashed_password = user_update.password  # In real app, hash this
    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update user")
    # Audit: log user update
    from app.deps.permissions import log_permission_denied
    log_permission_denied(db, current_user.id, "update_user", "user", str(user_id))
    return UserRead.from_orm(user)
