from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.leave_request import LeaveRequestRead, LeaveRequestCreate
from app.models.leave_request import LeaveRequest
from app.db.session import get_db
from uuid import UUID
from app.deps.permissions import get_current_user, require_role, require_direct_manager, log_permission_denied

router = APIRouter()

@router.get("/", tags=["leave"], response_model=list[LeaveRequestRead])
def list_leave_requests(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # IC: own, Manager: direct reports, HR/Admin: all
    if current_user.role_band in ("HR", "Admin") or current_user.role_title in ("HR", "Admin"):
        requests = db.query(LeaveRequest).all()
    elif current_user.role_band == "Manager":
        requests = db.query(LeaveRequest).filter(LeaveRequest.user_id.in_([
            u.id for u in db.query(LeaveRequest).filter(LeaveRequest.user_id == current_user.user_id)
        ])).all()
    else:
        requests = db.query(LeaveRequest).filter(LeaveRequest.user_id == current_user.user_id).all()
    return [LeaveRequestRead.from_orm(req) for req in requests]

@router.post("/", tags=["leave"], response_model=LeaveRequestRead)
def create_leave_request(req: LeaveRequestCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # IC can create for self, Manager/HR/Admin can create for direct reports/anyone
    if (current_user.role_band not in ("HR", "Admin") and current_user.role_title not in ("HR", "Admin") and req.user_id != current_user.user_id):
        log_permission_denied(db, current_user.user_id, "create_leave_request", "leave_request", str(req.user_id))
        raise HTTPException(status_code=403, detail="Insufficient permissions to create leave request for this user")
    db_req = LeaveRequest(**req.dict())
    db.add(db_req)
    try:
        db.commit()
        db.refresh(db_req)
    except Exception as e:
        db.rollback()
        if hasattr(e, 'orig') and hasattr(e.orig, 'diag') and 'unique' in str(e.orig).lower():
            raise HTTPException(status_code=400, detail="Duplicate leave request")
        raise HTTPException(status_code=500, detail="Internal server error")
    log_permission_denied(db, current_user.user_id, "create_leave_request", "leave_request", str(db_req.id))
    return LeaveRequestRead.from_orm(db_req)

@router.get("/{request_id}", tags=["leave"], response_model=LeaveRequestRead)
def get_leave_request(request_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    # IC can view own, Manager can view direct reports, HR/Admin can view all
    if (str(current_user.user_id) != str(req.user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
        and str(req.user_id) != str(current_user.user_id)):
        log_permission_denied(db, current_user.user_id, "get_leave_request", "leave_request", str(request_id))
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return LeaveRequestRead.from_orm(req)

@router.put("/{request_id}", tags=["leave"], response_model=LeaveRequestRead)
def update_leave_request(request_id: UUID, req_update: LeaveRequestCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    # IC can update/cancel own, Manager/HR/Admin can update under their scope
    if (str(current_user.user_id) != str(req.user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
        and str(req.user_id) != str(current_user.user_id)):
        log_permission_denied(db, current_user.user_id, "update_leave_request", "leave_request", str(request_id))
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    for k, v in req_update.dict().items():
        setattr(req, k, v)
    try:
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update leave request")
    log_permission_denied(db, current_user.user_id, "update_leave_request", "leave_request", str(request_id))
    return LeaveRequestRead.from_orm(req)

@router.patch("/{request_id}/approve", tags=["leave"], response_model=LeaveRequestRead)
def approve_leave_request(request_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")
    # Only direct manager or HR/Admin can approve
    if (current_user.role_band not in ("HR", "Admin") and current_user.role_title not in ("HR", "Admin") and str(req.user_id) != str(current_user.user_id)):
        log_permission_denied(db, current_user.user_id, "approve_leave_request", "leave_request", str(request_id))
        raise HTTPException(status_code=403, detail="Only direct manager or HR/Admin can approve")
    req.status = "approved"
    try:
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not approve leave request")
    log_permission_denied(db, current_user.user_id, "approve_leave_request", "leave_request", str(request_id))
    return LeaveRequestRead.from_orm(req)
