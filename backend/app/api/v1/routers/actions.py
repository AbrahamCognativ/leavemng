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
@router.post("/action/{token}", tags=["actions"])
async def execute_action_via_token(
        token: str,
        action: str = None,  # URL parameter for GET requests
        approval_note: str = None,  # URL parameter for GET requests
        db: Session = Depends(get_db),
        request: Request = None):
    """Execute approve/reject action via secure token from email"""
    
    # Extract approval note and action from URL parameters (GET) or form data (POST)
    extracted_approval_note = None
    extracted_action = None
    
    if request and request.method == "POST":
        # Handle POST request (form submission)
        try:
            form_data = await request.form()
            extracted_approval_note = form_data.get("approval_note", "").strip()
            if not extracted_approval_note:
                extracted_approval_note = None
            extracted_action = form_data.get("action", "").strip()
            
            # Log form submission for audit purposes
            import logging
            logging.info(f"Processing email action token via POST: {token}")
        except Exception as e:
            import logging
            logging.error(f"Error extracting form data: {e}")
            extracted_approval_note = None
            extracted_action = None
    else:
        # Handle GET request (URL parameters)
        extracted_action = action
        extracted_approval_note = approval_note
        
        import logging
        logging.info(f"Processing email action token via GET: {token}, action: {action}")
    
    # Use extracted values
    approval_note = extracted_approval_note
    selected_action = extracted_action
    
    # Find the token first to get request data
    action_token = db.query(ActionToken).filter(
        ActionToken.token == token
    ).first()
    
    if not action_token:
        return HTMLResponse(content=generate_error_page("Invalid or expired token"), status_code=404)
    
    # If this is a GET request without action parameter, show the note input page with request data
    if request and request.method == "GET" and not selected_action:
        # Fetch request data based on resource type
        request_data = get_request_data(action_token, db)
        return HTMLResponse(content=generate_note_input_page(token, request_data), status_code=200)
    
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
    
    # Override action type based on radio button selection if provided
    if selected_action:
        if selected_action == "approve":
            if action_token.resource_type == "wfh_request":
                action_token.action_type = ActionTypeEnum.wfh_approve
            elif action_token.resource_type == "leave_request":
                action_token.action_type = ActionTypeEnum.leave_approve
        elif selected_action == "reject":
            if action_token.resource_type == "wfh_request":
                action_token.action_type = ActionTypeEnum.wfh_reject
            elif action_token.resource_type == "leave_request":
                action_token.action_type = ActionTypeEnum.leave_reject
    
    try:
        if action_token.resource_type == "wfh_request":
            return process_wfh_action(action_token, approver, db, request, approval_note)
        elif action_token.resource_type == "leave_request":
            return process_leave_action(action_token, approver, db, request, approval_note)
        else:
            return HTMLResponse(content=generate_error_page("Invalid resource type"), status_code=400)
    except Exception as e:
        db.rollback()
        return HTMLResponse(content=generate_error_page(f"Error processing request: {str(e)}"), status_code=500)


def process_wfh_action(action_token: ActionToken, approver: User, db: Session, request: Request, approval_note: str = None):
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
    wfh_request.approval_note = approval_note
    
    # Log WFH decision for audit purposes
    import logging
    logging.info(f"WFH request {wfh_request.id} {'approved' if is_approve else 'rejected'}")
    
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
    
    # Add approval note to details if provided
    if approval_note:
        wfh_details["Note"] = approval_note
    
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


def process_leave_action(action_token: ActionToken, approver: User, db: Session, request: Request, approval_note: str = None):
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
    leave_request.approval_note = approval_note
    
    # Log leave decision for audit purposes
    import logging
    logging.info(f"Leave request {leave_request.id} {'approved' if is_approve else 'rejected'}")
    
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
    
    # Add approval note to details if provided
    if approval_note:
        leave_details["Note"] = approval_note
    
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


def get_request_data(action_token: ActionToken, db: Session) -> dict:
    """Fetch request data based on the action token's resource type"""
    try:
        if action_token.resource_type == "wfh_request":
            wfh_request = db.query(WFHRequest).filter(WFHRequest.id == action_token.resource_id).first()
            if wfh_request:
                user = db.query(User).filter(User.id == wfh_request.user_id).first()
                
                # Calculate days for WFH request
                days = 1  # Default to 1 day
                if wfh_request.start_date and wfh_request.end_date:
                    days = (wfh_request.end_date - wfh_request.start_date).days + 1
                
                return {
                    'employee_name': user.name if user else 'Unknown User',
                    'request_type': 'Work From Home',
                    'start_date': wfh_request.start_date.strftime('%Y-%m-%d') if wfh_request.start_date else 'N/A',
                    'end_date': wfh_request.end_date.strftime('%Y-%m-%d') if wfh_request.end_date else 'N/A',
                    'days': str(days),
                    'reason': wfh_request.reason if wfh_request.reason else 'No reason provided'
                }
        
        elif action_token.resource_type == "leave_request":
            leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == action_token.resource_id).first()
            if leave_request:
                user = db.query(User).filter(User.id == leave_request.user_id).first()
                leave_type = db.query(LeaveType).filter(LeaveType.id == leave_request.leave_type_id).first()
                return {
                    'employee_name': user.name if user else 'Unknown User',
                    'request_type': leave_type.description if leave_type else 'Leave Request',
                    'start_date': leave_request.start_date.strftime('%Y-%m-%d') if leave_request.start_date else 'N/A',
                    'end_date': leave_request.end_date.strftime('%Y-%m-%d') if leave_request.end_date else 'N/A',
                    'days': str(leave_request.total_days) if leave_request.total_days else 'N/A',
                    'reason': leave_request.comments if leave_request.comments else 'No reason provided'
                }
            
    except Exception as e:
        import logging
        logging.error(f"Error fetching request data: {e}")
    
    # Return default data if anything goes wrong
    return {
        'employee_name': 'Unknown User',
        'request_type': 'Request',
        'start_date': 'N/A',
        'end_date': 'N/A',
        'days': 'N/A',
        'reason': 'Unable to load request details'
    }


