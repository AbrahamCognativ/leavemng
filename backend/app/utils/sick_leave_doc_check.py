import logging
from app.db.session import SessionLocal
from fastapi import Request
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType, LeaveCodeEnum
from app.models.leave_document import LeaveDocument
from app.models.leave_balance import LeaveBalance
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.utils.audit_log_utils import log_audit
from app.utils.email_utils import send_leave_sick_doc_reminder


def sick_leave_doc_check_job(request: Request = None):
    db = SessionLocal()
    try:
        logging.info('[START] Sick leave document check job starting.')
        # Configurable document deadline (hours)
        DOC_DEADLINE_HOURS = 48
        now = datetime.now(timezone.utc)
        # Find pending sick leave requests older than deadline
        sick_type = db.query(LeaveType).filter(
            LeaveType.code == LeaveCodeEnum.sick).first()
        if not sick_type:
            log_audit(
                db,
                "Sick Leave Document Check",
                "No sick leave type found")
            return
        # Find pending sick leave requests applied more than DOC_DEADLINE_HOURS
        # ago
        overdue = db.query(LeaveRequest).filter(
            LeaveRequest.leave_type_id == sick_type.id,
            LeaveRequest.status == 'pending',
            LeaveRequest.applied_at <= now -
            timedelta(
                hours=DOC_DEADLINE_HOURS)).all()
        if not overdue:
            log_audit(db, "Sick Leave Document Check",
                      "No overdue sick leave requests found")
        else:
            for req in overdue:
                # Check if document exists
                doc = db.query(LeaveDocument).filter(
                    LeaveDocument.request_id == req.id).first()
                if not doc:
                    # Deduct from annual leave
                    annual_type = db.query(LeaveType).filter(
                        LeaveType.code == LeaveCodeEnum.annual).first()
                    if annual_type:
                        annual_bal = db.query(LeaveBalance).filter_by(
                            user_id=req.user_id, leave_type_id=annual_type.id).first()
                        sick_bal = db.query(LeaveBalance).filter_by(
                            user_id=req.user_id, leave_type_id=sick_type.id).first()
                        leave_days = float(req.total_days)
                        if annual_bal and sick_bal:
                            available_annual = float(annual_bal.balance_days)
                            if available_annual >= leave_days:
                                annual_bal.balance_days = Decimal(
                                    available_annual - leave_days)
                                sick_bal.balance_days = Decimal(
                                    float(sick_bal.balance_days) + leave_days)
                            else:
                                # Deduct all annual, deduct remainder from
                                # sick, and credit back sick
                                annual_bal.balance_days = Decimal(0)
                                remainder = leave_days - available_annual
                                sick_bal.balance_days = Decimal(
                                    float(sick_bal.balance_days) + remainder)

                    # Auto-approve
                    req.status = 'approved'
                    req.decision_at = now
                    req.decided_by = req.user_id
                    # Optionally, notify the user
                    try:
                        from app.models.user import User
                        from app.utils.email_utils import send_leave_auto_approval_notification
                        user = db.query(User).filter(
                            User.id == req.user_id).first()
                        if user:
                            leave_details = {
                                "Type": "Annual (auto-deducted for missing sick doc)",
                                "Start": str(
                                    req.start_date),
                                "End": str(
                                    req.end_date),
                                "Days": str(
                                    req.total_days)}
                            send_leave_auto_approval_notification(
                                user.email, leave_details, approved=True)
                    except (AttributeError, TypeError, Exception) as e:
                        log_audit(db, "Sick Leave Document Check",
                                  f"Could not send notification: {e}")
            db.commit()
            log_audit(
                db,
                "Sick Leave Document Check",
                "Sick leave document check job ran successfully.")
    except (AttributeError, TypeError, Exception) as e:
        log_audit(db, "Sick Leave Document Check",
                  f"Sick leave document check job failed: {e}")
    finally:
        db.close()


def sick_leave_doc_reminder_job():
    db = SessionLocal()
    try:
        logging.info('[START] Sick leave document reminder job starting.')
        # Configurable document deadline (hours)
        DOC_DEADLINE_HOURS = 48
        now = datetime.now(timezone.utc)
        # Find pending sick leave requests older than deadline
        sick_type = db.query(LeaveType).filter(
            LeaveType.code == LeaveCodeEnum.sick).first()
        if not sick_type:
            log_audit(
                db,
                "Sick Leave Document Reminder",
                "No sick leave type found")
            return
        # Overdue: sick type, pending, applied within last 48h, and no leave
        # document attached
        overdue = db.query(LeaveRequest).filter(
            LeaveRequest.leave_type_id == sick_type.id,
            LeaveRequest.status == 'pending',
            LeaveRequest.applied_at >= now -
            timedelta(
                hours=DOC_DEADLINE_HOURS),
            LeaveRequest.applied_at <= now,
            ~db.query(LeaveDocument).filter(
                LeaveDocument.request_id == LeaveRequest.id).exists()).all()
        if not overdue:
            log_audit(db, "Sick Leave Document Reminder",
                      "No overdue sick leave requests found")
        else:
            for req in overdue:
                # Check if document exists
                doc = db.query(LeaveDocument).filter(
                    LeaveDocument.request_id == req.id).first()
                if not doc:
                    # Send reminder email
                    try:
                        from app.models.user import User
                        user = db.query(User).filter(
                            User.id == req.user_id).first()
                        leave_details = {
                            'type': req.leave_type_id,
                            'start': req.start_date,
                            'end': req.end_date,
                            'days': req.total_days
                        }
                        if not user:
                            log_audit(
                                db,
                                "Sick Leave Document Reminder",
                                f"User not found for leave request {req.id}")
                            continue
                        elapsed = (now - req.applied_at).total_seconds() / 3600
                        DOC_DEADLINE_HOURS = 48
                        remaining_hours = max(
                            0, int(DOC_DEADLINE_HOURS - elapsed))
                        # Use background email sending for jobs (no FastAPI
                        # Request)
                        send_leave_sick_doc_reminder(
                            user.email, remaining_hours, leave_details)
                    except (AttributeError, TypeError, Exception) as e:
                        log_audit(db, "Sick Leave Document Reminder",
                                  f"Could not send reminder notification: {e}")
            db.commit()
            log_audit(db, "Sick Leave Document Reminder",
                      "Sick leave document reminder job ran successfully.")
    except (AttributeError, TypeError, Exception) as e:
        log_audit(db, "Sick Leave Document Reminder",
                  f"Sick leave document reminder job failed: {e}")
    finally:
        db.close()
