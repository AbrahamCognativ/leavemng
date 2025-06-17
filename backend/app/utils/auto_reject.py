from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.leave_request import LeaveRequest
from app.models.leave_balance import LeaveBalance
from app.models.user import User
from app.models.leave_type import LeaveType
from app.db.session import SessionLocal
from app.utils.email_utils import send_leave_auto_reject_notification
from app.utils.audit_log_utils import log_audit


def auto_reject_old_pending_leaves():
    db: Session = SessionLocal()
    try:
        threshold = datetime.now(timezone.utc) - timedelta(weeks=3)
        old_pending = db.query(LeaveRequest).filter(
            LeaveRequest.status == 'pending',
            LeaveRequest.applied_at < threshold
        ).all()
        if not old_pending:
            log_audit(db, "Auto-Reject Pending Leaves",
                      "No old pending leaves found")
        else:
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
                    leave_details = {
                        "Type": next(
                            (f"{
                                lt.code.value.capitalize()} leave" for lt in db.query(LeaveType).all() if lt.id == req.leave_type_id and lt.code.value in [
                                'sick',
                                'annual',
                                'compassionate',
                                'maternity',
                                'paternity']),
                            'Unknown'),
                        "Start": req.start_date,
                        "End": req.end_date,
                        "Days": req.total_days}
                    try:
                        send_leave_auto_reject_notification(
                            user.email, leave_details, approved=False
                        )
                    except Exception as e:
                        log_audit(db, "Auto-Reject Pending Leaves",
                                  f"Error sending auto-rejection email: {e}")
            log_audit(db, "Auto-Reject Pending Leaves",
                      f"Auto-rejected {len(old_pending)} old pending leaves")
    except Exception as e:
        log_audit(db, "Auto-Reject Pending Leaves",
                  f"Error in auto_reject_old_pending_leaves: {e}")
    finally:
        db.close()
