from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRead
from pydantic import BaseModel, EmailStr
from jose import jwt
from datetime import datetime, timedelta
import os

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class Token(BaseModel):
    access_token: str
    token_type: str

class InviteRequest(BaseModel):
    email: EmailStr
    name: str
    role_band: str
    role_title: str
    org_unit_id: str = None
    manager_id: str = None

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or user.hashed_password != form_data.password:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    claims = {
        "sub": str(user.id),
        "user_id": str(user.id),
        "role_band": user.role_band,
        "role_title": user.role_title,
        "org_unit_id": str(user.org_unit_id) if user.org_unit_id else None,
        "manager_id": str(user.manager_id) if user.manager_id else None,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    token = jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

# Dummy permission dependency for HR/Admin
from fastapi import Security

def require_hr_admin(current_user: User = Depends(get_db)):
    # In real app, extract user from JWT and check role_band/title
    if getattr(current_user, "role_band", None) not in ("HR", "Admin") and getattr(current_user, "role_title", None) not in ("HR", "Admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return current_user

@router.post("/invite", response_model=UserRead)
def invite_user(invite: InviteRequest, db: Session = Depends(get_db), current_user: User = Depends(require_hr_admin)):
    # In a real app, send invite email and create user with temp password
    existing = db.query(User).filter(User.email == invite.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    user = User(
        name=invite.name,
        email=invite.email,
        hashed_password="temp123",  # In real app, generate/send temp password
        role_band=invite.role_band,
        role_title=invite.role_title,
        org_unit_id=invite.org_unit_id,
        manager_id=invite.manager_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    # In a real app, send invite email here
    return UserRead.from_orm(user)
