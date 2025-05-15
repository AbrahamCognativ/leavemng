import time
import threading
from app.db.session import SessionLocal
from app.utils.accrual import add_existing_users_to_leave_balances, accrue_monthly_leave_balances, accrue_quarterly_leave_balances, accrue_yearly_leave_balances, reset_annual_leave_carry_forward, test_accrue_annual_leave
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.auto_reject import auto_reject_old_pending_leaves

import logging

def run_accrual_scheduler():
    scheduler = BackgroundScheduler()

    # Accrual job: run monthly (for demo/testing, every 2 minutes)
    def accrual_job_monthly():
        db = SessionLocal()
        try:
            logging.info('[START] Accrual job starting.')
            add_existing_users_to_leave_balances(db)
            accrue_monthly_leave_balances(db)
            db.commit()
            logging.info('[SUCCESS] Accrual job ran successfully.')
        except Exception as e:
            logging.error(f'[ERROR] Accrual job failed: {e}')
        finally:
            db.close()

    def yearly_accrual_job():
        db = SessionLocal()
        try:
            logging.info('[START] Yearly accrual job starting.')
            accrue_yearly_leave_balances
            db.commit()
            logging.info('[SUCCESS] Yearly accrual job ran successfully.')
        except Exception as e:
            logging.error(f'[ERROR] Yearly accrual job failed: {e}')
        finally:
            db.close()


    def quarterly_accrual_job():
        db = SessionLocal()
        try:
            logging.info('[START] Quarterly accrual job starting.')
            accrue_quarterly_leave_balances(db)
            db.commit()
            logging.info('[SUCCESS] Quarterly accrual job ran successfully.')
        except Exception as e:
            logging.error(f'[ERROR] Quarterly accrual job failed: {e}')
        finally:
            db.close()

    # For demo/testing: run every 2 minutes. For real monthly: use 'cron', day=1, hour=0, minute=0
    # Run monthly on the 1st at 00:00
    scheduler.add_job(accrual_job_monthly, 'cron', day=1, hour=0, minute=0, id='accrual_job_monthly')
    # Run yearly on January 1st at 00:00
    scheduler.add_job(yearly_accrual_job, 'cron', month=1, day=1, hour=0, minute=0, id='yearly_accrual_job')
    # Run quarterly on the 1st of Jan, Apr, Jul, Oct at 00:00
    scheduler.add_job(quarterly_accrual_job, 'cron', month='1,4,7,10', day=1, hour=0, minute=0, id='quarterly_accrual_job')

    # Schedule quarterly accrual for Apr 1st at 00:00
    def test_quarterly_accrual_job():
        db = SessionLocal()
        try:
            logging.info('[START] Test annual leave accrual job starting.')
            test_accrue_annual_leave(db)
            db.commit()
            logging.info('[SUCCESS] Test annual leave accrual job ran successfully.')
        except Exception as e:
            logging.error(f'[ERROR] Test annual leave accrual job failed: {e}')
        finally:
            db.close()
    # For demo/testing: run every 2 minutes. For real monthly: use 'interval', minutes=30
    scheduler.add_job(test_quarterly_accrual_job, 'interval', minutes=1, id='test_quarterly_accrual_job')


    # Schedule carry forward logic for Dec 31st at midnight
    def carry_forward_job():
        db = SessionLocal()
        try:
            logging.info('[START] Annual leave carry forward job starting.')
            reset_annual_leave_carry_forward(db)
            db.commit()
            logging.info('[SUCCESS] Annual leave carry forward job ran successfully.')
        except Exception as e:
            logging.error(f'[ERROR] Annual leave carry forward job failed: {e}')
        finally:
            db.close()
    # Run at 00:00 on December 31st every year
    scheduler.add_job(carry_forward_job, 'cron', month=12, day=31, hour=0, minute=0, id='annual_leave_carry_forward')

    # Schedule sick leave document check every hour
    from app.utils.sick_leave_doc_check import sick_leave_doc_check_job
    scheduler.add_job(sick_leave_doc_check_job, 'interval', hours=1, id='sick_leave_doc_check')

    # Schedule auto-reject of old pending leaves every midnight
    def auto_reject_old_pending_leaves_job():
        try:
            logging.info('[START] Auto-reject pending leaves job starting.')
            auto_reject_old_pending_leaves()
            logging.info('[SUCCESS] Auto-reject pending leaves job ran successfully.')
        except Exception as e:
            logging.error(f'[ERROR] Auto-reject pending leaves job failed: {e}')
    scheduler.add_job(auto_reject_old_pending_leaves_job, 'cron', hour=0, minute=0, id='auto_reject_pending_leaves')

    scheduler.start()
    logging.info('[INFO] Scheduler started. All jobs are scheduled.')
