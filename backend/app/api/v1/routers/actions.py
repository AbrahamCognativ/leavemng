from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.models.action_token import ActionToken, ActionTypeEnum
from app.models.wfh_request import WFHRequest
from app.models.leave_request import LeaveRequest
from app.models.user import User
from app.models.leave_balance import LeaveBalance
from app.models.leave_type import LeaveType
from app.db.session import get_db
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from app.deps.permissions import log_permission_accepted, log_permission_denied
import secrets

router = APIRouter()


def generate_action_tokens(resource_type: str, resource_id: str, approver_id: str, db: Session) -> dict:
    """Generate secure tokens for approve/reject actions"""
    tokens = {}
    
    if resource_type == "wfh_request":
        action_types = [ActionTypeEnum.wfh_approve, ActionTypeEnum.wfh_reject]
    elif resource_type == "leave_request":
        action_types = [ActionTypeEnum.leave_approve, ActionTypeEnum.leave_reject]
    else:
        raise ValueError(f"Unsupported resource type: {resource_type}")
    
    for action_type in action_types:
        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=72)  # 72 hour expiry (naive datetime to match database)
        
        # Create token record
        action_token = ActionToken(
            resource_type=resource_type,
            resource_id=resource_id,
            approver_id=approver_id,
            action_type=action_type,
            token=token,
            expires_at=expires_at
        )
        db.add(action_token)
        
        # Store token with simplified key
        action_key = action_type.value.split('_')[1]  # "approve" or "reject"
        tokens[action_key] = token
    
    db.commit()
    return tokens


@router.get("/action/{token}", tags=["actions"])
def execute_action_via_token(
        token: str,
        db: Session = Depends(get_db),
        request: Request = None):
    """Execute approve/reject action via secure token from email"""
    
    # Find the token
    action_token = db.query(ActionToken).filter(
        ActionToken.token == token
    ).first()
    
    if not action_token:
        return HTMLResponse(content=generate_error_page("Invalid or expired token"), status_code=404)
    
    # Check if token is expired (handle timezone-aware vs naive datetime)
    current_time = datetime.now(timezone.utc)
    expires_at = action_token.expires_at
    if expires_at.tzinfo is None:
        # If stored datetime is naive, make current time naive for comparison
        current_time = datetime.now()
    
    if expires_at < current_time:
        return HTMLResponse(content=generate_error_page("Token has expired"), status_code=400)
    
    # Check if token has been used
    if action_token.used:
        return HTMLResponse(content=generate_error_page("Token has already been used"), status_code=400)
    
    # Get approver user
    approver = db.query(User).filter(User.id == action_token.approver_id).first()
    if not approver:
        return HTMLResponse(content=generate_error_page("Approver not found"), status_code=404)
    
    try:
        if action_token.resource_type == "wfh_request":
            return process_wfh_action(action_token, approver, db, request)
        elif action_token.resource_type == "leave_request":
            return process_leave_action(action_token, approver, db, request)
        else:
            return HTMLResponse(content=generate_error_page("Invalid resource type"), status_code=400)
    except Exception as e:
        db.rollback()
        return HTMLResponse(content=generate_error_page(f"Error processing request: {str(e)}"), status_code=500)


