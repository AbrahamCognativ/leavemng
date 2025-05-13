from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from app.schemas.leave_request import LeaveRequestRead, LeaveRequestCreate
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.user import User
from app.db.session import get_db
from uuid import UUID
from fastapi import Request
from datetime import datetime, timezone
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
    return [LeaveRequestRead.model_validate(req) for req in requests]

@router.post("/", tags=["leave"], response_model=LeaveRequestRead)
def create_leave_request(req: LeaveRequestCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user), request: Request = None):
    # Validate leave_type_id exists
    try:
        leave_type = db.query(LeaveType).filter(LeaveType.id == req.leave_type_id).first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up leave_type_id: {str(e)}")
    if not leave_type:
        raise HTTPException(status_code=400, detail="Invalid leave_type_id")

    # Check for duplicate leave request
    existing = db.query(LeaveRequest).filter(
        LeaveRequest.user_id == current_user.id,
        LeaveRequest.leave_type_id == req.leave_type_id,
        LeaveRequest.start_date == req.start_date,
        LeaveRequest.end_date == req.end_date
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Duplicate leave request")

    # Validate that end_date is the same as or after start_date
    if req.end_date < req.start_date:
        raise HTTPException(status_code=400, detail="End date must be the same as or after start date.")

    # Calculate total_days
    from datetime import timedelta, date, datetime as dt
    # Calculate total_days for annual leave (weekdays only) or all days otherwise
    from datetime import timedelta, date, datetime as dt
    total_days = 0
    current = req.start_date
    leave_code = leave_type.code.value if hasattr(leave_type.code, 'value') else str(leave_type.code)
    if leave_code.lower() == "annual":
        # 1. Enforce 3-day prior application rule
        today = date.today()
        start_date = req.start_date
        # Defensive conversion to date
        if isinstance(start_date, str):
            try:
                start_date = dt.fromisoformat(start_date).date()
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid start_date format.")
        elif isinstance(start_date, dt):
            start_date = start_date.date()
        # print(f"[DEBUG] leave_code={leave_code}, start_date={start_date}, today={today}, delta_days={(start_date - today).days}")
        if (start_date - today).days < 3:
            raise HTTPException(status_code=400, detail="Leave must be requested at least 3 days in advance.")

        # 2. Count only weekdays (Monday=0 to Friday=4)
        while current <= req.end_date:
            if current.weekday() < 5:
                total_days += 1
            current += timedelta(days=1)

        # 3. Retrieve user's annual leave entitlement (max 19, from policy or leave_type)
        from app.models.leave_policy import LeavePolicy
        policy = db.query(LeavePolicy).filter(LeavePolicy.leave_type_id == leave_type.id, LeavePolicy.org_unit_id == current_user.org_unit_id).first()
        entitlement = 19
        if policy and policy.allocation_days_per_year:
            entitlement = min(float(policy.allocation_days_per_year), 19)
        elif hasattr(leave_type, 'default_allocation_days'):
            entitlement = min(float(leave_type.default_allocation_days), 19)

        # 4. Calculate user's annual leave taken in their accrual year (from joining date)
        # from app.models.user import User
        user = db.query(User).filter(User.id == current_user.id).first()
        join_date = user.created_at.date() if hasattr(user.created_at, 'date') else user.created_at
        accrual_year_start = join_date.replace(year=today.year)
        if accrual_year_start > today:
            accrual_year_start = join_date.replace(year=today.year-1)
        accrual_year_end = accrual_year_start.replace(year=accrual_year_start.year+1)
        taken = db.query(LeaveRequest).filter(
            LeaveRequest.user_id == current_user.id,
            LeaveRequest.leave_type_id == req.leave_type_id,
            LeaveRequest.start_date >= accrual_year_start,
            LeaveRequest.start_date < accrual_year_end,
            LeaveRequest.status == 'approved'
        ).all()
        taken_days = sum(lr.total_days for lr in taken)

        # 5. Check if new request exceeds entitlement
        if taken_days + total_days > entitlement:
            raise HTTPException(status_code=400, detail=f"Annual leave request exceeds entitlement ({entitlement} days per year). You have already taken {taken_days} days.")
    elif leave_code == "sick":
        # 1. Entitlement: 45 days/year (30 full + 15 half days)
        SICK_FULL_DAYS = 30
        SICK_HALF_DAYS = 15
        SICK_TOTAL = SICK_FULL_DAYS + SICK_HALF_DAYS * 0.5
        # Calculate user's sick leave taken in accrual year
        # from app.models.user import User
        user = db.query(User).filter(User.id == current_user.id).first()
        join_date = user.created_at.date() if hasattr(user.created_at, 'date') else user.created_at
        today = date.today()
        accrual_year_start = join_date.replace(year=today.year)
        if accrual_year_start > today:
            accrual_year_start = join_date.replace(year=today.year-1)
        accrual_year_end = accrual_year_start.replace(year=accrual_year_start.year+1)
        taken = db.query(LeaveRequest).filter(
            LeaveRequest.user_id == current_user.id,
            LeaveRequest.leave_type_id == req.leave_type_id,
            LeaveRequest.start_date >= accrual_year_start,
            LeaveRequest.start_date < accrual_year_end,
            LeaveRequest.status == 'approved'
        ).all()
        taken_days = sum(lr.total_days for lr in taken)
        # Calculate requested days (all days, including weekends)
        total_days = (req.end_date - req.start_date).days + 1
        if taken_days + total_days > SICK_TOTAL:
            raise HTTPException(status_code=400, detail=f"Sick leave request exceeds entitlement (45 days per year). You have already taken {taken_days} days.")
        # Mark request as pending and require document upload within 48 hours (configurable)
        # This will be handled by a background job
    elif leave_code == "paternity":
        # Only available to male users
        # from app.models.user import User
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user or user.gender != "male":
            raise HTTPException(status_code=400, detail="Paternity leave is only available to male employees.")
        PATERNITY_DAYS = 14
        today = date.today()
        join_date = user.created_at.date() if hasattr(user.created_at, 'date') else user.created_at
        accrual_year_start = join_date.replace(year=today.year)
        if accrual_year_start > today:
            accrual_year_start = join_date.replace(year=today.year-1)
        accrual_year_end = accrual_year_start.replace(year=accrual_year_start.year+1)
        taken = db.query(LeaveRequest).filter(
            LeaveRequest.user_id == current_user.id,
            LeaveRequest.leave_type_id == req.leave_type_id,
            LeaveRequest.start_date >= accrual_year_start,
            LeaveRequest.start_date < accrual_year_end,
            LeaveRequest.status == 'approved'
        ).all()
        taken_days = sum(lr.total_days for lr in taken)
        total_days = (req.end_date - req.start_date).days + 1
        if taken_days + total_days > PATERNITY_DAYS:
            raise HTTPException(status_code=400, detail=f"Paternity leave request exceeds entitlement (14 days per year). You have already taken {taken_days} days.")
    elif leave_code == "maternity":
        # Only available to female users
        # from app.models.user import User
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user or user.gender != "female":
            raise HTTPException(status_code=400, detail="Maternity leave is only available to female employees.")
        MATERNITY_DAYS = 90
        today = date.today()
        join_date = user.created_at.date() if hasattr(user.created_at, 'date') else user.created_at
        accrual_year_start = join_date.replace(year=today.year)
        if accrual_year_start > today:
            accrual_year_start = join_date.replace(year=today.year-1)
        accrual_year_end = accrual_year_start.replace(year=accrual_year_start.year+1)
        taken = db.query(LeaveRequest).filter(
            LeaveRequest.user_id == current_user.id,
            LeaveRequest.leave_type_id == req.leave_type_id,
            LeaveRequest.start_date >= accrual_year_start,
            LeaveRequest.start_date < accrual_year_end,
            LeaveRequest.status == 'approved'
        ).all()
        taken_days = sum(lr.total_days for lr in taken)
        total_days = (req.end_date - req.start_date).days + 1
        if taken_days + total_days > MATERNITY_DAYS:
            raise HTTPException(status_code=400, detail=f"Maternity leave request exceeds entitlement (90 days per year). You have already taken {taken_days} days.")
    elif leave_code == "compassionate":
        # Compassionate: 10 days per quarter, based on start date's quarter
        # from app.models.user import User
        user = db.query(User).filter(User.id == current_user.id).first()
        COMPASSIONATE_DAYS = 10
        start = req.start_date
        # Determine quarter for start date
        quarter = (start.month - 1) // 3 + 1
        quarter_start = date(start.year, 3 * (quarter - 1) + 1, 1)
        if quarter == 4:
            quarter_end = date(start.year, 12, 31)
        else:
            quarter_end = date(start.year, 3 * quarter + 1, 1) - timedelta(days=1)
        taken = db.query(LeaveRequest).filter(
            LeaveRequest.user_id == current_user.id,
            LeaveRequest.leave_type_id == req.leave_type_id,
            LeaveRequest.start_date >= quarter_start,
            LeaveRequest.start_date <= quarter_end,
            LeaveRequest.status == 'approved'
        ).all()
        taken_days = sum(lr.total_days for lr in taken)
        total_days = (req.end_date - req.start_date).days + 1
        if taken_days + total_days > COMPASSIONATE_DAYS:
            raise HTTPException(status_code=400, detail=f"Compassionate leave request exceeds entitlement (10 days per quarter). You have already taken {taken_days} days this quarter.")
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
        applied_at=dt.now(timezone.utc),
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
    # Send notification to approver (manager)
    from app.utils.email_utils import send_leave_request_notification
    manager = db.query(User).filter(User.id == current_user.manager_id).first() if current_user.manager_id else None
    if manager:
        # Use LeaveType.description as the label if available, fallback to code label
        LEAVE_TYPE_LABELS = {
            "annual": "Annual Leave",
            "sick": "Sick Leave",
            "unpaid": "Unpaid Leave",
            "compassionate": "Compassionate Leave",
            "maternity": "Maternity Leave",
            "paternity": "Paternity Leave",
            "custom": "Custom Leave"
        }
        type_label = None
        
        # if not type_label:
        code_value = getattr(leave_type, 'code', None)
        if hasattr(code_value, 'value'):
            code_value = code_value.value

        if code_value == "custom":
            type_label = getattr(leave_type, 'custom_code', None)
        else:
            type_label = LEAVE_TYPE_LABELS.get(code_value, str(code_value) if code_value else "Unknown")
        
        leave_details = {
            "Type": type_label,
            "Start Date": str(req.start_date),
            "End Date": str(req.end_date),
            "Days": total_days,
            "Comments": req.comments or ""
        }
        send_leave_request_notification(
            manager.email,
            current_user.name,
            leave_details,
            request=request,
            request_id=db_req.id,
            requestor_email=current_user.email
        )
    return LeaveRequestRead.model_validate(db_req)


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
    return LeaveRequestRead.model_validate(req)

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
    for k, v in req_update.model_dump().items():
        setattr(req, k, v)
    try:
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update leave request")
    log_permission_denied(db, current_user.id, "update_leave_request", "leave_request", str(request_id))
    return LeaveRequestRead.model_validate(req)

@router.patch("/{request_id}/approve", tags=["leave"], response_model=LeaveRequestRead)
def approve_leave_request(request_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user), request: Request = None ):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    sstt = req.status if hasattr(req.status, 'value') else str(req.status)
    if (sstt if not hasattr(req.status, 'value') else req.status.value) != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")
    # Prevent self-approval, even for Admin/HR
    if str(req.user_id) == str(current_user.id):
        log_permission_denied(db, current_user.id, "approve_leave_request", "leave_request", str(request_id))
        raise HTTPException(status_code=403, detail="You cannot approve your own leave request.")
    if (current_user.role_band not in ("HR", "Admin") and current_user.role_title not in ("HR", "Admin") and str(req.user_id) != str(current_user.id)):
        log_permission_denied(db, current_user.id, "approve_leave_request", "leave_request", str(request_id))
        raise HTTPException(status_code=403, detail="Only direct manager or HR/Admin can approve")
    try:
        req.status = 'approved'
        req.decision_at = datetime.now(timezone.utc)
        req.decided_by = current_user.id
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        import logging
        logging.error(f"Error during leave approval DB commit: {e}")
        raise HTTPException(status_code=500, detail=f"Could not approve leave request: {e}")

    from app.utils.email_utils import send_leave_approval_notification
    user = db.query(User).filter(User.id == req.user_id).first()
    leave_details = f"Type: {req.leave_type_id}, Start: {req.start_date}, End: {req.end_date}, Days: {req.total_days}"
    try:
        if user:
            send_leave_approval_notification(user.email, leave_details, approved=True, request=request)
        log_permission_denied(db, current_user.id, "approve_leave_request", "leave_request", str(request_id))
    except Exception as e:
        import logging
        logging.error(f"Error sending approval email: {e}")
    return LeaveRequestRead.model_validate(req)


