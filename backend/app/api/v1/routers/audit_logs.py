from app.deps.permissions import require_role
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.db.session import get_db
from app.deps.permissions import get_current_user, has_permission
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogResponse, AuditLogListResponse
from app.models.user import User

router = APIRouter()


@router.get("", response_model=AuditLogListResponse,
            tags=["audit-logs"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    user_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    sort: Optional[str] = "timestamp",
    order: Optional[str] = "desc",
):
    """
    Get audit logs with optional filtering.
    Only users with admin permissions can access this endpoint.
    """
    try:
        # Check if user has admin permissions
        if not has_permission(current_user, "view_audit_logs"):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view audit logs"
            )

        # Build the query
        query_obj = db.query(AuditLog)

        # Apply filters
        if user_id:
            query_obj = query_obj.filter(AuditLog.user_id == user_id)
        if resource_type:
            query_obj = query_obj.filter(
                AuditLog.resource_type == resource_type)
        if action:
            query_obj = query_obj.filter(AuditLog.action == action)
        if from_date:
            query_obj = query_obj.filter(AuditLog.timestamp >= from_date)
        if to_date:
            query_obj = query_obj.filter(AuditLog.timestamp <= to_date)

        # Get total count for pagination
        total_count = query_obj.count()

        # Apply pagination and ordering
        # First, prioritize records with non-null timestamps
        # Then sort by timestamp in descending order (newest first)
        from sqlalchemy import nullslast

        # Always sort by timestamp for consistency
        query_obj = query_obj.order_by(
            # First, put NULL timestamps at the end
            nullslast(desc(AuditLog.timestamp))
        ).offset(skip).limit(limit)

        # Execute query
        audit_logs = query_obj.all()

        # Prepare response data with additional user information
        enriched_logs = []
        for log in audit_logs:
            # Convert resource_id to string to avoid UUID validation issues
            if log.resource_id:
                log.resource_id = str(log.resource_id)

            # Get user information for the log
            user = db.query(User).filter(User.id == log.user_id).first()
            user_name = user.name if user else "Unknown User"
            user_email = user.email if user else "unknown@example.com"

            # Get resource information based on resource type
            resource_name = "Unknown"
            resource_details = {}

            if log.resource_type == "user":
                resource = db.query(User).filter(
                    User.id == log.resource_id).first()
                if resource:
                    resource_name = resource.name
                    resource_details = {
                        "email": resource.email,
                        "role": resource.role_band
                    }

            elif log.resource_type == "leave_request":
                from app.models.leave_request import LeaveRequest
                from app.models.leave_type import LeaveType

                try:
                    resource = db.query(LeaveRequest).filter(
                        LeaveRequest.id == log.resource_id).first()
                    if resource:
                        leave_type = db.query(LeaveType).filter(
                            LeaveType.id == resource.leave_type_id).first()
                        leave_type_name = leave_type.name if leave_type else "Unknown"
                        resource_name = f"{leave_type_name} ({
                            resource.start_date.strftime('%Y-%m-%d')} to {
                            resource.end_date.strftime('%Y-%m-%d')})"
                        resource_details = {
                            "status": resource.status,
                            "days": resource.days_requested
                        }
                except Exception as e:
                    print(f"Error getting leave request details: {str(e)}")

            elif log.resource_type == "org_unit":
                from app.models.org_unit import OrgUnit
                try:
                    resource = db.query(OrgUnit).filter(
                        OrgUnit.id == log.resource_id).first()
                    if resource:
                        resource_name = resource.name
                        resource_details = {
                            "description": resource.description
                        }
                except Exception as e:
                    print(f"Error getting org unit details: {str(e)}")

            # Create a dictionary with log data, user info, and resource info
            log_dict = {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "resource_name": resource_name,
                "resource_details": resource_details,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "extra_metadata": log.extra_metadata,
                "user_name": user_name,
                "user_email": user_email}
            enriched_logs.append(log_dict)

        return {
            "data": enriched_logs,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        # Log the error for debugging
        import traceback
        print(f"Error in get_audit_logs: {str(e)}")
        print(traceback.format_exc())

        # Return a more helpful error message
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving audit logs: {str(e)}"
        )


@router.get("/{audit_log_id}", response_model=AuditLogResponse,
            tags=["audit-logs"], dependencies=[Depends(require_role(["HR", "Admin"]))])
def get_audit_log(
    audit_log_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific audit log by ID.
    Only users with admin permissions can access this endpoint.
    """
    # Check if user has admin permissions
    if not has_permission(current_user, "view_audit_logs"):
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view audit logs"
        )

    # Get the audit log
    audit_log = db.query(AuditLog).filter(AuditLog.id == audit_log_id).first()

    if not audit_log:
        raise HTTPException(
            status_code=404,
            detail="Audit log not found"
        )

    return {"data": audit_log}
