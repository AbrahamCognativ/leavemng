from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.leave_request import LeaveRequest
from datetime import datetime, timedelta

router = APIRouter()
from app.deps.permissions import require_role
from fastapi import Depends

@router.get("/summary", tags=["analytics"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def analytics_summary(db: Session = Depends(get_db)):
    users = db.query(User).count()
    leaves = db.query(LeaveRequest).count()
    return {"total_users": users, "total_leave_requests": leaves}

@router.get("/leave-stats", tags=["analytics"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def leave_stats(db: Session = Depends(get_db)):
    last_30 = datetime.utcnow() - timedelta(days=30)
    recent_leaves = db.query(LeaveRequest).filter(LeaveRequest.created_at >= last_30).count()
    total_leaves = db.query(LeaveRequest).count()
    return {"last_30_days": recent_leaves, "total": total_leaves}

@router.get("/user-growth", tags=["analytics"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def user_growth(db: Session = Depends(get_db)):
    last_30 = datetime.utcnow() - timedelta(days=30)
    recent_users = db.query(User).filter(User.created_at >= last_30).count()
    total_users = db.query(User).count()
    return {"new_users_last_30_days": recent_users, "total_users": total_users}