def generate_note_input_page(token: str, request_data: dict = None) -> str:
    """Generate simple decision page HTML matching success page style"""
    # Default placeholder data
    if not request_data:
        request_data = {
            'employee_name': 'Loading...',
            'request_type': 'Leave Request',
            'start_date': 'Loading...',
            'end_date': 'Loading...',
            'days': 'Loading...',
            'reason': 'Loading...'
        }
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Review & Submit Decision</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h1 {{ margin: 0; color: #333; font-size: 24px; font-weight: bold; }}
            .header p {{ margin: 10px 0 0 0; color: #666; font-size: 16px; }}
            .request-details {{ background: #f8f9fa; padding: 20px; border-radius: 6px; margin-bottom: 25px; }}
            .request-details h3 {{ margin: 0 0 15px 0; color: #333; font-size: 18px; font-weight: bold; }}
            .detail-row {{ display: flex; justify-content: space-between; margin: 8px 0; padding: 4px 0; border-bottom: 1px solid #e9ecef; }}
            .detail-label {{ font-weight: bold; color: #495057; }}
            .detail-value {{ color: #333; }}
            .form-group {{ margin-bottom: 20px; }}
            .form-group label {{ display: block; font-weight: bold; margin-bottom: 8px; color: #333; font-size: 14px; }}
            .form-group textarea {{ width: 100%; height: 80px; padding: 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; font-family: inherit; box-sizing: border-box; resize: vertical; }}
            .radio-group {{ display: flex; gap: 15px; margin-bottom: 25px; }}
            .radio-option {{ flex: 1; }}
            .radio-option input[type="radio"] {{ display: none; }}
            .radio-option label {{ display: block; padding: 12px; border: 2px solid #e9ecef; border-radius: 4px; text-align: center; cursor: pointer; font-weight: bold; font-size: 14px; }}
            .radio-option input[type="radio"]:checked + label {{ border-color: #28a745; background: #f8fff8; color: #28a745; }}
            .radio-option.reject input[type="radio"]:checked + label {{ border-color: #dc3545; background: #fff8f8; color: #dc3545; }}
            .button-group {{ text-align: center; }}
            .btn {{ padding: 12px 24px; border: none; border-radius: 4px; font-weight: bold; font-size: 14px; cursor: pointer; text-decoration: none; display: inline-block; text-align: center; }}
            .btn-primary {{ background: #0f6cbd; color: white; }}
            .btn-primary:hover {{ background: #0d5aa7; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Review & Submit Decision</h1>
                <p>Please review the request details and submit your decision</p>
            </div>
            
            <div class="request-details">
                <h3>Request Details:</h3>
                <div class="detail-row">
                    <span class="detail-label">Employee:</span>
                    <span class="detail-value">{request_data.get('employee_name', 'Loading...')}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Type:</span>
                    <span class="detail-value">{request_data.get('request_type', 'Loading...')}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Start Date:</span>
                    <span class="detail-value">{request_data.get('start_date', 'Loading...')}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">End Date:</span>
                    <span class="detail-value">{request_data.get('end_date', 'Loading...')}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Days:</span>
                    <span class="detail-value">{request_data.get('days', 'Loading...')}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Comments:</span>
                    <span class="detail-value">{request_data.get('reason', 'Loading...')}</span>
                </div>
            </div>
            
            <div class="form-group">
                <label for="approval_note">Note (Optional):</label>
                <textarea id="approval_note" name="approval_note" placeholder="Add a note for your decision..."></textarea>
            </div>
            
            <div class="radio-group">
                <div class="radio-option">
                    <input type="radio" id="approve" name="decision" value="approve" checked>
                    <label for="approve">APPROVE</label>
                </div>
                <div class="radio-option reject">
                    <input type="radio" id="reject" name="decision" value="reject">
                    <label for="reject">REJECT</label>
                </div>
            </div>
            
            <div class="button-group">
                <button type="button" class="btn btn-primary" onclick="submitDecision()">
                    Submit Decision
                </button>
            </div>
            
            <div class="footer">
                <p><strong>Leave Management System</strong></p>
            </div>
        </div>
        
        <script>
            function submitDecision() {{
                const note = document.getElementById('approval_note').value.trim();
                const decision = document.querySelector('input[name="decision"]:checked').value;
                const url = new URL(window.location.href);
                url.searchParams.set('action', decision);
                if (note) {{
                    url.searchParams.set('approval_note', note);
                }}
                window.location.href = url.toString();
            }}
        </script>
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