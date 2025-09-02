from app.settings import get_settings
import os
import logging
import ssl
import urllib3
from typing import Optional
from fastapi import Request, HTTPException
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_email_background(
        subject: str,
        body: str,
        to_emails: list[str],
        from_email: Optional[str] = None,
        html: Optional[str] = None,
        attachments: Optional[list] = None):
    """
    Send an email using SendGrid settings from environment variables. Use this for background jobs where FastAPI Request is not available.
    
    Args:
        attachments: List of tuples (file_path, filename) for attachments
    """
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    if not sendgrid_api_key:
        logging.error("SENDGRID_API_KEY not configured in environment.")
        raise Exception("Email service not configured.")

    # from_email = from_email or os.environ.get('EMAIL_USER') or os.environ.get('EMAIL_HOST')
    # if not from_email:
    #     logging.error("No from_email configured in environment.")
    #     raise Exception("Sender email not configured.")

    message = Mail(
        from_email='info@cognativ.com',
        to_emails=to_emails,
        subject=subject,
        plain_text_content=body,
        html_content=html or body
    )
    
    # Add attachments if provided
    if attachments:
        import base64
        from sendgrid.helpers.mail import Attachment, FileContent, FileName, FileType, Disposition
        
        for file_path, filename in attachments:
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                encoded_file = base64.b64encode(data).decode()
                
                # Determine file type from extension
                file_type = "application/pdf"
                if filename.lower().endswith('.pdf'):
                    file_type = "application/pdf"
                elif filename.lower().endswith(('.jpg', '.jpeg')):
                    file_type = "image/jpeg"
                elif filename.lower().endswith('.png'):
                    file_type = "image/png"
                elif filename.lower().endswith('.docx'):
                    file_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                
                attachment = Attachment(
                    FileContent(encoded_file),
                    FileName(filename),
                    FileType(file_type),
                    Disposition('attachment')
                )
                message.attachment = attachment
            except Exception as e:
                logging.error(f"Failed to attach file {filename}: {e}")
    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        if response.status_code >= 400:
            logging.error(
                f"SendGrid error: {response.status_code} {response.body}")
            raise Exception("Could not send email.")
    except (OSError, AttributeError, TypeError) as e:
        logging.error(f"Email sending failed: {e}")
        raise Exception(f"Could not send email: {e}")


def send_email(
        subject: str,
        body: str,
        to_emails: list[str],
        request: Request,
        from_email: Optional[str] = None,
        html: Optional[str] = None):
    """
    Send an email using SendGrid settings from FastAPI app.state.settings.
    Args:
        subject: Email subject
        body: Plain text body
        to_emails: List of recipient emails
        request: FastAPI Request (to access app.state.settings)
        from_email: Optional sender override
        html: Optional HTML body
    """
    settings = request.app.state.settings
    sendgrid_api_key = getattr(settings, 'SENDGRID_API_KEY', None)
    if not sendgrid_api_key:
        logging.error("SENDGRID_API_KEY not configured in settings.")
        raise HTTPException(status_code=500,
                            detail="Email service not configured.")

    from_email = from_email or getattr(
        settings, 'EMAIL_USER', None) or getattr(
        settings, 'EMAIL_HOST', None)
    if not from_email:
        logging.error("No from_email configured.")
        raise HTTPException(
            status_code=500,
            detail="Sender email not configured.")

    # SendGrid expects a single email or a list
    message = Mail(
        from_email=from_email,
        to_emails=to_emails,
        subject=subject,
        plain_text_content=body,
        html_content=html or body
    )
    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        if response.status_code >= 400:
            logging.error(
                f"SendGrid error: {response.status_code} {response.body}")
            raise HTTPException(
                status_code=502,
                detail="Could not send email.")
    except (OSError, AttributeError, TypeError) as e:
        logging.error(f"Email sending failed: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Could not send email: {e}")


