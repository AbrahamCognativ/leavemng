from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.leave_request import LeaveRequestRead, LeaveRequestCreate
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
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
            u.id for u in db.query(LeaveRequest).filter(LeaveRequest.user_id == current_user.id)
        ])).all()
    else:
        requests = db.query(LeaveRequest).filter(LeaveRequest.user_id == current_user.id).all()
    return [LeaveRequestRead.from_orm(req) for req in requests]

@router.post("/", tags=["leave"], response_model=LeaveRequestRead)
def create_leave_request(req: LeaveRequestCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Validate leave_type_id exists
    try:
        leave_type = db.query(LeaveType).filter(LeaveType.id == req.leave_type_id).first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up leave_type_id: {str(e)}")
    if not leave_type:
        raise HTTPException(status_code=400, detail="Invalid leave_type_id")

    # Calculate total_days
    from datetime import timedelta, date, datetime as dt
    # Calculate total_days for annual leave (weekdays only) or all days otherwise
    from datetime import timedelta, date, datetime as dt
    total_days = 0
    current = req.start_date
    leave_code = leave_type.code.value if hasattr(leave_type.code, 'value') else str(leave_type.code)
    if leave_code == "annual":
        # Count only weekdays (Monday=0 to Friday=4)
        while current <= req.end_date:
            if current.weekday() < 5:
                total_days += 1
            current += timedelta(days=1)
    else:
        # Count all days
        total_days = (req.end_date - req.start_date).days + 1
    # print(f"DEBUG: Calculated total_days = {total_days} for leave_type = {leave_code}")



    db_req = LeaveRequest(
        user_id=current_user.id,
        leave_type_id=req.leave_type_id,
        start_date=req.start_date,
        end_date=req.end_date,
        total_days=total_days,
        status='pending',
        applied_at=dt.utcnow(),
        comments=req.comments
    )
    db.add(db_req)
    try:
        db.commit()
        db.refresh(db_req)
    except Exception as e:
        db.rollback()
        if hasattr(e, 'orig') and hasattr(e.orig, 'diag') and 'unique' in str(e.orig).lower():
            raise HTTPException(status_code=400, detail="Duplicate leave request")
        raise HTTPException(status_code=500, detail="Internal server error")
    return LeaveRequestRead.from_orm(db_req)


@router.get("/{request_id}", tags=["leave"], response_model=LeaveRequestRead)
def get_leave_request(request_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    # IC can view own, Manager can view direct reports, HR/Admin can view all
    if (str(current_user.id) != str(req.user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
        and str(req.user_id) != str(current_user.id)):
        log_permission_denied(db, current_user.id, "get_leave_request", "leave_request", str(request_id), message="Insufficient permissions to view leave request", http_status=403)
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return LeaveRequestRead.from_orm(req)

@router.put("/{request_id}", tags=["leave"], response_model=LeaveRequestRead)
def update_leave_request(request_id: UUID, req_update: LeaveRequestCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    # IC can update/cancel own, Manager/HR/Admin can update under their scope
    if (str(current_user.id) != str(req.user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
        and str(req.user_id) != str(current_user.id)):
        log_permission_denied(db, current_user.id, "update_leave_request", "leave_request", str(request_id))
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    for k, v in req_update.dict().items():
        setattr(req, k, v)
    try:
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update leave request")
    log_permission_denied(db, current_user.id, "update_leave_request", "leave_request", str(request_id))
    return LeaveRequestRead.from_orm(req)

@router.patch("/{request_id}/approve", tags=["leave"], response_model=LeaveRequestRead)
def approve_leave_request(request_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    sstt = req.status if hasattr(req.status, 'value') else str(req.status)
    # leave_code = leave_type.code.value if hasattr(leave_type.code, 'value') else str(leave_type.code)
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if (sstt if not hasattr(req.status, 'value') else req.status.value) != "pending":
        # print(f"Leave status = {sstt if not hasattr(req.status, 'value') else req.status.value}")
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")
    # Only direct manager or HR/Admin can approve
    if (current_user.role_band not in ("HR", "Admin") and current_user.role_title not in ("HR", "Admin") and str(req.user_id) != str(current_user.id)):
        log_permission_denied(db, current_user.id, "approve_leave_request", "leave_request", str(request_id))
        raise HTTPException(status_code=403, detail="Only direct manager or HR/Admin can approve")
    
    req.status = "approved"
    try:
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not approve leave request")
    log_permission_denied(db, current_user.id, "approve_leave_request", "leave_request", str(request_id))
    return LeaveRequestRead.from_orm(req)
