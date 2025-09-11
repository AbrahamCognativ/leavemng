from fastapi import APIRouter, Depends, Request, HTTPException, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.schemas.leave_request import LeaveRequestRead, LeaveRequestCreate, LeaveRequestUpdate, LeaveRequestPartialUpdate
from app.schemas.leave_balance import LeaveBalanceUpdate, LeaveBalanceRead
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.models.user import User
from app.models.leave_balance import LeaveBalance
from app.db.session import get_db
from uuid import UUID
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from app.deps.permissions import get_current_user, log_permission_denied, log_permission_accepted

router = APIRouter()


@router.get("/", tags=["leave"], response_model=list[LeaveRequestRead])
def list_leave_requests(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    # IC: own, Manager: direct reports, HR/Admin: all
    if current_user.role_band in (
        "HR",
        "Admin") or current_user.role_title in (
        "HR",
            "Admin"):
        requests = db.query(LeaveRequest).all()
    elif current_user.role_band == "Manager":
        requests = db.query(LeaveRequest).filter(LeaveRequest.user_id.in_([
            u.id for u in db.query(User).filter(User.manager_id == current_user.id)
        ])).all()
    else:
        requests = db.query(LeaveRequest).filter(
            LeaveRequest.user_id == current_user.id).all()
    return [LeaveRequestRead.model_validate(req) for req in requests]


@router.post("/", tags=["leave"], response_model=LeaveRequestRead)
def create_leave_request(
        req: LeaveRequestCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
        request: Request = None):
    # Validate leave_type_id exists
    try:
        leave_type = db.query(LeaveType).filter(
            LeaveType.id == req.leave_type_id).first()
    except (SQLAlchemyError, AttributeError, TypeError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error looking up leave_type_id: {str(e)}")
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
        raise HTTPException(
            status_code=400,
            detail="End date must be the same as or after start date.")

    # Calculate total days for all leave types (weekdays only)
    total_days = 0
    for n in range(int((req.end_date - req.start_date).days) + 1):
        day = req.start_date + timedelta(n)
        if day.weekday() < 5:
            total_days += 1
    req.total_days = total_days

    # Validate that annual leave is applied at least 5 days in advance
    if leave_type.code.value == 'annual':
        start_date = req.start_date
        if (start_date - date.today()) < timedelta(days=5):
            raise HTTPException(
                status_code=400,
                detail="Annual leave must be applied at least 5 days in advance")

    elif leave_type.code.value == 'maternity':
        if current_user.gender != 'female':
            raise HTTPException(
                status_code=400,
                detail="Only female employees can apply for maternity leave")
    elif leave_type.code.value == 'paternity':
        if current_user.gender != 'male':
            raise HTTPException(
                status_code=400,
                detail="Only male employees can apply for paternity leave")

    # Query LeaveBalance, check and deduct req.total_days
    leave_balance = db.query(LeaveBalance).filter(
        LeaveBalance.user_id == current_user.id,
        LeaveBalance.leave_type_id == req.leave_type_id).first()
    if not leave_balance or leave_balance.balance_days < req.total_days:
        raise HTTPException(
            status_code=400,
            detail="Insufficient leave balance")

    try:
        leave_balance.balance_days -= Decimal(str(req.total_days))
        db.add(leave_balance)
        db_req = LeaveRequest(
            user_id=current_user.id,
            leave_type_id=req.leave_type_id,
            start_date=req.start_date,
            end_date=req.end_date,
            total_days=req.total_days,
            status='pending',
            applied_at=datetime.now(timezone.utc),
            comments=req.comments
        )
        db.add(db_req)
        db.commit()
        db.refresh(db_req)
    except Exception as e:
        db.rollback()
        leave_balance.balance_days += Decimal(str(req.total_days))
        db.add(leave_balance)
        db.commit()
        orig = getattr(e, 'orig', None)
        if orig is not None and hasattr(orig, 'diag') and 'unique' in str(orig).lower():
            raise HTTPException(
                status_code=400,
                detail="Duplicate leave request")
        raise HTTPException(status_code=503, detail="Internal server error")

    # Send notification to approver (manager)
    from app.utils.email_utils import send_leave_request_notification_with_tokens
    from app.api.v1.routers.actions import generate_action_tokens
    manager = db.query(User).filter(
        User.id == current_user.manager_id).first() if current_user.manager_id else None
    if manager:
        # Generate secure tokens for approve/reject actions
        tokens = generate_action_tokens("leave_request", str(db_req.id), str(manager.id), db)
        
        LEAVE_TYPE_LABELS = {
            "annual": "Annual Leave",
            "sick": "Sick Leave",
            "unpaid": "Unpaid Leave",
            "compassionate": "Compassionate Leave",
            "maternity": "Maternity Leave",
            "paternity": "Paternity Leave",
            "custom": "Custom Leave"
        }
        type_label = LEAVE_TYPE_LABELS.get(leave_type.code.value, str(
            leave_type.code.value) if leave_type.code.value else "Unknown")

        code_value = getattr(leave_type, 'code', None)
        if hasattr(code_value, 'value'):
            code_value = code_value.value

        if code_value == "custom":
            type_label = getattr(leave_type, 'custom_code', None)
        else:
            type_label = LEAVE_TYPE_LABELS.get(
                code_value, str(code_value) if code_value else "Unknown")

        leave_details = {
            "Type": type_label,
            "Start Date": str(req.start_date),
            "End Date": str(req.end_date),
            "Days": (req.end_date - req.start_date).days + 1,
            "Comments": req.comments or ""
        }
        try:
            send_leave_request_notification_with_tokens(
                manager.email,
                current_user.name,
                leave_details,
                request=request,
                request_id=db_req.id,
                requestor_email=current_user.email,
                approve_token=tokens['approve'],
                reject_token=tokens['reject']
            )
        except Exception as e:
            # Log the error but don't fail the request creation
            import logging
            logging.error(f"Error sending leave notification email: {e}")
    return LeaveRequestRead.model_validate(db_req)


@router.get("/{request_id}", tags=["leave"], response_model=LeaveRequestRead)
def get_leave_request(
        request_id: UUID,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    # IC can view own, Manager can view direct reports, HR/Admin can view all
    if (str(current_user.id) != str(req.user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
            and str(req.user_id) != str(current_user.id)):
        log_permission_denied(
            db,
            current_user.id,
            "get_leave_request",
            "leave_request",
            str(request_id),
            message="Insufficient permissions to view leave request",
            http_status=403)
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return LeaveRequestRead.model_validate(req)


@router.put("/{request_id}", tags=["leave"], response_model=LeaveRequestRead)
def update_leave_request(
        request_id: UUID,
        req_update: LeaveRequestUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    # IC can update/cancel own, Manager/HR/Admin can update under their scope
    if (str(current_user.id) != str(req.user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
            and str(req.user_id) != str(current_user.id)):
        log_permission_denied(
            db,
            current_user.id,
            "update_leave_request",
            "leave_request",
            str(request_id))
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    for k, v in req_update.model_dump().items():
        setattr(req, k, v)
    try:
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500,
                            detail="Could not update leave request")
    return LeaveRequestRead.model_validate(req)


@router.patch("/{request_id}", tags=["leave"], response_model=LeaveRequestRead)
def partial_update_leave_request(
        request_id: UUID,
        req_update: LeaveRequestPartialUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    # Get the leave request
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")

    # Check if the request belongs to the current user
    if str(current_user.id) != str(req.user_id):
        log_permission_denied(
            db,
            current_user.id,
            "update_leave_request",
            "leave_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="You can only update your own leave requests")

    # Allow editing for both pending and approved statuses
    # Leave the validation check commented out for reference
    # status = req.status if hasattr(req.status, 'value') else str(req.status)
    # if (status if not hasattr(req.status, 'value') else req.status.value) != "pending":
    #     raise HTTPException(status_code=400, detail="Only pending leave requests can be updated")

    # Update only the allowed fields (comments)
    update_data = req_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'comments':
            setattr(req, field, value)

    try:
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Could not update leave request: {str(e)}")

    return LeaveRequestRead.model_validate(req)


@router.patch("/{request_id}/approve",
              tags=["leave"],
              response_model=LeaveRequestRead)
def approve_leave_request(
        request_id: UUID,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
        request: Request = None,
        approval_note: str = Form(None)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    sstt = req.status if hasattr(req.status, 'value') else str(req.status)
    if (sstt if not hasattr(req.status, 'value')
            else req.status.value) != "pending":
        raise HTTPException(status_code=400,
                            detail="Only pending requests can be approved")
    # Prevent self-approval, even for Admin/HR
    if str(req.user_id) == str(current_user.id):
        log_permission_denied(
            db,
            current_user.id,
            "approve_leave_request",
            "leave_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="You cannot approve your own leave request.")
    if (current_user.role_band not in ("HR",
                                       "Admin") and current_user.role_title not in ("HR",
                                                                                    "Admin") and str(req.user_id) != str(current_user.id)):
        log_permission_denied(
            db,
            current_user.id,
            "approve_leave_request",
            "leave_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="Only direct manager or HR/Admin can approve")
    try:
        req.status = 'approved'
        req.decision_at = datetime.now(timezone.utc)
        req.decided_by = current_user.id
        req.approval_note = approval_note
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500,
                            detail=f"Could not approve leave request: {e}")

    from app.utils.email_utils import send_leave_approval_notification
    user = db.query(User).filter(User.id == req.user_id).first()

    # Get the leave type name
    leave_type = db.query(LeaveType).filter(
        LeaveType.id == req.leave_type_id).first()
    leave_type_name = leave_type.custom_code if leave_type and leave_type.code.value == 'custom' else (
        leave_type.code.value.title() + ' Leave' if leave_type else 'Leave')

    # Create a proper leave details dictionary
    leave_details = {
        "Type": leave_type_name,
        "Start Date": str(req.start_date),
        "End Date": str(req.end_date),
        "Days": str(req.total_days)
    }

    try:
        if user:
            send_leave_approval_notification(
                user.email, leave_details, approved=True, request=request)
    except Exception as e:
        import logging
        logging.error(f"Error sending approval email: {e}")
    return LeaveRequestRead.model_validate(req)


@router.patch("/{request_id}/reject",
              tags=["leave"],
              response_model=LeaveRequestRead)
def reject_leave_request(
        request_id: UUID,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
        request: Request = None,
        approval_note: str = Form(None)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    sstt = req.status if hasattr(req.status, 'value') else str(req.status)
    if (sstt if not hasattr(req.status, 'value')
            else req.status.value) != "pending":
        raise HTTPException(status_code=400,
                            detail="Only pending requests can be rejected")
    # Prevent self-rejection, even for Admin/HR
    if str(req.user_id) == str(current_user.id):
        log_permission_denied(
            db,
            current_user.id,
            "reject_leave_request",
            "leave_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="You cannot reject your own leave request.")
    if (current_user.role_band not in ("HR",
                                       "Admin") and current_user.role_title not in ("HR",
                                                                                    "Admin") and str(req.user_id) != str(current_user.id)):
        log_permission_denied(
            db,
            current_user.id,
            "reject_leave_request",
            "leave_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="Only direct manager or HR/Admin can reject")
    try:
        req.status = 'rejected'
        req.decision_at = datetime.now(timezone.utc)
        req.decided_by = current_user.id
        req.approval_note = approval_note
        db.commit()
        db.refresh(req)

        # Add total_days back to user's leave balance
        leave_balance = db.query(LeaveBalance).filter(
            LeaveBalance.user_id == req.user_id,
            LeaveBalance.leave_type_id == req.leave_type_id).first()
        if leave_balance:
            leave_balance.balance_days += Decimal(str(req.total_days))
            db.add(leave_balance)
            db.commit()
        log_permission_accepted(
            db,
            current_user.id,
            "reject_leave_request",
            "leave_request",
            str(request_id))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500,
                            detail=f"Could not reject leave request: {e}")

    from app.utils.email_utils import send_leave_approval_notification
    user = db.query(User).filter(User.id == req.user_id).first()

    # Get the leave type name
    leave_type = db.query(LeaveType).filter(
        LeaveType.id == req.leave_type_id).first()
    leave_type_name = leave_type.custom_code if leave_type and leave_type.code.value == 'custom' else (
        leave_type.code.value.title() + ' Leave' if leave_type else 'Leave')

    # Create a proper leave details dictionary
    leave_details = {
        "Type": leave_type_name,
        "Start Date": str(req.start_date),
        "End Date": str(req.end_date),
        "Days": str(req.total_days)
    }

    try:
        if user:
            send_leave_approval_notification(
                user.email, leave_details, approved=False, request=request)
    except (AttributeError, TypeError, SQLAlchemyError) as e:
        import logging
        logging.error(f"Error sending rejection email: {e}")
    return LeaveRequestRead.model_validate(req)


@router.delete("/{request_id}", tags=["leave"], status_code=204)
def delete_leave_request(
        request_id: UUID,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    # Only the request owner, HR, or Admin can delete
    if (str(current_user.id) != str(req.user_id)
        and current_user.role_band not in ("HR", "Admin")
            and current_user.role_title not in ("HR", "Admin")):
        log_permission_denied(
            db,
            current_user.id,
            "delete_leave_request",
            "leave_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to delete leave request")
    db.delete(req)
    db.commit()
    return None


@router.put("/balance/{user_id}/{leave_type_id}",
            tags=["leave"], response_model=LeaveBalanceRead)
def update_leave_balance(
        user_id: UUID,
        leave_type_id: UUID,
        balance_update: LeaveBalanceUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    """Update leave balance for a specific user and leave type.

    Only HR, Admin, and Managers can update leave balances.
    Managers can only update balances for their direct reports.
    """
    # First check if the user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the leave type exists
    leave_type = db.query(LeaveType).filter(
        LeaveType.id == leave_type_id).first()
    if not leave_type:
        raise HTTPException(status_code=404, detail="Leave type not found")

    # Check permissions: HR/Admin can update any, Manager can update direct
    # reports
    is_admin_or_hr = current_user.role_band in (
        "HR", "Admin") or current_user.role_title in (
        "HR", "Admin")
    is_manager_of_user = user.manager_id == current_user.id

    if not (is_admin_or_hr or is_manager_of_user):
        log_permission_denied(
            db,
            current_user.id,
            "update_leave_balance",
            "leave_balance",
            str(user_id))
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to update leave balance")

    # Get the leave balance record
    leave_balance = db.query(LeaveBalance).filter(
        LeaveBalance.user_id == user_id,
        LeaveBalance.leave_type_id == leave_type_id
    ).first()

    if not leave_balance:
        # If balance doesn't exist, create it
        leave_balance = LeaveBalance(
            user_id=user_id,
            leave_type_id=leave_type_id,
            balance_days=balance_update.balance_days,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(leave_balance)
    else:
        # Update existing balance
        leave_balance.balance_days = Decimal(str(balance_update.balance_days))
        leave_balance.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(leave_balance)
        log_permission_accepted(
            db,
            current_user.id,
            "update_leave_balance",
            "leave_balance",
            str(user_id))
    except (SQLAlchemyError, AttributeError, TypeError) as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Could not update leave balance: {str(e)}")

    return LeaveBalanceRead.model_validate(leave_balance)
