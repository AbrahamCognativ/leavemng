import os
import datetime
from app.models.audit_log import AuditLog
from app.models.user import User
from sqlalchemy.orm import Session

LOG_PATH = os.path.join(
    os.path.dirname(__file__),
    '..',
    'api',
    'uploads',
    'logs',
    'accrual_audit.log')
LOG_PATH = os.path.abspath(LOG_PATH)

# Scheduler will use or create this user for audit logs


def get_or_create_scheduler_user(db: Session):
    """Get or create the Anonymous Scheduler user for audit logging."""
    from app.models.user import User
    scheduler_name = 'anonymous scheduler'
    user = db.query(User).filter(User.name == scheduler_name).first()
    if not user:
        user = User(
            name=scheduler_name,
            email='scheduler@cognativ.com',
            hashed_password='!',  # Not used for login
            role_band='IC',
            role_title='Scheduler',
            passport_or_id_number='SCHEDULER-000',
            gender='male',
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def write_audit_log(message: str):
    """Append a message to the audit log file, creating directories/files as needed."""
    log_dir = os.path.dirname(LOG_PATH)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    with open(LOG_PATH, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")


def insert_audit_log_db(
        db: Session,
        action: str,
        resource_id: str = "",
        extra_metadata: dict = None):
    """Insert an audit log record into the database using the scheduler user."""
    user = get_or_create_scheduler_user(db)
    log = AuditLog(
        user_id=user.id,
        action=action,
        resource_type="system_scheduler",
        resource_id="cron_job",
        timestamp=datetime.datetime.now(),
        extra_metadata=extra_metadata
    )
    db.add(log)
    db.commit()


def log_audit(db: Session, action: str, details: str):
    write_audit_log(f"{action}: {details}")
    insert_audit_log_db(db, action, extra_metadata={"details": details})