def process_wfh_action(action_token: ActionToken, approver: User, db: Session, request: Request):
    """Process WFH approve/reject action"""
    from app.utils.email_utils import send_wfh_approval_notification
    
    # Get the WFH request
    wfh_request = db.query(WFHRequest).filter(
        WFHRequest.id == action_token.resource_id
    ).first()
    
    if not wfh_request:
        return HTMLResponse(content=generate_error_page("WFH request not found"), status_code=404)
    
    # Check if request is still pending
    status = wfh_request.status.value if hasattr(wfh_request.status, 'value') else str(wfh_request.status)
    if status != "pending":
        return HTMLResponse(content=generate_error_page("WFH request is no longer pending"), status_code=400)
    
    # Verify approver still has permission
    request_owner = db.query(User).filter(User.id == wfh_request.user_id).first()
    if (approver.role_band not in ("HR", "Admin") 
        and approver.role_title not in ("HR", "Admin") 
        and (not request_owner or str(request_owner.manager_id) != str(approver.id))):
        return HTMLResponse(content=generate_error_page("Approver no longer has permission"), status_code=403)
    
    # Prevent self-approval
    if str(wfh_request.user_id) == str(approver.id):
        return HTMLResponse(content=generate_error_page("Cannot approve/reject your own request"), status_code=403)
    
    # Update WFH request status
    is_approve = action_token.action_type == ActionTypeEnum.wfh_approve
    wfh_request.status = 'approved' if is_approve else 'rejected'
    wfh_request.decision_at = datetime.now(timezone.utc)
    wfh_request.decided_by = approver.id
    
    # Mark token as used
    action_token.used = True
    
    db.commit()
    db.refresh(wfh_request)
    
    # Log the action
    action_name = "approve_wfh_request" if is_approve else "reject_wfh_request"
    log_permission_accepted(
        db,
        approver.id,
        action_name,
        "wfh_request",
        str(wfh_request.id),
        message=f"WFH request {'approved' if is_approve else 'rejected'} via email token")
    
    # Send notification to employee
    employee = db.query(User).filter(User.id == wfh_request.user_id).first()
    
    wfh_details = {
        "Start Date": str(wfh_request.start_date),
        "End Date": str(wfh_request.end_date),
        "Days": str((wfh_request.end_date - wfh_request.start_date).days + 1),
        "Decided By": approver.name
    }
    
    try:
        if employee:
            send_wfh_approval_notification(
                employee.email, 
                wfh_details, 
                approved=is_approve, 
                request=request)
    except Exception as e:
        import logging
        logging.error(f"Error sending WFH notification email: {e}")
    
    # Return success page
    action_text = "approved" if is_approve else "rejected"
    return HTMLResponse(content=generate_success_page(
        "WFH Request", action_text, employee.name if employee else "Unknown", 
        wfh_details, approver.name, wfh_request.decision_at
    ))


def process_leave_action(action_token: ActionToken, approver: User, db: Session, request: Request):
    """Process leave approve/reject action"""
    from app.utils.email_utils import send_leave_approval_notification
    
    # Get the leave request
    leave_request = db.query(LeaveRequest).filter(
        LeaveRequest.id == action_token.resource_id
    ).first()
    
    if not leave_request:
        return HTMLResponse(content=generate_error_page("Leave request not found"), status_code=404)
    
    # Check if request is still pending
    status = leave_request.status.value if hasattr(leave_request.status, 'value') else str(leave_request.status)
    if status != "pending":
        return HTMLResponse(content=generate_error_page("Leave request is no longer pending"), status_code=400)
    
    # Verify approver still has permission
    request_owner = db.query(User).filter(User.id == leave_request.user_id).first()
    if (approver.role_band not in ("HR", "Admin") 
        and approver.role_title not in ("HR", "Admin") 
        and (not request_owner or str(request_owner.manager_id) != str(approver.id))):
        return HTMLResponse(content=generate_error_page("Approver no longer has permission"), status_code=403)
    
    # Prevent self-approval
    if str(leave_request.user_id) == str(approver.id):
        return HTMLResponse(content=generate_error_page("Cannot approve/reject your own request"), status_code=403)
    
    # Update leave request status
    is_approve = action_token.action_type == ActionTypeEnum.leave_approve
    leave_request.status = 'approved' if is_approve else 'rejected'
    leave_request.decision_at = datetime.now(timezone.utc)
    leave_request.decided_by = approver.id
    
    # Handle leave balance for rejections
    if not is_approve:
        leave_balance = db.query(LeaveBalance).filter(
            LeaveBalance.user_id == leave_request.user_id,
            LeaveBalance.leave_type_id == leave_request.leave_type_id
        ).first()
        if leave_balance:
            leave_balance.balance_days += Decimal(str(leave_request.total_days))
    
    # Mark token as used
    action_token.used = True
    
    db.commit()
    db.refresh(leave_request)
    
    # Log the action
    action_name = "approve_leave_request" if is_approve else "reject_leave_request"
    log_permission_accepted(
        db,
        approver.id,
        action_name,
        "leave_request",
        str(leave_request.id),
        message=f"Leave request {'approved' if is_approve else 'rejected'} via email token")
    
    # Send notification to employee
    employee = db.query(User).filter(User.id == leave_request.user_id).first()
    
    # Get leave type details
    leave_type = db.query(LeaveType).filter(LeaveType.id == leave_request.leave_type_id).first()
    leave_type_name = leave_type.custom_code if leave_type and leave_type.code.value == 'custom' else (
        leave_type.code.value.title() + ' Leave' if leave_type else 'Leave')
    
    leave_details = {
        "Type": leave_type_name,
        "Start Date": str(leave_request.start_date),
        "End Date": str(leave_request.end_date),
        "Days": str(leave_request.total_days),
        "Decided By": approver.name
    }
    
    try:
        if employee:
            send_leave_approval_notification(
                employee.email, 
                leave_details, 
                approved=is_approve, 
                request=request)
    except Exception as e:
        import logging
        logging.error(f"Error sending leave notification email: {e}")
    
    # Return success page
    action_text = "approved" if is_approve else "rejected"
    return HTMLResponse(content=generate_success_page(
        "Leave Request", action_text, employee.name if employee else "Unknown", 
        leave_details, approver.name, leave_request.decision_at
    ))


