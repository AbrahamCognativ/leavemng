import time
from app.db.session import SessionLocal
from app.utils.accrual import add_existing_users_to_leave_balances, accrue_monthly_leave_balances, accrue_quarterly_leave_balances, accrue_yearly_leave_balances, reset_annual_leave_carry_forward, reset_yearly_leave_balances_on_join_date
from apscheduler.schedulers.background import BackgroundScheduler
from app.utils.auto_reject import auto_reject_old_pending_leaves
from app.utils.sick_leave_doc_check import sick_leave_doc_check_job
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
    # scheduler.add_job(accrual_job_monthly, 'interval', seconds=90, id='accrual_job_monthly')

    # Run quarterly on the 1st of Jan, Apr, Jul, Oct at 00:00
    scheduler.add_job(quarterly_accrual_job, 'cron', month='1,4,7,10', day=1, hour=0, minute=0, id='quarterly_accrual_job')


    # Schedule reset yearly leave balances on join date every midnight
    def reset_yearly_leave_balances_on_join_date_job():
        db = SessionLocal()
        try:
            logging.info('[START] Reset yearly leave balances on join date job starting.')
            reset_yearly_leave_balances_on_join_date(db)
            db.commit()
            logging.info('[SUCCESS] Reset yearly leave balances on join date job ran successfully.')
        except Exception as e:
            logging.error(f'[ERROR] Reset yearly leave balances on join date job failed: {e}')
        finally:
            db.close()
    scheduler.add_job(reset_yearly_leave_balances_on_join_date_job, 'cron', hour=0, minute=0, id='reset_yearly_leave_balances_on_join_date_job')



    # Schedule sick leave document check every hour
    def sick_leave_doc_check_job_scheduler():
        db = SessionLocal()
        try:
            logging.info('[START] Sick leave document check job starting.')
            sick_leave_doc_check_job()
            db.commit()
            logging.info('[SUCCESS] Sick leave document check job ran successfully.')
        except Exception as e:
            logging.error(f'[ERROR] Sick leave document check job failed: {e}')
        finally:
            db.close()
    # Schedule sick leave document check every hour
    scheduler.add_job(sick_leave_doc_check_job_scheduler, 'cron', minute=0, id='sick_leave_doc_check')
    # scheduler.add_job(sick_leave_doc_check_job_scheduler, 'interval', seconds=80, id='sick_leave_doc_check')

    # Schedule sick leave document check every 12 hours
    def sick_leave_doc_reminder_job_scheduler():
        db = SessionLocal()
        from app.utils.sick_leave_doc_check import sick_leave_doc_reminder_job
        try:
            logging.info('[START] Sick leave document reminder job starting.')
            sick_leave_doc_reminder_job()
            db.commit()
            logging.info('[SUCCESS] Sick leave document reminder job ran successfully.')
        except Exception as e:
            logging.error(f'[ERROR] Sick leave document reminder job failed: {e}')
        finally:
            db.close()
    scheduler.add_job(sick_leave_doc_reminder_job_scheduler, 'cron', hour='0,12', id='sick_leave_doc_reminder_job')



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
    # scheduler.add_job(carry_forward_job, 'interval', seconds=10, id='annual_leave_carry_forward')



    # Schedule auto-reject of old pending leaves every midnight
    def auto_reject_old_pending_leaves_job():
        try:
            logging.info('[START] Auto-reject pending leaves job starting.')
            auto_reject_old_pending_leaves()
            logging.info('[SUCCESS] Auto-reject pending leaves job ran successfully.')
        except Exception as e:
            logging.error(f'[ERROR] Auto-reject pending leaves job failed: {e}')
    scheduler.add_job(auto_reject_old_pending_leaves_job, 'cron', hour=0, minute=0, id='auto_reject_pending_leaves')
    # scheduler.add_job(auto_reject_old_pending_leaves_job, 'interval', seconds=10, id='auto_reject_pending_leaves')


    scheduler.start()
    logging.info('[INFO] Scheduler started. All jobs are scheduled.')

