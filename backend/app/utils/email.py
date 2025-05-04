import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import os

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", SMTP_USERNAME)


def send_email(subject: str, body: str, to_emails: List[str], from_email: Optional[str] = None, html: Optional[str] = None):
    from_email = from_email or DEFAULT_FROM_EMAIL
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)

    part1 = MIMEText(body, "plain")
    msg.attach(part1)
    if html:
        part2 = MIMEText(html, "html")
        msg.attach(part2)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(from_email, to_emails, msg.as_string())


def send_invite_email(to_email: str, invite_link: str):
    subject = "You're Invited to Leave Management System"
    body = f"Hello,\n\nYou have been invited to join the Leave Management System. Please click the link below to register:\n{invite_link}\n\nBest Regards."
    send_email(subject, body, [to_email])


def send_leave_request_notification(to_email: str, requester_name: str, leave_details: str):
    subject = "New Leave Request Submitted"
    body = f"Hello,\n\n{requester_name} has submitted a leave request.\nDetails: {leave_details}\n\nPlease review and approve or reject the request."
    send_email(subject, body, [to_email])


def send_leave_approval_notification(to_email: str, leave_details: str, approved: bool):
    status = "approved" if approved else "rejected"
    subject = f"Your Leave Request has been {status.title()}"
    body = f"Hello,\n\nYour leave request has been {status}.\nDetails: {leave_details}\n\nBest Regards."
    send_email(subject, body, [to_email])