def generate_success_page(request_type: str, action: str, employee_name: str, details: dict, approver_name: str, decision_time: datetime) -> str:
    """Generate success page HTML"""
    color = "#28a745" if action == "approved" else "#dc3545"
    icon = "✓" if action == "approved" else "✗"
    
    detail_rows = ''.join(
        f'<div class="detail-row"><span class="detail-label">{k}:</span><span>{v}</span></div>'
        for k, v in details.items()
    )
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{request_type} {action.title()}</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .status-icon {{ font-size: 48px; color: {color}; margin-bottom: 10px; }}
            .status-text {{ font-size: 24px; color: {color}; font-weight: bold; margin: 0; }}
            .details {{ background: #f8f9fa; padding: 20px; border-radius: 6px; margin: 20px 0; }}
            .detail-row {{ display: flex; justify-content: space-between; margin: 8px 0; padding: 4px 0; border-bottom: 1px solid #e9ecef; }}
            .detail-label {{ font-weight: bold; color: #495057; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="status-icon">{icon}</div>
                <h1 class="status-text">{request_type} {action.title()}</h1>
            </div>
            
            <p style="text-align: center; font-size: 16px; color: #495057; margin-bottom: 30px;">
                The {request_type.lower()} has been successfully {action}.
            </p>
            
            <div class="details">
                <h3 style="margin-top: 0; color: #495057;">Request Details:</h3>
                <div class="detail-row">
                    <span class="detail-label">Employee:</span>
                    <span>{employee_name}</span>
                </div>
                {detail_rows}
                <div class="detail-row">
                    <span class="detail-label">Decision Time:</span>
                    <span>{decision_time.strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
                </div>
            </div>
            
            <div class="footer">
                <p>The employee has been notified of this decision via email.</p>
                <p><strong>Leave Management System</strong></p>
            </div>
        </div>
    </body>
    </html>
    """


def generate_error_page(error_message: str) -> str:
    """Generate compact error page HTML with helpful information"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Action Failed</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="margin: 0; padding: 0; background: #f5f5f5; font-family: Arial, sans-serif;">
        <div style="max-width: 500px; margin: 20px auto; background: white; padding: 30px; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center;">
            <div style="font-size: 48px; color: #dc3545; margin-bottom: 16px;">⚠️</div>
            <h1 style="font-size: 20px; color: #dc3545; font-weight: bold; margin: 0 0 16px 0;">Action Failed</h1>
            <p style="font-size: 16px; color: #495057; margin: 0 0 20px 0;">{error_message}</p>
            
            <div style="background: #f8f9fa; padding: 16px; border-radius: 4px; margin: 20px 0; text-align: left;">
                <p style="margin: 0; font-size: 14px; color: #6c757d;">
                    <strong>Common Issues:</strong><br>
                    • Link has expired (72 hour limit)<br>
                    • Link has already been used<br>
                    • Request is no longer pending<br>
                    • You no longer have permission to approve this request
                </p>
            </div>
            
            <p style="font-size: 12px; color: #6c757d; margin: 16px 0 0 0;">
                If you need assistance, please contact your system administrator.
            </p>
        </div>
    </body>
    </html>
    """