from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserRead, UserCreate
from app.models.user import User
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
    if (str(current_user.user_id) != str(user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
        and str(user.manager_id) != str(current_user.user_id)):
        from app.deps.permissions import log_permission_denied
        log_permission_denied(db, current_user.user_id, "get_user", "user", str(user_id))
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return UserRead.from_orm(user)

@router.put("/{user_id}", tags=["users"], response_model=UserRead)
def update_user(user_id: UUID, user_update: UserCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # IC can edit self, HR/Admin can edit any
    if (str(current_user.user_id) != str(user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")):
        from app.deps.permissions import log_permission_denied
        log_permission_denied(db, current_user.user_id, "update_user", "user", str(user_id))
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
    log_permission_denied(db, current_user.user_id, "update_user", "user", str(user_id))
    return UserRead.from_orm(user)
