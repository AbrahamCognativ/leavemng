from app.deps.permissions import get_current_user, require_role
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserRead, UserCreate, UserUpdate
from app.utils.password import hash_password
from app.models.user import User
from app.models.leave_balance import LeaveBalance
from app.models.leave_type import LeaveType
from app.models.leave_request import LeaveRequest
from app.db.session import get_db
from uuid import UUID

router = APIRouter()


@router.delete("/{user_id}", tags=["users"], status_code=204,
               dependencies=[Depends(require_role(["HR", "Admin"]))])
def delete_user(user_id: UUID, db: Session = Depends(get_db),
                current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return None


@router.patch("/{user_id}/softdelete",
              tags=["users"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def soft_delete_user(
        user_id: UUID,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400,
                            detail="User is already inactive (soft-deleted)")
    user.is_active = False
    db.commit()
    return {"detail": f"User {user.email} soft-deleted (marked as inactive)."}


@router.get("/", tags=["users"], response_model=list[UserRead],
            dependencies=[Depends(require_role(["Manager", "HR", "Admin"]))])
def list_users(db: Session = Depends(get_db),
               current_user=Depends(get_current_user)):
    """
    HR/Admin: See all users.
    Manager: See only users whose manager_id == current_user.id.
    """
    if current_user.role_band in (
        "HR",
        "Admin") or current_user.role_title in (
        "HR",
            "Admin"):
        users = db.query(User).all()
    else:
        users = db.query(User).filter(User.manager_id == current_user.id).all()
    return [UserRead.model_validate(user) for user in users]


@router.post("/", tags=["users"], response_model=UserRead,
             dependencies=[Depends(require_role(["HR", "Admin"]))])
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(
        **user.model_dump(exclude={"password"}), hashed_password=hash_password(user.password))
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except Exception as e:
        db.rollback()
        if hasattr(
            e, 'orig') and hasattr(
            e.orig, 'diag') and 'unique' in str(
                e.orig).lower():
            raise HTTPException(status_code=400,
                                detail="passport_or_id_number already exists")
        raise HTTPException(status_code=500, detail="Internal server error")

    # --- AUTO-CREATE LEAVE BALANCES FOR ELIGIBLE LEAVE TYPES ---
    from datetime import datetime, timezone
    leave_types = db.query(LeaveType).all()
    eligible_leave_types = []
    gender = getattr(db_user, 'gender', None)
    for lt in leave_types:
        code = lt.code.value if hasattr(lt.code, 'value') else str(lt.code)
        if code == "maternity" and gender != "female":
            continue
        if code == "paternity" and gender != "male":
            continue
        eligible_leave_types.append(lt)
    for lt in eligible_leave_types:
        balance = LeaveBalance(
            user_id=db_user.id,
            leave_type_id=lt.id,
            balance_days=lt.default_allocation_days,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(balance)
    db.commit()

    # Audit: log user creation
    from app.deps.permissions import log_permission_denied
    log_permission_denied(db, db_user.id, "create_user", "user", db_user.id)
    return UserRead.model_validate(db_user)


@router.get("/{user_id}", tags=["users"], response_model=UserRead)
def get_user(user_id: UUID, db: Session = Depends(get_db),
             current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # IC can view self, Manager can view direct reports, HR/Admin can view any
    if (str(current_user.id) != str(user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
            and str(user.manager_id) != str(current_user.id)):
        from app.deps.permissions import log_permission_denied
        log_permission_denied(db, current_user.id, "get_user", "user", str(
            user_id), message="Insufficient permissions to view user", http_status=403)
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return UserRead.model_validate(user)


@router.get("/{user_id}/leave", tags=["users"])
def get_user_leave(
        user_id: UUID,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Permissions: IC can view self, Manager can view direct, HR/Admin can
    # view all
    if (
        current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
        and user.id != current_user.id
        and (user.manager_id != current_user.id)
    ):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Get leave types for reference
    leave_types_query = db.query(LeaveType).all()
    leave_types = {lt.id: lt.code.value if hasattr(lt.code, 'value') else str(
        lt.code) for lt in leave_types_query} if leave_types_query else {}

    # Get leave balances from database
    balances = db.query(LeaveBalance).filter(
        LeaveBalance.user_id == user.id).all()
    leave_balance = {}
    for bal in balances:
        leave_type_obj = db.query(LeaveType).filter(
            LeaveType.id == bal.leave_type_id).first()
        if leave_type_obj:
            code = leave_type_obj.code.value if hasattr(
                leave_type_obj.code, 'value') else str(
                leave_type_obj.code)
            if code == 'custom':
                custom_code = getattr(leave_type_obj, 'custom_code', None)
                leave_balance[custom_code or 'custom'] = float(
                    bal.balance_days)
            else:
                leave_balance[code] = float(bal.balance_days)

    # Get leave requests
    try:
        requests = db.query(LeaveRequest).filter(
            LeaveRequest.user_id == user.id).all()
        leave_requests = []

        for r in requests:
            try:
                leave_requests.append({
                    'id': str(r.id),
                    'leave_type': leave_types.get(r.leave_type_id),
                    'start_date': r.start_date,
                    'end_date': r.end_date,
                    'total_days': float(r.total_days) if r.total_days is not None else 0.0,
                    'status': r.status.value if hasattr(r.status, 'value') else str(r.status),
                    'applied_at': r.applied_at,
                    'decision_at': r.decision_at,
                    'decided_by': str(r.decided_by) if r.decided_by else None,
                    'comments': r.comments
                })
            except Exception as e:
                logger.error(f"Error processing leave request: {str(e)}")
                # Continue with next request if one fails
                continue
    except Exception as e:
        leave_requests = []
        logger.error(f"Error fetching leave requests: {str(e)}")

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
            {'leave_type': code, 'balance_days': int(days) if float(days).is_integer() else float(days)}
            for code, days in leave_balance.items()
        ],
        'leave_request': leave_requests
    }
    return resp


@router.patch("/{user_id}", tags=["users"], response_model=UserRead)
def update_user(
        user_id: UUID,
        user_update: UserUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # IC can edit self, HR/Admin can edit any
    if (str(current_user.id) != str(user_id)
        and current_user.role_band not in ("HR", "Admin")
            and current_user.role_title not in ("HR", "Admin")):
        from app.deps.permissions import log_permission_denied
        log_permission_denied(
            db,
            current_user.id,
            "update_user",
            "user",
            str(user_id))
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
    # Audit: log user update with proper audit logging
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="update_user",
        resource_type="user",
        resource_id=str(user_id),
        metadata={
            "updated_fields": list(update_data.keys()),
            "updated_by": current_user.email,
            "self_update": str(current_user.id) == str(user_id)
        }
    )
    return UserRead.model_validate(user)
