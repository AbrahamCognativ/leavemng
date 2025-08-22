from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.schemas.wfh_request import WFHRequestRead, WFHRequestCreate, WFHRequestUpdate, WFHRequestPartialUpdate
from app.models.wfh_request import WFHRequest
from app.models.user import User
from app.db.session import get_db
from uuid import UUID
from datetime import datetime, timezone, date, timedelta
from app.deps.permissions import get_current_user, log_permission_denied, log_permission_accepted

router = APIRouter()


def build_wfh_response(wfh_request: WFHRequest, db: Session) -> dict:
    """Build WFH response with approver name and working days populated"""
    response_data = WFHRequestRead.model_validate(wfh_request).model_dump()
    
    # Add approver name if decided_by is set
    if wfh_request.decided_by:
        approver = db.query(User).filter(User.id == wfh_request.decided_by).first()
        response_data['approver_name'] = approver.name if approver else 'Unknown'
    else:
        response_data['approver_name'] = None
    
    # Calculate working days (excluding weekends)
    working_days = 0
    current_date = wfh_request.start_date
    while current_date <= wfh_request.end_date:
        # Monday = 0, Sunday = 6, so weekdays are 0-4
        if current_date.weekday() < 5:
            working_days += 1
        current_date += timedelta(days=1)
    
    response_data['working_days'] = working_days
    
    return response_data


