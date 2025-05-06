import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from fastapi import Request

# SMTP config will be loaded from app.state.settings


def send_email(subject: str, body: str, to_emails: list[str], request: Request, from_email: Optional[str] = None, html: Optional[str] = None):
    """
    Send an email using SMTP settings from FastAPI app.state.settings.
    Args:
        subject: Email subject
        body: Plain text body
        to_emails: List of recipient emails
        request: FastAPI Request (to access app.state.settings)
        from_email: Optional sender override
        html: Optional HTML body
    """
    settings = request.app.state.settings
    smtp_server = settings.EMAIL_HOST
    smtp_port = settings.EMAIL_PORT
    smtp_user = settings.EMAIL_USER
    smtp_password = settings.EMAIL_PASSWORD
    from_email = from_email or smtp_user or settings.EMAIL_HOST

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)

    part1 = MIMEText(body, "plain")
    msg.attach(part1)
    if html:
        part2 = MIMEText(html, "html")
        msg.attach(part2)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(from_email, to_emails, msg.as_string())
    except (smtplib.SMTPException, socket.error) as e:
        logging.error(f"Email sending failed: {e}")
        raise HTTPException(status_code=502, detail=f"Could not send email: {e}")


def send_invite_email(to_email: str, invite_link: str, request: Request):
    subject = "You're Invited to Leave Management System"
    body = f"Hello,\n\nYou have been invited to join the Leave Management System. Please click the link below to register:\n{invite_link}\n\nBest Regards."
    try:
        send_email(subject, body, [to_email], request=request)
    except HTTPException as e:
        # Optionally, log or handle further if needed
        raise


def send_leave_request_notification(to_email: str, requester_name: str, leave_details: str, request: Request):
    subject = "New Leave Request Submitted"
    body = f"Hello,\n\n{requester_name} has submitted a leave request.\nDetails: {leave_details}\n\nPlease review and approve or reject the request."
    send_email(subject, body, [to_email], request=request)


def send_leave_approval_notification(to_email: str, leave_details: str, approved: bool, request: Request):
    status = "approved" if approved else "rejected"
    subject = f"Your Leave Request has been {status.title()}"
    body = f"Hello,\n\nYour leave request has been {status}.\nDetails: {leave_details}\n\nBest Regards."
    send_email(subject, body, [to_email], request=request)
