#!/usr/bin/env python3
"""
Script to add test audit logs to the database.
Run this script to populate the audit_logs table with sample data.
"""

from app.models.user import User
from app.models.audit_log import AuditLog
from app.db.session import SessionLocal
import sys
import os
import uuid
from datetime import datetime, timezone
# Add the parent directory to the path so we can import from app
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..')))


def create_test_audit_logs():
    """Create test audit logs in the database."""
    db = SessionLocal()

    try:
        # Get a user to associate with the logs
        user = db.query(User).first()
        if not user:
            print("No users found in the database. Please create a user first.")
            return

        # Create sample audit logs for various actions
        sample_logs = [
            {
                "user_id": user.id,
                "action": "login_success",
                "resource_type": "auth",
                "resource_id": user.id,
                "timestamp": datetime.now(timezone.utc),
                "extra_metadata": {"email": user.email, "role": user.role_band}
            },
            {
                "user_id": user.id,
                "action": "view_profile",
                "resource_type": "user",
                "resource_id": user.id,
                "timestamp": datetime.now(timezone.utc),
                "extra_metadata": {"viewed_by": user.email}
            },
            {
                "user_id": user.id,
                "action": "update_user",
                "resource_type": "user",
                "resource_id": user.id,
                "timestamp": datetime.now(timezone.utc),
                "extra_metadata": {
                    "updated_fields": ["name", "gender"],
                    "updated_by": user.email,
                    "self_update": True
                }
            },
            {
                "user_id": user.id,
                "action": "upload_profile_image",
                "resource_type": "user",
                "resource_id": user.id,
                "timestamp": datetime.now(timezone.utc),
                "extra_metadata": {
                    "uploaded_by": user.email,
                    "self_upload": True,
                    "file_type": ".jpg"
                }
            },
            {
                "user_id": user.id,
                "action": "create_leave_request",
                "resource_type": "leave_request",
                "resource_id": uuid.uuid4(),
                "timestamp": datetime.now(timezone.utc),
                "extra_metadata": {
                    "leave_type": "Annual Leave",
                    "start_date": datetime.now(timezone.utc).isoformat(),
                    "end_date": datetime.now(timezone.utc).isoformat()
                }
            }
        ]

        # Add logs to the database
        for log_data in sample_logs:
            log = AuditLog(
                user_id=log_data["user_id"],
                action=log_data["action"],
                resource_type=log_data["resource_type"],
                resource_id=log_data["resource_id"],
                timestamp=log_data["timestamp"],
                extra_metadata=log_data["extra_metadata"]
            )
            db.add(log)

        db.commit()
        print(
            f"Successfully added {
                len(sample_logs)} test audit logs to the database.")

    except (AttributeError, TypeError, Exception) as e:
        db.rollback()
        print(f"Error creating test audit logs: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    create_test_audit_logs()