def send_invite_email(
        to_email: str,
        to_name: str,
        invite_link: str,
        password: str,
        request: Request):
    subject = "Invite - Welcome to Cognativ Technology Ltd"
    body = (
        f"Hello {to_name},\n\n"
        f"You have been invited to join the Leave Management System.\n"
        f"Please use the following link to register:\n{invite_link}\n\n"
        f"Your temporary password is: {password}\n\nBest Regards."
    )
    html = f"""
    <html>
    <body style='font-family: Arial, sans-serif; background: #f9f9f9; padding: 24px;'>
      <div style='max-width: 480px; margin: auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #eee; padding: 32px;'>
        <h2 style='color: #2d6cdf; margin-top: 0;'>You're Invited!</h2>
        <p style='font-size: 16px; color: #333;'>
          You have been invited to join the <b>Leave Management System</b>.<br>
          Please click the button below to accept your invitation and register your account.
        </p>
        <a href='{invite_link}' style='display: inline-block; margin: 24px 0 8px 0; padding: 12px 32px; background: #2d6cdf; color: #fff; border-radius: 4px; text-decoration: none; font-size: 16px; font-weight: bold;'>
          Accept Invitation
        </a>
        <p style='font-size: 15px; color: #333; margin-top: 24px;'>
          <b>Your temporary password is:</b> <span style='background:#f4f4f4; padding:4px 8px; border-radius:4px; font-family:monospace;'>{password}</span>
        </p>
        <p style='font-size: 13px; color: #888; margin-top: 16px;'>
          If the button above doesn't work, copy and paste this link into your browser:<br>
          <a href='{invite_link}' style='color: #2d6cdf;'>{invite_link}</a>
        </p>
        <p style='font-size: 15px; color: #333;'>Best Regards,<br>Leave Management System Team</p>
      </div>
    </body>
    </html>
    """
    send_email(subject, body, [to_email], request=request, html=html)


def send_leave_request_notification(
        to_email: str,
        requester_name: str,
        leave_details: dict,
        request: Request,
        request_id: int = None,
        requestor_email: str = None):
    """
    Send a leave request notification with approve/reject links and a table of leave details.
    leave_details should be a dict with keys/values for the table.
    Also sends a confirmation email to the leave requestor if requestor_email is provided.
    """
    subject = f"New Leave Request Submitted - {requester_name}"
    # Fallback for plain text body
    plain_body = f"Hello,\n\n{requester_name} has submitted a leave request.\nDetails: {leave_details}\n\nPlease review and approve or reject the request."

    # HTML Table for leave details
    if isinstance(leave_details, dict):
        table_rows = ''.join(
            f'<tr><td style=\"padding:4px 8px;border:1px solid #ddd;\"><b>{k}</b></td><td style=\"padding:4px 8px;border:1px solid #ddd;\">{v}</td></tr>' for k,
            v in leave_details.items())
        details_table = f'<table style=\"border-collapse:collapse;margin:12px 0;\">{table_rows}</table>'
    else:
        details_table = f'<pre>{leave_details}</pre>'

    # Approve/Reject links (PATCH endpoints, shown as buttons)
    approve_url = reject_url = "#"
    if request_id:
        settings = get_settings()
        base_url = settings.REGISTER_URL.rstrip('/')
        approve_url = f"{base_url}/api/v1/leave/{request_id}/approve"
        reject_url = f"{base_url}/api/v1/leave/{request_id}/reject"
    approve_btn = f'<a href="{approve_url}" style="background:#28a745;color:#fff;padding:8px 16px;text-decoration:none;border-radius:4px;margin-right:8px;">Approve</a>'
    reject_btn = f'<a href="{reject_url}" style="background:#dc3545;color:#fff;padding:8px 16px;text-decoration:none;border-radius:4px;">Reject</a>'

    html = f'''
    <div style="font-family:sans-serif;max-width:600px;">
        <p>Hello,</p>
        <p><b>{requester_name}</b> has submitted a leave request. Please review the details below:</p>
        {details_table}
        <p>{approve_btn}{reject_btn}</p>
        <p style="margin-top:24px;">Best Regards,<br/>Leave Management System</p>
    </div>
    '''
    send_email(subject, plain_body, [to_email], request=request, html=html)

    # Send confirmation to leave requestor
    if requestor_email:
        confirm_subject = "Your Leave Request Has Been Submitted"
        confirm_body = f"Hello {requester_name},\n\nYour leave request has been submitted for review. You will be notified once it is approved or rejected.\n\nDetails: {leave_details}\n\nBest Regards."
        confirm_html = f'''
        <div style="font-family:sans-serif;max-width:600px;">
            <p>Hello {requester_name},</p>
            <p>Your leave request has been <b>submitted for review</b>. You will be notified once it is approved or rejected.</p>
            {details_table}
            <p style="margin-top:24px;">Best Regards,<br/>Leave Management System</p>
        </div>
        '''
        send_email(
            confirm_subject,
            confirm_body,
            [requestor_email],
            request=request,
            html=confirm_html)


