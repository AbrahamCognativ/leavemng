from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserRead, UserCreate
from app.models.user import User
from app.db.session import get_db
from uuid import UUID

router = APIRouter()

@router.get("/", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [UserRead.from_orm(user) for user in users]

@router.post("/", response_model=UserRead)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(**user.dict(exclude={"password"}), hashed_password=user.password)  # Hash in real impl
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except Exception as e:
        db.rollback()
        if hasattr(e, 'orig') and hasattr(e.orig, 'diag') and 'unique' in str(e.orig).lower():
            raise HTTPException(status_code=400, detail="passport_or_id_number already exists")
        raise HTTPException(status_code=500, detail="Internal server error")
    return UserRead.from_orm(db_user)

@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead.from_orm(user)

@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, user_update: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for k, v in user_update.dict(exclude={"password"}).items():
        setattr(user, k, v)
    user.hashed_password = user_update.password  # In real app, hash this
    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update user")
    return UserRead.from_orm(user)
