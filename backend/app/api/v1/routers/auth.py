from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.utils.password import hash_password, verify_password
from app.schemas.user import UserRead
from pydantic import BaseModel, EmailStr
from jose import jwt
from datetime import datetime, timedelta
from datetime import timezone
from app.settings import get_settings
from uuid import UUID
from app.deps.permissions import get_current_user, require_role
from fastapi import Request


router = APIRouter()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserRead

class InviteRequest(BaseModel):
    email: EmailStr
    name: str
    role_band: str
    role_title: str
    gender: str
    passport_or_id_number: str
    org_unit_id: str = None
    manager_id: str = None

@router.post("/login", tags=["auth"], response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    # if not user or not user.is_active:
    #     raise HTTPException(status_code=401, detail="User is not active")
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Log failed login attempt
        from app.utils.audit import create_audit_log
        create_audit_log(
            db=db,
            user_id="00000000-0000-0000-0000-000000000000",  # Unknown user
            action="login_failed",
            resource_type="auth",
            resource_id="00000000-0000-0000-0000-000000000000",
            metadata={"email": form_data.username, "reason": "Incorrect email or password"}
        )
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    claims = {
            "sub": str(user.id),
            "user_id": str(user.id),
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role_band": user.role_band,
            "gender": user.gender,
            "role_title": user.role_title,
            "org_unit_id": str(user.org_unit_id) if user.org_unit_id else None,
            "manager_id": str(user.manager_id) if user.manager_id else None,
            "passport_or_id_number": user.passport_or_id_number,
            "profile_image_url": user.profile_image_url,
            "extra_metadata": user.extra_metadata,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
    token = jwt.encode(claims, get_settings().SECRET_KEY, algorithm=ALGORITHM)
    
    # Log successful login
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(user.id),
        action="login_success",
        resource_type="auth",
        resource_id=str(user.id),
        metadata={"email": user.email, "role": user.role_band}
    )
    
    return {"access_token": token, "token_type": "bearer", "user": UserRead.from_orm(user)}

# Dummy permission dependency for HR/Admin
from fastapi import Security

def require_hr_admin(current_user: User = Depends(get_db)):
    # In real app, extract user from JWT and check role_band/title
    if getattr(current_user, "role_band", None) not in ("HR", "Admin") and getattr(current_user, "role_title", None) not in ("HR", "Admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return current_user

from app.deps.permissions import get_current_user, require_role

@router.post("/invite", tags=["auth"], response_model=UserRead, dependencies=[Depends(require_role(["HR", "Admin"]))])
def invite_user(invite: InviteRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user), request: Request = None):
    # Only HR or Manager/Admin can invite
    existing = db.query(User).filter(User.email == invite.email).first()
    passport_exist = db.query(User).filter(User.passport_or_id_number == invite.passport_or_id_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    if passport_exist:
        raise HTTPException(status_code=400, detail="User with this passport or ID number already exists")
    # Validate passport_or_id_number is provided
    if not getattr(invite, 'passport_or_id_number', None):
        raise HTTPException(status_code=422, detail="Field 'passport_or_id_number' is required and cannot be null or empty.")
    # Validate manager_id and org_unit_id are valid UUIDs or None
    manager_id = invite.manager_id
    org_unit_id = invite.org_unit_id
    for field_name, field_value in [("manager_id", manager_id), ("org_unit_id", org_unit_id)]:
        if field_value not in (None, "", "null"):
            try:
                field_value = str(UUID(field_value))
            except Exception:
                raise HTTPException(
                    status_code=422,
                    detail=f"Field '{field_name}' must be a valid UUID or null. Got: '{field_value}'. Example: 'e7b8e9b9-8e6e-4e3a-9e3a-9e3a9e3a9e3a'"
                )
            if field_name == "manager_id":
                manager_id = field_value
            else:
                org_unit_id = field_value
    # Require gender, default to 'male' if not provided
    gender = getattr(invite, 'gender', None) or 'male'
    user = User(
        name=invite.name,
        email=invite.email,
        hashed_password=hash_password("secret123"),  # In real app, generate/send temp password
        role_band=invite.role_band,
        role_title=invite.role_title,
        passport_or_id_number=invite.passport_or_id_number,
        org_unit_id=org_unit_id,
        manager_id=manager_id,
        gender=gender
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # Send invite email
    from app.utils.email import send_invite_email
    invite_link = f"https://your-app-url/register?email={user.email}"  # TODO: Replace with real link
    send_invite_email(user.email, invite_link, request=request)
    return UserRead.from_orm(user)

@router.post("/logout", tags=["auth"])
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Logout endpoint - primarily used for audit logging purposes.
    The actual token invalidation happens client-side by removing the token.
    """
    # Log the logout action
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="logout",
        resource_type="auth",
        resource_id=str(current_user.id),
        metadata={"email": current_user.email}
    )
    
    return {"detail": "Successfully logged out"}