def send_leave_approval_notification(
        to_email: str,
        leave_details,
        approved: bool,
        request: Request):
    status = "approved" if approved else "rejected"
    subject = f"Your Leave Request has been {status.title()}"

    # Parse leave_details if it's a string in 'Key: Value, Key: Value' format
    parsed_details = None
    if isinstance(leave_details, dict):
        parsed_details = leave_details
    elif isinstance(leave_details, str):
        # Try to parse string to dict
        try:
            items = [item.strip() for item in leave_details.split(',')]
            parsed_details = dict()
            for item in items:
                if ':' in item:
                    k, v = item.split(':', 1)
                    parsed_details[k.strip()] = v.strip()
            if not parsed_details:
                parsed_details = None
        except Exception:
            parsed_details = None

    if parsed_details:
        table_rows = ''.join(
            f'<tr><td style="padding:4px 8px;border:1px solid #ddd;"><b>{k}</b></td><td style="padding:4px 8px;border:1px solid #ddd;">{v}</td></tr>' for k,
            v in parsed_details.items())
        details_table = f'<table style="border-collapse:collapse;margin:12px 0;">{table_rows}</table>'
        plain_details = '\n'.join(
            [f"{k}: {v}" for k, v in parsed_details.items()])
    else:
        details_table = f'<pre>{leave_details}</pre>'
        plain_details = str(leave_details)

    # Color bar for status
    color = "#28a745" if approved else "#dc3545"
    status_text = f'<span style="color:{color};font-weight:bold;">{status.title()}</span>'
    html = f'''
    <div style="font-family:sans-serif;max-width:600px;">
        <p>Hello,</p>
        <p>Your leave request has been {status_text}.</p>
        {details_table}
        <div style="margin:16px 0;height:8px;background:{color};border-radius:4px;"></div>
        <p style="margin-top:24px;">Best Regards,<br/>Leave Management System</p>
    </div>
    '''
    body = f"Hello,\n\nYour leave request has been {status}.\n\nDetails:\n{plain_details}\n\nBest Regards."
    send_email(subject, body, [to_email], request=request, html=html)


def send_leave_sick_doc_reminder(
        to_email: str,
        remaining_hours: str,
        leave_details: dict):
    subject = "Reminder: Please Upload Sick Leave Document"
    body = f"Hello,\n\nPlease upload a doctor's note or medical certificate to support your sick leave request.\n\nDetails:\n{leave_details}\n\nBest Regards."
    # Format leave_details dict as HTML table rows
    table_rows = "".join(
        f'<tr><td style="padding:4px 8px;border:1px solid #ddd;">{key}</td><td style="padding:4px 8px;border:1px solid #ddd;">{value}</td></tr>'
        for key, value in leave_details.items()
    )
    html = f'''
    <div style="font-family:sans-serif;max-width:600px;">
        <p>Hello,</p>
        <p>You have {remaining_hours} hours left to <b>upload a doctor's note or medical certificate</b> to support your sick leave request.</p>
        <p style="margin-top:24px;">Details:</p>
        <table style="border-collapse:collapse;margin:12px 0;">
            <tr><th style="padding:4px 8px;border:1px solid #ddd;">Key</th><th style="padding:4px 8px;border:1px solid #ddd;">Value</th></tr>
            {table_rows}
        </table>
        <p style="margin-top:24px;">Best Regards,<br/>Leave Management System</p>
    </div>
    '''
    send_email_background(subject, body, [to_email], html=html)