@router.get("/", tags=["wfh"], response_model=list[WFHRequestRead])
def list_wfh_requests(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    """
    List WFH requests based on user role:
    - IC: own requests
    - Manager: direct reports' requests
    - HR/Admin: all requests
    """
    if current_user.role_band in ("HR", "Admin") or current_user.role_title in ("HR", "Admin"):
        requests = db.query(WFHRequest).all()
    elif current_user.role_band == "Manager":
        requests = db.query(WFHRequest).filter(WFHRequest.user_id.in_([
            u.id for u in db.query(User).filter(User.manager_id == current_user.id)
        ])).all()
    else:
        requests = db.query(WFHRequest).filter(
            WFHRequest.user_id == current_user.id).all()
    
    # Build responses with approver names
    return [build_wfh_response(req, db) for req in requests]


@router.post("/", tags=["wfh"], response_model=WFHRequestRead)
def create_wfh_request(
        req: WFHRequestCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
        request: Request = None):
    """Create a new WFH request"""
    
    # Validate that end_date is the same as or after start_date
    if req.end_date < req.start_date:
        raise HTTPException(
            status_code=400,
            detail="End date must be the same as or after start date.")

    # Check for duplicate WFH request
    existing = db.query(WFHRequest).filter(
        WFHRequest.user_id == current_user.id,
        WFHRequest.start_date == req.start_date,
        WFHRequest.end_date == req.end_date
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Duplicate WFH request")

    # Validate that WFH is applied at least 1 day in advance
    if (req.start_date - date.today()) < timedelta(days=1):
        raise HTTPException(
            status_code=400,
            detail="Work from home must be applied at least 1 day in advance")

    try:
        db_req = WFHRequest(
            user_id=current_user.id,
            start_date=req.start_date,
            end_date=req.end_date,
            status='pending',
            applied_at=datetime.now(timezone.utc),
            reason=req.reason
        )
        db.add(db_req)
        db.commit()
        db.refresh(db_req)
        
        # Log successful WFH request creation
        log_permission_accepted(
            db,
            current_user.id,
            "create_wfh_request",
            "wfh_request",
            str(db_req.id),
            message="WFH request created successfully")
    except Exception as e:
        db.rollback()
        orig = getattr(e, 'orig', None)
        if orig is not None and hasattr(orig, 'diag') and 'unique' in str(orig).lower():
            raise HTTPException(
                status_code=400,
                detail="Duplicate WFH request")
        raise HTTPException(status_code=503, detail="Internal server error")

    # Send notification to approver (manager)
    from app.utils.email_utils import send_wfh_request_notification
    manager = db.query(User).filter(
        User.id == current_user.manager_id).first() if current_user.manager_id else None
    if manager:
        wfh_details = {
            "Start Date": str(req.start_date),
            "End Date": str(req.end_date),
            "Days": (req.end_date - req.start_date).days + 1,
            "Reason": req.reason or ""
        }
        try:
            send_wfh_request_notification(
                manager.email,
                current_user.name,
                wfh_details,
                request=request,
                request_id=db_req.id,
                requestor_email=current_user.email
            )
        except Exception as e:
            # Log the error but don't fail the request creation
            import logging
            logging.error(f"Error sending WFH notification email: {e}")

    return WFHRequestRead.model_validate(db_req)


@router.get("/{request_id}", tags=["wfh"], response_model=WFHRequestRead)
def get_wfh_request(
        request_id: UUID,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    """Get a specific WFH request"""
    req = db.query(WFHRequest).filter(WFHRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="WFH request not found")
    
    # IC can view own, Manager can view direct reports, HR/Admin can view all
    if (str(current_user.id) != str(req.user_id)
        and current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")):
        
        # Check if current user is the manager of the request owner
        request_owner = db.query(User).filter(User.id == req.user_id).first()
        if not request_owner or str(request_owner.manager_id) != str(current_user.id):
            log_permission_denied(
                db,
                current_user.id,
                "get_wfh_request",
                "wfh_request",
                str(request_id),
                message="Insufficient permissions to view WFH request",
                http_status=403)
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return build_wfh_response(req, db)


@router.patch("/{request_id}", tags=["wfh"], response_model=WFHRequestRead)
def partial_update_wfh_request(
        request_id: UUID,
        req_update: WFHRequestPartialUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    """Partially update a WFH request (only reason and comments)"""
    req = db.query(WFHRequest).filter(WFHRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="WFH request not found")

    # Check if the request belongs to the current user
    if str(current_user.id) != str(req.user_id):
        log_permission_denied(
            db,
            current_user.id,
            "update_wfh_request",
            "wfh_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="You can only update your own WFH requests")

    # Update only the allowed fields
    update_data = req_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ['reason', 'comments']:
            setattr(req, field, value)

    try:
        db.commit()
        db.refresh(req)
        
        # Log successful WFH request update
        log_permission_accepted(
            db,
            current_user.id,
            "update_wfh_request",
            "wfh_request",
            str(request_id),
            message="WFH request updated successfully")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Could not update WFH request: {str(e)}")

    return build_wfh_response(req, db)


@router.patch("/{request_id}/approve", tags=["wfh"], response_model=WFHRequestRead)
def approve_wfh_request(
        request_id: UUID,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
        request: Request = None):
    """Approve a WFH request"""
    req = db.query(WFHRequest).filter(WFHRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="WFH request not found")
    
    sstt = req.status if hasattr(req.status, 'value') else str(req.status)
    if (sstt if not hasattr(req.status, 'value') else req.status.value) != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")
    
    # Prevent self-approval, even for Admin/HR
    if str(req.user_id) == str(current_user.id):
        log_permission_denied(
            db,
            current_user.id,
            "approve_wfh_request",
            "wfh_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="You cannot approve your own WFH request.")
    
    # Check if user has permission to approve
    request_owner = db.query(User).filter(User.id == req.user_id).first()
    if (current_user.role_band not in ("HR", "Admin") 
        and current_user.role_title not in ("HR", "Admin") 
        and (not request_owner or str(request_owner.manager_id) != str(current_user.id))):
        log_permission_denied(
            db,
            current_user.id,
            "approve_wfh_request",
            "wfh_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="Only direct manager or HR/Admin can approve")
    
    try:
        req.status = 'approved'
        req.decision_at = datetime.now(timezone.utc)
        req.decided_by = current_user.id
        db.commit()
        db.refresh(req)
        
        # Log successful WFH request approval
        log_permission_accepted(
            db,
            current_user.id,
            "approve_wfh_request",
            "wfh_request",
            str(request_id),
            message="WFH request approved successfully")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Could not approve WFH request: {e}")

    # Send approval notification
    from app.utils.email_utils import send_wfh_approval_notification
    user = db.query(User).filter(User.id == req.user_id).first()
    
    wfh_details = {
        "Start Date": str(req.start_date),
        "End Date": str(req.end_date),
        "Days": str((req.end_date - req.start_date).days + 1)
    }

    try:
        if user:
            send_wfh_approval_notification(
                user.email, wfh_details, approved=True, request=request)
    except Exception as e:
        import logging
        logging.error(f"Error sending WFH approval email: {e}")
    
    return build_wfh_response(req, db)


@router.patch("/{request_id}/reject", tags=["wfh"], response_model=WFHRequestRead)
def reject_wfh_request(
        request_id: UUID,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
        request: Request = None):
    """Reject a WFH request"""
    req = db.query(WFHRequest).filter(WFHRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="WFH request not found")
    
    sstt = req.status if hasattr(req.status, 'value') else str(req.status)
    if (sstt if not hasattr(req.status, 'value') else req.status.value) != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be rejected")
    
    # Prevent self-rejection, even for Admin/HR
    if str(req.user_id) == str(current_user.id):
        log_permission_denied(
            db,
            current_user.id,
            "reject_wfh_request",
            "wfh_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="You cannot reject your own WFH request.")
    
    # Check if user has permission to reject
    request_owner = db.query(User).filter(User.id == req.user_id).first()
    if (current_user.role_band not in ("HR", "Admin") 
        and current_user.role_title not in ("HR", "Admin") 
        and (not request_owner or str(request_owner.manager_id) != str(current_user.id))):
        log_permission_denied(
            db,
            current_user.id,
            "reject_wfh_request",
            "wfh_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="Only direct manager or HR/Admin can reject")
    
    try:
        req.status = 'rejected'
        req.decision_at = datetime.now(timezone.utc)
        req.decided_by = current_user.id
        db.commit()
        db.refresh(req)
        
        log_permission_accepted(
            db,
            current_user.id,
            "reject_wfh_request",
            "wfh_request",
            str(request_id))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Could not reject WFH request: {e}")

    # Send rejection notification
    from app.utils.email_utils import send_wfh_approval_notification
    user = db.query(User).filter(User.id == req.user_id).first()
    
    wfh_details = {
        "Start Date": str(req.start_date),
        "End Date": str(req.end_date),
        "Days": str((req.end_date - req.start_date).days + 1)
    }

    try:
        if user:
            send_wfh_approval_notification(
                user.email, wfh_details, approved=False, request=request)
    except Exception as e:
        import logging
        logging.error(f"Error sending WFH rejection email: {e}")
    
    return build_wfh_response(req, db)


@router.delete("/{request_id}", tags=["wfh"], status_code=204)
def delete_wfh_request(
        request_id: UUID,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)):
    """Delete a WFH request"""
    req = db.query(WFHRequest).filter(WFHRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="WFH request not found")
    
    # Only the request owner, HR, or Admin can delete
    if (str(current_user.id) != str(req.user_id)
        and current_user.role_band not in ("HR", "Admin")
            and current_user.role_title not in ("HR", "Admin")):
        log_permission_denied(
            db,
            current_user.id,
            "delete_wfh_request",
            "wfh_request",
            str(request_id))
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to delete WFH request")
    
    # Log successful WFH request deletion
    log_permission_accepted(
        db,
        current_user.id,
        "delete_wfh_request",
        "wfh_request",
        str(request_id),
        message="WFH request deleted successfully")
    
    db.delete(req)
    db.commit()
    return None