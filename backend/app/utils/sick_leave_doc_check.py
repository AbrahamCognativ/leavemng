import logging
from sqlalchemy import and_
from app.db.session import SessionLocal
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType, LeaveCodeEnum
from app.models.leave_document import LeaveDocument
from app.models.leave_balance import LeaveBalance
from datetime import datetime, timedelta, timezone
from decimal import Decimal

def sick_leave_doc_check_job():
    db = SessionLocal()
    try:
        logging.info('[START] Sick leave document check job starting.')
        # Configurable document deadline (hours)
        DOC_DEADLINE_HOURS = 48
        now = datetime.now(timezone.utc)
        # Find pending sick leave requests older than deadline
        sick_type = db.query(LeaveType).filter(LeaveType.code == LeaveCodeEnum.sick).first()
        if not sick_type:
            return
        overdue = db.query(LeaveRequest).filter(
            LeaveRequest.leave_type_id == sick_type.id,
            LeaveRequest.status == 'pending',
            LeaveRequest.applied_at < now - timedelta(hours=DOC_DEADLINE_HOURS)
        ).all()
        for req in overdue:
            # Check if document exists
            doc = db.query(LeaveDocument).filter(LeaveDocument.request_id == req.id).first()
            if not doc:
                # Deduct from annual leave
                annual_type = db.query(LeaveType).filter(LeaveType.code == LeaveCodeEnum.annual).first()
                if annual_type:
                    bal = db.query(LeaveBalance).filter_by(user_id=req.user_id, leave_type_id=annual_type.id).first()
                    if bal:
                        bal.balance_days = Decimal(max(float(bal.balance_days) - float(req.total_days), 0))
                # Auto-approve
                req.status = 'approved'
                req.decision_at = now
                req.decided_by = req.user_id
                # Optionally, notify the user
                try:
                    from app.models.user import User
                    from app.utils.email import send_leave_approval_notification
                    user = db.query(User).filter(User.id == req.user_id).first()
                    if user:
                        leave_details = f"Type: Annual (auto-deducted for missing sick doc), Start: {req.start_date}, End: {req.end_date}, Days: {req.total_days}"
                        send_leave_approval_notification(user.email, leave_details, approved=True)
                except Exception as e:
                    logging.warning(f"Could not send notification: {e}")
        db.commit()
        logging.info('[SUCCESS] Sick leave document check job ran successfully.')
    except Exception as e:
        logging.error(f'[ERROR] Sick leave document check job failed: {e}')
    finally:
        db.close()