def send_leave_auto_approval_notification(
        to_email: str,
        leave_details: dict,
        approved: bool = True):
    status = "approved" if approved else "rejected"
    subject = f"Your Leave Request has been Auto-{status.title()}"

    # Format leave_details dict as HTML table rows
    table_rows = "".join(
        f'<tr><td style="padding:4px 8px;border:1px solid #ddd;">{key}</td><td style="padding:4px 8px;border:1px solid #ddd;">{value}</td></tr>'
        for key, value in leave_details.items()
    )
    html = f'''
    <div style="font-family:sans-serif;max-width:600px;">
        <p>Hello,</p>
        <p>Your leave request has been Auto-{status.title()}.</p>
        <p style="margin-top:24px;">Details:</p>
        <table style="border-collapse:collapse;margin:12px 0;">
            <tr><th style="padding:4px 8px;border:1px solid #ddd;">Key</th><th style="padding:4px 8px;border:1px solid #ddd;">Value</th></tr>
            {table_rows}
        </table>
        <p style="margin-top:24px;">Best Regards,<br/>Leave Management System</p>
    </div>
    '''

    body = f"Hello,\n\nYour leave request has been Auto-{status}.\n\nDetails:\n{leave_details}\n\nBest Regards."
    send_email_background(subject, body, [to_email], html=html)