@router.patch("/{request_id}/reject", tags=["leave"], response_model=LeaveRequestRead)
def reject_leave_request(request_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user), request: Request = None ):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    sstt = req.status if hasattr(req.status, 'value') else str(req.status)
    if (sstt if not hasattr(req.status, 'value') else req.status.value) != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be rejected")
    # Prevent self-rejection, even for Admin/HR
    if str(req.user_id) == str(current_user.id):
        log_permission_denied(db, current_user.id, "reject_leave_request", "leave_request", str(request_id))
        raise HTTPException(status_code=403, detail="You cannot reject your own leave request.")
    if (current_user.role_band not in ("HR", "Admin") and current_user.role_title not in ("HR", "Admin") and str(req.user_id) != str(current_user.id)):
        log_permission_denied(db, current_user.id, "reject_leave_request", "leave_request", str(request_id))
        raise HTTPException(status_code=403, detail="Only direct manager or HR/Admin can reject")
    try:
        req.status = 'rejected'
        req.decision_at = datetime.now(timezone.utc)
        req.decided_by = current_user.id
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        import logging
        logging.error(f"Error during leave rejection DB commit: {e}")
        raise HTTPException(status_code=500, detail=f"Could not reject leave request: {e}")

    from app.utils.email_utils import send_leave_approval_notification
    user = db.query(User).filter(User.id == req.user_id).first()
    leave_details = f"Type: {req.leave_type_id}, Start: {req.start_date}, End: {req.end_date}, Days: {req.total_days}"
    try:
        if user:
            send_leave_approval_notification(user.email, leave_details, approved=False, request=request)
        log_permission_denied(db, current_user.id, "reject_leave_request", "leave_request", str(request_id))
    except Exception as e:
        import logging
        logging.error(f"Error sending rejection email: {e}")
    return LeaveRequestRead.model_validate(req)
    
    from app.utils.email_utils import send_leave_approval_notification
    user = db.query(User).filter(User.id == req.user_id).first()
    leave_details = f"Type: {req.leave_type_id}, Start: {req.start_date}, End: {req.end_date}, Days: {req.total_days}"
    try:
        if user:
            send_leave_approval_notification(user.email, leave_details, approved=True, request=request)
        log_permission_denied(db, current_user.id, "approve_leave_request", "leave_request", str(request_id))
    except Exception as e:
        # Optionally log the error but don't fail the approval
        import logging
        logging.error(f"Error in approval post-processing: {e}")
        pass
    from pydantic import ValidationError
    import logging
    logging.debug(f"LeaveRequest DB object before validation: {req.__dict__}")
    try:
        return LeaveRequestRead.model_validate(req)
    except ValidationError as ve:
        logging.error(f"LeaveRequestRead validation error: {ve}")
        raise HTTPException(status_code=500, detail="Internal error during approval response formatting")
    except Exception as e:
        logging.error(f"Unexpected error in approval endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal error during approval")


@router.delete("/{request_id}", tags=["leave"], status_code=204)
def delete_leave_request(request_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    # Only the request owner, HR, or Admin can delete
    if (str(current_user.id) != str(req.user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")):
        log_permission_denied(db, current_user.id, "delete_leave_request", "leave_request", str(request_id))
        raise HTTPException(status_code=403, detail="Insufficient permissions to delete leave request")
    db.delete(req)
    db.commit()
    return None

