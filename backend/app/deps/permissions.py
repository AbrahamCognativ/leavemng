from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from typing import List, Optional
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRead
from sqlalchemy.orm import Session
import os

SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class UserInToken(UserRead):
    role_band: str
    role_title: str
    org_unit_id: Optional[str]
    manager_id: Optional[str]


# 1. Extract current user from JWT

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInToken:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authentication credentials")
    try:
        return UserInToken(**payload)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed user claims")

# 2. Role-based permission dependency

def require_role(allowed_bands: List[str] = None, allowed_titles: List[str] = None):
    def verifier(current: UserInToken = Depends(get_current_user), db: Session = Depends(get_db)):
        if allowed_bands and current.role_band not in allowed_bands:
            log_permission_denied(db, current.id, "require_role", "", "00000000-0000-0000-0000-000000000000", message="Insufficient band permissions", http_status=403)
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient band permissions")
        if allowed_titles and current.role_title not in allowed_titles:
            log_permission_denied(db, current.id, "require_role", "", "00000000-0000-0000-0000-000000000000", message="Insufficient title permissions", http_status=403)
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient title permissions")
        return current
    return verifier

# 3. Hierarchy-based permission dependency

def require_direct_manager(request_user_id: str, db: Session = Depends(get_db), current: UserInToken = Depends(get_current_user)):
    # HR and Admin always pass
    if current.role_band in ("HR", "Admin"):
        return current
    target = db.query(User).filter(User.id == request_user_id).first()
    if not target or str(target.manager_id) != str(current.id):
        log_permission_denied(db, current.id, "require_direct_manager", "user", request_user_id, message="Only the reporting manager (or HR/Admin) may perform this action", http_status=403)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the reporting manager (or HR/Admin) may perform this action")
    return current

# 4. Audit logging for permission failures

def log_permission_denied(db: Session, user_id: str, action: str, resource: str, resource_id: str, message: str = None, http_status: int = None):
    from app.models.audit_log import AuditLog
    meta = {"attempted_action": action}
    if message:
        meta["message"] = message
    if http_status:
        meta["http_status"] = http_status
    entry = AuditLog(
        user_id=user_id,
        action="permission_denied",
        resource_type=resource,
        resource_id=resource_id,
        metadata=meta
    )
    db.add(entry)
    db.commit()
