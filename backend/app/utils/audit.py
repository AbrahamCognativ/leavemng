from sqlalchemy.orm import Session
from datetime import datetime
from app.models.audit_log import AuditLog
from uuid import UUID
from typing import Optional, Dict, Any


def create_audit_log(
    db: Session,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Create an audit log entry for any system action.

    Args:
        db: Database session
        user_id: ID of the user performing the action
        action: Type of action performed (e.g., "login", "create", "update")
        resource_type: Type of resource affected (e.g., "user", "leave_request")
        resource_id: ID of the affected resource
        metadata: Additional information about the action
    """
    try:
        # Convert resource_id to UUID if it's a string
        if isinstance(resource_id, str):
            try:
                resource_id = UUID(resource_id)
            except ValueError:
                # If not a valid UUID, use a default UUID
                resource_id = UUID('00000000-0000-0000-0000-000000000000')

        # Create the audit log entry
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=datetime.now(),
            extra_metadata=metadata or {}
        )

        # Add and commit to the database
        db.add(entry)
        db.commit()
        return True
    except (AttributeError, TypeError, Exception) as e:
        # Broad catch remains to ensure no audit log failure ever breaks main flow
        # Error creating audit log - handled silently in production
        db.rollback()
        return False
