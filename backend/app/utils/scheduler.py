import time
import threading
from app.db.session import SessionLocal
from app.utils.accrual import accrue_leave_balances, reset_annual_leave_carry_forward
from apscheduler.schedulers.background import BackgroundScheduler
from app.auto_reject import auto_reject_old_pending_leaves

def run_accrual_scheduler(interval_seconds=120):  # Default: 30 days 2592000
    def job():
        while True:
            db = SessionLocal()
            try:
                accrue_leave_balances(db)
                print('[SUCCESS] Accrual job ran successfully.')
            finally:
                db.close()
            time.sleep(interval_seconds)
    t = threading.Thread(target=job, daemon=True)
    t.start()

    # Schedule carry forward logic for Dec 31st at midnight
    scheduler = BackgroundScheduler()
    def carry_forward_job():
        db = SessionLocal()
        try:
            reset_annual_leave_carry_forward(db)
            print('[SUCCESS] Annual leave carry forward job ran successfully.')
        finally:
            db.close()
    # Run at 00:00 on December 31st every year
    scheduler.add_job(carry_forward_job, 'cron', month=12, day=31, hour=0, minute=0, id='annual_leave_carry_forward')
    # Schedule sick leave document check every hour
    def sick_leave_doc_check_job():
        from sqlalchemy import and_
        from app.models.leave_request import LeaveRequest
        from app.models.leave_type import LeaveType, LeaveCodeEnum
        from app.models.leave_document import LeaveDocument
        from app.models.leave_balance import LeaveBalance
        from datetime import datetime, timedelta, timezone
        from decimal import Decimal
        import logging
        db = SessionLocal()
        try:
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
            print('[SUCCESS] Sick leave document check job ran successfully.')
        finally:
            db.close()
    scheduler.add_job(sick_leave_doc_check_job, 'interval', hours=1, id='sick_leave_doc_check')
    # Schedule auto-reject of old pending leaves every midnight
    def auto_reject_old_pending_leaves_job():
        auto_reject_old_pending_leaves()
        print('[SUCCESS] Auto-reject pending leaves job ran successfully.')
    scheduler.add_job(auto_reject_old_pending_leaves_job, 'cron', hour=0, minute=0, id='auto_reject_pending_leaves')
    scheduler.start()
