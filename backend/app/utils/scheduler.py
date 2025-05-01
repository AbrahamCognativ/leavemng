import time
import threading
from app.db.session import SessionLocal
from app.utils.accrual import accrue_leave_balances

def run_accrual_scheduler(interval_seconds=2592000):  # Default: 30 days
    def job():
        while True:
            db = SessionLocal()
            try:
                accrue_leave_balances(db)
            finally:
                db.close()
            time.sleep(interval_seconds)
    t = threading.Thread(target=job, daemon=True)
    t.start()
