from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.leave_request import LeaveRequest
from app.models.leave_balance import LeaveBalance
from app.models.user import User
from app.db.session import SessionLocal
from app.utils.email_utils import send_leave_approval_notification
import logging

def auto_reject_old_pending_leaves():
    db: Session = SessionLocal()
    try:
        threshold = datetime.now(timezone.utc) - timedelta(weeks=3)
        old_pending = db.query(LeaveRequest).filter(
            LeaveRequest.status == 'pending',
            LeaveRequest.applied_at < threshold
        ).all()
        for req in old_pending:
            req.status = 'rejected'
            req.decision_at = datetime.now(timezone.utc)
            req.decided_by = None  # or a system/admin user id
            # Restore leave balance
            leave_balance = db.query(LeaveBalance).filter(
                LeaveBalance.user_id == req.user_id,
                LeaveBalance.leave_type_id == req.leave_type_id
            ).first()
            if leave_balance:
                leave_balance.balance_days += req.total_days
                db.add(leave_balance)
            db.add(req)
            db.commit()
            db.refresh(req)
            # Notify the user
            user = db.query(User).filter(User.id == req.user_id).first()
            if user:
                leave_details = f"Type: {req.leave_type_id}, Start: {req.start_date}, End: {req.end_date}, Days: {req.total_days}"
                try:
                    send_leave_approval_notification(
                        user.email, leave_details, approved=False, request=None
                    )
                except Exception as e:
                    logging.error(f"Error sending auto-rejection email: {e}")
    except Exception as e:
        logging.error(f"Error in auto_reject_old_pending_leaves: {e}")
    finally:
        db.close()