def send_wfh_request_notification_with_tokens(
        to_email: str,
        requester_name: str,
        wfh_details: dict,
        request: Request,
        request_id: int = None,
        requestor_email: str = None,
        approve_token: str = None,
        reject_token: str = None):
    """
    Send a WFH request notification with secure approve/reject token links.
    wfh_details should be a dict with keys/values for the table.
    Also sends a confirmation email to the WFH requestor if requestor_email is provided.
    """
    subject = f"New Work From Home Request Submitted - {requester_name}"
    # Fallback for plain text body
    plain_body = f"Hello,\n\n{requester_name} has submitted a work from home request.\nDetails: {wfh_details}\n\nPlease review and approve or reject the request."

    # HTML Table for WFH details
    if isinstance(wfh_details, dict):
        table_rows = ''.join(
            f'<tr><td style=\"padding:8px 12px;border:1px solid #ddd;background:#f8f9fa;\"><b>{k}</b></td><td style=\"padding:8px 12px;border:1px solid #ddd;\">{v}</td></tr>' for k,
            v in wfh_details.items())
        details_table = f'<table style=\"border-collapse:collapse;margin:16px 0;width:100%;\">{table_rows}</table>'
    else:
        details_table = f'<pre>{wfh_details}</pre>'

    # Secure Approve/Reject links using tokens
    approve_url = reject_url = "#"
    if approve_token and reject_token:
        settings = get_settings()
        base_url = settings.SITE_URL.rstrip('/')
        approve_url = f"{base_url}/api/v1/actions/action/{approve_token}"
        reject_url = f"{base_url}/api/v1/actions/action/{reject_token}"

    # Enhanced button styling for better email client compatibility
    approve_btn = f'''
    <a href="{approve_url}" style="
        display: inline-block;
        background: #28a745;
        color: #ffffff;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 6px;
        margin: 8px 8px 8px 0;
        font-weight: bold;
        font-size: 14px;
        border: 2px solid #28a745;
        text-align: center;
        min-width: 100px;
    ">✓ APPROVE</a>'''
    
    reject_btn = f'''
    <a href="{reject_url}" style="
        display: inline-block;
        background: #dc3545;
        color: #ffffff;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 6px;
        margin: 8px 0;
        font-weight: bold;
        font-size: 14px;
        border: 2px solid #dc3545;
        text-align: center;
        min-width: 100px;
    ">✗ REJECT</a>'''

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>WFH Request - {requester_name}</title>
    </head>
    <body style="margin: 0; padding: 0; background: #f5f5f5; font-family: Arial, sans-serif;">
        <div style="max-width: 500px; margin: 10px auto; background: #ffffff; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: #2d6cdf; color: white; padding: 16px; text-align: center; border-radius: 6px 6px 0 0;">
                <h2 style="margin: 0; font-size: 18px;">🏠 WFH Request</h2>
            </div>
            
            <!-- Content -->
            <div style="padding: 20px;">
                <p style="margin: 0 0 12px 0; color: #333;">
                    <strong>{requester_name}</strong> requests work from home approval:
                </p>
                
                <!-- Compact Details -->
                <div style="background: #f8f9fa; padding: 12px; border-radius: 4px; margin: 12px 0; font-size: 14px;">
                    {details_table}
                </div>
                
                <!-- Action Buttons - Prominent Position -->
                <div style="text-align: center; margin: 20px 0;">
                    {approve_btn}
                    {reject_btn}
                </div>
                
                <p style="font-size: 11px; color: #6c757d; text-align: center; margin: 12px 0 0 0;">
                    Links expire in 72 hours • Single use only
                </p>
            </div>
        </div>
    </body>
    </html>
    '''
    
    send_email(subject, plain_body, [to_email], request=request, html=html)

    # Send confirmation to WFH requestor
    if requestor_email:
        confirm_subject = "Your Work From Home Request Has Been Submitted"
        confirm_body = f"Hello {requester_name},\n\nYour work from home request has been submitted for review. You will be notified once it is approved or rejected.\n\nDetails: {wfh_details}\n\nBest Regards."
        confirm_html = f'''
        <div style="font-family:sans-serif;max-width:600px;">
            <p>Hello {requester_name},</p>
            <p>Your work from home request has been <b>submitted for review</b>. You will be notified once it is approved or rejected.</p>
            {details_table}
            <p style="margin-top:24px;">Best Regards,<br/>Leave Management System</p>
        </div>
        '''
        send_email(
            confirm_subject,
            confirm_body,
            [requestor_email],
            request=request,
            html=confirm_html)


def send_leave_request_notification_with_tokens(
        to_email: str,
        requester_name: str,
        leave_details: dict,
        request: Request,
        request_id: int = None,
        requestor_email: str = None,
        approve_token: str = None,
        reject_token: str = None):
    """
    Send a leave request notification with secure approve/reject token links.
    leave_details should be a dict with keys/values for the table.
    Also sends a confirmation email to the leave requestor if requestor_email is provided.
    """
    subject = f"New Leave Request Submitted - {requester_name}"
    # Fallback for plain text body
    plain_body = f"Hello,\n\n{requester_name} has submitted a leave request.\nDetails: {leave_details}\n\nPlease review and approve or reject the request."

    # HTML Table for leave details
    if isinstance(leave_details, dict):
        table_rows = ''.join(
            f'<tr><td style=\"padding:8px 12px;border:1px solid #ddd;background:#f8f9fa;\"><b>{k}</b></td><td style=\"padding:8px 12px;border:1px solid #ddd;\">{v}</td></tr>' for k,
            v in leave_details.items())
        details_table = f'<table style=\"border-collapse:collapse;margin:16px 0;width:100%;\">{table_rows}</table>'
    else:
        details_table = f'<pre>{leave_details}</pre>'

    # Secure Approve/Reject links using tokens
    approve_url = reject_url = "#"
    if approve_token and reject_token:
        settings = get_settings()
        base_url = settings.SITE_URL.rstrip('/')
        approve_url = f"{base_url}/api/v1/actions/action/{approve_token}"
        reject_url = f"{base_url}/api/v1/actions/action/{reject_token}"

    # Enhanced button styling for better email client compatibility
    approve_btn = f'''
    <a href="{approve_url}" style="
        display: inline-block;
        background: #28a745;
        color: #ffffff;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 6px;
        margin: 8px 8px 8px 0;
        font-weight: bold;
        font-size: 14px;
        border: 2px solid #28a745;
        text-align: center;
        min-width: 100px;
    ">✓ APPROVE</a>'''
    
    reject_btn = f'''
    <a href="{reject_url}" style="
        display: inline-block;
        background: #dc3545;
        color: #ffffff;
        padding: 12px 24px;
        text-decoration: none;
        border-radius: 6px;
        margin: 8px 0;
        font-weight: bold;
        font-size: 14px;
        border: 2px solid #dc3545;
        text-align: center;
        min-width: 100px;
    ">✗ REJECT</a>'''

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Leave Request - {requester_name}</title>
    </head>
    <body style="margin: 0; padding: 0; background: #f5f5f5; font-family: Arial, sans-serif;">
        <div style="max-width: 500px; margin: 10px auto; background: #ffffff; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <!-- Header -->
            <div style="background: #2d6cdf; color: white; padding: 16px; text-align: center; border-radius: 6px 6px 0 0;">
                <h2 style="margin: 0; font-size: 18px;">🏖️ Leave Request</h2>
            </div>
            
            <!-- Content -->
            <div style="padding: 20px;">
                <p style="margin: 0 0 12px 0; color: #333;">
                    <strong>{requester_name}</strong> requests leave approval:
                </p>
                
                <!-- Compact Details -->
                <div style="background: #f8f9fa; padding: 12px; border-radius: 4px; margin: 12px 0; font-size: 14px;">
                    {details_table}
                </div>
                
                <!-- Action Buttons - Prominent Position -->
                <div style="text-align: center; margin: 20px 0;">
                    {approve_btn}
                    {reject_btn}
                </div>
                
                <p style="font-size: 11px; color: #6c757d; text-align: center; margin: 12px 0 0 0;">
                    Links expire in 72 hours • Single use only
                </p>
            </div>
        </div>
    </body>
    </html>
    '''
    
    send_email(subject, plain_body, [to_email], request=request, html=html)

    # Send confirmation to leave requestor
    if requestor_email:
        confirm_subject = "Your Leave Request Has Been Submitted"
        confirm_body = f"Hello {requester_name},\n\nYour leave request has been submitted for review. You will be notified once it is approved or rejected.\n\nDetails: {leave_details}\n\nBest Regards."
        confirm_html = f'''
        <div style="font-family:sans-serif;max-width:600px;">
            <p>Hello {requester_name},</p>
            <p>Your leave request has been <b>submitted for review</b>. You will be notified once it is approved or rejected.</p>
            {details_table}
            <p style="margin-top:24px;">Best Regards,<br/>Leave Management System</p>
        </div>
        '''
        send_email(
            confirm_subject,
            confirm_body,
            [requestor_email],
            request=request,
            html=confirm_html)


def send_wfh_approval_notification(
        to_email: str,
        wfh_details,
        approved: bool,
        request: Request):
    status = "approved" if approved else "rejected"
    subject = f"Your Work From Home Request has been {status.title()}"

    # Parse wfh_details if it's a string in 'Key: Value, Key: Value' format
    parsed_details = None
    if isinstance(wfh_details, dict):
        parsed_details = wfh_details
    elif isinstance(wfh_details, str):
        # Try to parse string to dict
        try:
            items = [item.strip() for item in wfh_details.split(',')]
            parsed_details = dict()
            for item in items:
                if ':' in item:
                    k, v = item.split(':', 1)
                    parsed_details[k.strip()] = v.strip()
            if not parsed_details:
                parsed_details = None
        except Exception:
            parsed_details = None

    if parsed_details:
        table_rows = ''.join(
            f'<tr><td style="padding:4px 8px;border:1px solid #ddd;"><b>{k}</b></td><td style="padding:4px 8px;border:1px solid #ddd;">{v}</td></tr>' for k,
            v in parsed_details.items())
        details_table = f'<table style="border-collapse:collapse;margin:12px 0;">{table_rows}</table>'
        plain_details = '\n'.join(
            [f"{k}: {v}" for k, v in parsed_details.items()])
    else:
        details_table = f'<pre>{wfh_details}</pre>'
        plain_details = str(wfh_details)

    # Color bar for status
    color = "#28a745" if approved else "#dc3545"
    status_text = f'<span style="color:{color};font-weight:bold;">{status.title()}</span>'
    html = f'''
    <div style="font-family:sans-serif;max-width:600px;">
        <p>Hello,</p>
        <p>Your work from home request has been {status_text}.</p>
        {details_table}
        <div style="margin:16px 0;height:8px;background:{color};border-radius:4px;"></div>
        <p style="margin-top:24px;">Best Regards,<br/>Leave Management System</p>
    </div>
    '''
    body = f"Hello,\n\nYour work from home request has been {status}.\n\nDetails:\n{plain_details}\n\nBest Regards."
    send_email(subject, body, [to_email], request=request, html=html)


def send_password_reset_email(
        to_email: str,
        to_name: str,
        new_password: str,
        reset_link: str,
        request: Request):
    """
    Send password reset email with new temporary password and reset link (similar to invite flow)
    """
    subject = "Password Reset - Leave Management System"
    body = (
        f"Hello {to_name},\n\n"
        f"Your password has been reset as requested.\n"
        f"Please use the following link to set your new password:\n{reset_link}\n\n"
        f"Your temporary password is: {new_password}\n\n"
        f"You will need to enter this temporary password along with your new password.\n\n"
        f"Best Regards,\nLeave Management System Team"
    )
    html = f"""
    <html>
    <body style='font-family: Arial, sans-serif; background: #f9f9f9; padding: 24px;'>
      <div style='max-width: 480px; margin: auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #eee; padding: 32px;'>
        <h2 style='color: #2d6cdf; margin-top: 0;'>Password Reset</h2>
        <p style='font-size: 16px; color: #333;'>
          Hello {to_name},<br><br>
          Your password has been reset as requested. Please click the button below to set your new password.
        </p>
        <a href='{reset_link}' style='display: inline-block; margin: 24px 0 8px 0; padding: 12px 32px; background: #2d6cdf; color: #fff; border-radius: 4px; text-decoration: none; font-size: 16px; font-weight: bold;'>
          Set New Password
        </a>
        <p style='font-size: 15px; color: #333; margin-top: 24px;'>
          <b>Your temporary password is:</b><br>
          <span style='background:#f4f4f4; padding:8px 12px; border-radius:4px; font-family:monospace; font-size:16px; display:inline-block; margin:8px 0;'>{new_password}</span>
        </p>
        <div style='background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 12px; margin: 24px 0;'>
          <p style='margin: 0; font-size: 14px; color: #856404;'>
            <b>💡 Note:</b> You will need to enter the temporary password above along with your new password when you click the link.
          </p>
        </div>
        <p style='font-size: 13px; color: #888; margin-top: 16px;'>
          If the button above doesn't work, copy and paste this link into your browser:<br>
          <a href='{reset_link}' style='color: #2d6cdf;'>{reset_link}</a>
        </p>
        <p style='font-size: 15px; color: #333;'>Best Regards,<br>Leave Management System Team</p>
      </div>
    </body>
    </html>
    """
    send_email(subject, body, [to_email], request=request, html=html)


def send_leave_auto_reject_notification(
        to_email: str,
        leave_details: dict,
        approved: bool = True):
    status = "approved" if approved else "rejected"
    subject = f"Your Leave Request has been Auto-{status.title()}"

    # Format leave_details dict as HTML table rows
    table_rows = "".join(
        f'<tr><td style="padding:4px 8px;border:1px solid #ddd;">{key}</td><td style="padding:4px 8px;border:1px solid #ddd;">{value}</td></tr>'
        for key, value in leave_details.items()
    )
    html = f'''
    <div style="font-family:sans-serif;max-width:600px;">
        <p>Hello,</p>
        <p>Your leave request has been Auto-{status.title()}.</p>
        <p style="margin-top:24px;">Details:</p>
        <table style="border-collapse:collapse;margin:12px 0;">
            <tr><th style="padding:4px 8px;border:1px solid #ddd;">Key</th><th style="padding:4px 8px;border:1px solid #ddd;">Value</th></tr>
            {table_rows}
        </table>
        <p style="margin-top:24px;">Best Regards,<br/>Leave Management System</p>
    </div>
    '''

    body = f"Hello,\n\nYour leave request has been Auto-{status}.\n\nDetails:\n{leave_details}\n\nBest Regards."
    send_email_background(subject, body, [to_email], html=html)

