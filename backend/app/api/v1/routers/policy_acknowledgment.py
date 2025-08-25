from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, case
from app.db.session import get_db
from app.models.policy import Policy
from app.models.policy_acknowledgment import PolicyAcknowledgment
from app.models.user import User
from app.schemas.policy_acknowledgment import (
    PolicyAcknowledmentCreate, 
    PolicyAcknowledmentRead, 
    PolicyAcknowledmentListItem,
    PolicyNotificationRequest,
    PolicyAcknowledmentStats,
    UserPolicyStatus
)
from app.deps.permissions import get_current_user, require_role
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from app.utils.email_utils import send_email_background

router = APIRouter()


@router.post("/acknowledge", response_model=PolicyAcknowledmentRead, tags=["policy-acknowledgments"])
async def acknowledge_policy(
    acknowledgment_data: PolicyAcknowledmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Acknowledge a policy by the current user"""
    
    # Verify policy exists and is active
    policy = db.query(Policy).filter(
        Policy.id == acknowledgment_data.policy_id,
        Policy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Check if user has already acknowledged this policy
    existing_ack = db.query(PolicyAcknowledgment).filter(
        PolicyAcknowledgment.policy_id == acknowledgment_data.policy_id,
        PolicyAcknowledgment.user_id == current_user.id
    ).first()
    
    # Only raise error if the policy is actually acknowledged (not just a pending record)
    if existing_ack and existing_ack.is_acknowledged:
        raise HTTPException(status_code=400, detail="Policy already acknowledged")
    
    # Get client IP and user agent for audit trail
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    
    # Create or update acknowledgment record
    if existing_ack:
        # Update existing pending record
        acknowledgment = existing_ack
        acknowledgment.ip_address = client_ip
        acknowledgment.user_agent = user_agent
        acknowledgment.signature_data = acknowledgment_data.signature_data
        acknowledgment.signature_method = acknowledgment_data.signature_method
        acknowledgment.is_acknowledged = True
        acknowledgment.acknowledged_at = datetime.now(timezone.utc)
    else:
        # Create new acknowledgment record
        acknowledgment = PolicyAcknowledgment(
            policy_id=acknowledgment_data.policy_id,
            user_id=current_user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            signature_data=acknowledgment_data.signature_data,
            signature_method=acknowledgment_data.signature_method,
            is_acknowledged=True
        )
        db.add(acknowledgment)
    
    db.commit()
    db.refresh(acknowledgment)
    
    # Log audit
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="acknowledge_policy",
        resource_type="policy_acknowledgment",
        resource_id=str(acknowledgment.id),
        metadata={
            "policy_id": str(policy.id),
            "policy_name": policy.name,
            "signature_method": acknowledgment_data.signature_method,
            "ip_address": client_ip
        }
    )
    
    # Generate and send signed PDF copy
    try:
        await generate_and_send_signed_pdf(db, acknowledgment, policy, current_user)
    except Exception as e:
        # Log error but don't fail the acknowledgment
        print(f"Failed to generate/send signed PDF: {e}")
    
    return _build_acknowledgment_response(db, acknowledgment)


@router.get("/user/policies", response_model=List[UserPolicyStatus], tags=["policy-acknowledgments"])
def get_user_policy_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all policies and their acknowledgment status for the current user"""
    
    # Get all active policies that apply to the user's org unit or all org units
    policies_query = db.query(Policy).filter(
        Policy.is_active == True,
        (Policy.org_unit_id == current_user.org_unit_id) | (Policy.org_unit_id.is_(None))
    )
    
    policies = policies_query.all()
    result = []
    
    for policy in policies:
        # Check if user has acknowledged this policy
        acknowledgment = db.query(PolicyAcknowledgment).filter(
            PolicyAcknowledgment.policy_id == policy.id,
            PolicyAcknowledgment.user_id == current_user.id
        ).first()
        
        # Only consider it acknowledged if the is_acknowledged flag is True
        is_acknowledged = acknowledgment is not None and acknowledgment.is_acknowledged
        acknowledged_at = acknowledgment.acknowledged_at if acknowledgment and acknowledgment.is_acknowledged else None
        notification_sent_at = acknowledgment.notification_sent_at if acknowledgment else None
        acknowledgment_deadline = acknowledgment.acknowledgment_deadline if acknowledgment else None
        
        # Calculate if overdue and days remaining
        is_overdue = False
        days_remaining = None
        
        if acknowledgment_deadline and not is_acknowledged:
            now = datetime.now(timezone.utc)
            if now > acknowledgment_deadline:
                is_overdue = True
            else:
                days_remaining = (acknowledgment_deadline - now).days
        
        result.append(UserPolicyStatus(
            policy_id=policy.id,
            policy_name=policy.name,
            policy_description=policy.description,
            file_name=policy.file_name,
            file_type=policy.file_type,
            created_at=policy.created_at,
            acknowledgment_deadline=acknowledgment_deadline,
            is_acknowledged=is_acknowledged,
            acknowledged_at=acknowledged_at,
            notification_sent_at=notification_sent_at,
            is_overdue=is_overdue,
            days_remaining=days_remaining
        ))
    
    return result


@router.post("/notify", tags=["policy-acknowledgments"],
             dependencies=[Depends(require_role(["HR", "Admin"]))])
async def send_policy_notifications(
    notification_request: PolicyNotificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send policy acknowledgment notifications to users (Admin/HR only)"""
    
    # Verify policy exists and is active
    policy = db.query(Policy).filter(
        Policy.id == notification_request.policy_id,
        Policy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Determine which users to notify
    if notification_request.user_ids:
        # Notify specific users
        users = db.query(User).filter(
            User.id.in_(notification_request.user_ids),
            User.is_active == True
        ).all()
    else:
        # Notify all users in the policy's org unit or all users if policy applies to all
        if policy.org_unit_id:
            users = db.query(User).filter(
                User.org_unit_id == policy.org_unit_id,
                User.is_active == True
            ).all()
        else:
            users = db.query(User).filter(User.is_active == True).all()
    
    # Calculate deadline
    deadline = datetime.now(timezone.utc) + timedelta(days=notification_request.deadline_days)
    
    notifications_sent = 0
    
    for user in users:
        # Check if user has already acknowledged this policy
        existing_ack = db.query(PolicyAcknowledgment).filter(
            PolicyAcknowledgment.policy_id == policy.id,
            PolicyAcknowledgment.user_id == user.id
        ).first()
        
        if existing_ack:
            # Update deadline if not acknowledged yet
            if not existing_ack.is_acknowledged:
                existing_ack.acknowledgment_deadline = deadline
                existing_ack.notification_sent_at = datetime.now(timezone.utc)
                existing_ack.reminder_count = str(int(existing_ack.reminder_count) + 1)
        else:
            # Create new acknowledgment record with pending status
            acknowledgment = PolicyAcknowledgment(
                policy_id=policy.id,
                user_id=user.id,
                is_acknowledged=False,
                acknowledgment_deadline=deadline,
                notification_sent_at=datetime.now(timezone.utc),
                reminder_count="1"
            )
            db.add(acknowledgment)
        
        # Send email notification
        try:
            send_policy_notification_email(user.email, user.name, policy, deadline)
            notifications_sent += 1
        except Exception as e:
            # Log error but continue with other users
            print(f"Failed to send email to {user.email}: {e}")
    
    db.commit()
    
    # Log audit
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="send_policy_notifications",
        resource_type="policy",
        resource_id=str(policy.id),
        metadata={
            "policy_name": policy.name,
            "users_notified": len(users),
            "notifications_sent": notifications_sent,
            "deadline_days": notification_request.deadline_days
        }
    )
    
    return {
        "detail": f"Notifications sent to {notifications_sent} users",
        "users_notified": len(users),
        "notifications_sent": notifications_sent
    }


@router.get("/policy/{policy_id}/stats", response_model=PolicyAcknowledmentStats, tags=["policy-acknowledgments"],
            dependencies=[Depends(require_role(["HR", "Admin", "Manager"]))])
def get_policy_acknowledgment_stats(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get acknowledgment statistics for a specific policy"""
    
    # Verify policy exists
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Get total users that should acknowledge this policy
    if policy.org_unit_id:
        total_users = db.query(User).filter(
            User.org_unit_id == policy.org_unit_id,
            User.is_active == True
        ).count()
    else:
        total_users = db.query(User).filter(User.is_active == True).count()
    
    # Get acknowledgment counts
    acknowledged_count = db.query(PolicyAcknowledgment).filter(
        PolicyAcknowledgment.policy_id == policy_id,
        PolicyAcknowledgment.is_acknowledged == True
    ).count()
    
    pending_count = db.query(PolicyAcknowledgment).filter(
        PolicyAcknowledgment.policy_id == policy_id,
        PolicyAcknowledgment.is_acknowledged == False
    ).count()
    
    # Get overdue count
    now = datetime.now(timezone.utc)
    overdue_count = db.query(PolicyAcknowledgment).filter(
        PolicyAcknowledgment.policy_id == policy_id,
        PolicyAcknowledgment.is_acknowledged == False,
        PolicyAcknowledgment.acknowledgment_deadline < now
    ).count()
    
    # Calculate acknowledgment rate
    acknowledgment_rate = (acknowledged_count / total_users * 100) if total_users > 0 else 0
    
    return PolicyAcknowledmentStats(
        policy_id=policy_id,
        policy_name=policy.name,
        total_users=total_users,
        acknowledged_count=acknowledged_count,
        pending_count=pending_count,
        overdue_count=overdue_count,
        acknowledgment_rate=round(acknowledgment_rate, 2),
        created_at=policy.created_at
    )


@router.get("/policy/{policy_id}/acknowledgments", response_model=List[PolicyAcknowledmentListItem], tags=["policy-acknowledgments"],
            dependencies=[Depends(require_role(["HR", "Admin", "Manager"]))])
def get_policy_acknowledgments(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all acknowledgments for a specific policy"""
    
    # Verify policy exists
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Get acknowledgments with user details
    acknowledgments = db.query(PolicyAcknowledgment).options(
        joinedload(PolicyAcknowledgment.user),
        joinedload(PolicyAcknowledgment.policy)
    ).filter(PolicyAcknowledgment.policy_id == policy_id).all()
    
    result = []
    for ack in acknowledgments:
        result.append(PolicyAcknowledmentListItem(
            id=ack.id,
            policy_id=ack.policy_id,
            user_id=ack.user_id,
            policy_name=ack.policy.name,
            user_name=ack.user.name,
            user_email=ack.user.email,
            acknowledged_at=ack.acknowledged_at,
            signature_method=ack.signature_method,
            acknowledgment_deadline=ack.acknowledgment_deadline,
            is_acknowledged=ack.is_acknowledged,
            notification_sent_at=ack.notification_sent_at,
            reminder_count=ack.reminder_count
        ))
    
    return result


def send_policy_notification_email(to_email: str, to_name: str, policy: Policy, deadline: datetime):
    """Send policy notification email to user"""
    
    subject = f"New Policy Requires Your Acknowledgment: {policy.name}"
    
    # Format deadline
    deadline_str = deadline.strftime("%B %d, %Y at %I:%M %p UTC")
    
    body = f"""
Hello {to_name},

A new company policy has been published and requires your acknowledgment.

Policy: {policy.name}
Description: {policy.description or 'No description provided'}
Deadline: {deadline_str}

Please log into the Leave Management System to read and acknowledge this policy within 5 days.

Best Regards,
Leave Management System Team
"""
    
    html = f"""
    <html>
    <body style='font-family: Arial, sans-serif; background: #f9f9f9; padding: 24px;'>
      <div style='max-width: 600px; margin: auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #eee; padding: 32px;'>
        <h2 style='color: #2d6cdf; margin-top: 0;'>📋 New Policy Acknowledgment Required</h2>
        <p style='font-size: 16px; color: #333;'>
          Hello {to_name},<br><br>
          A new company policy has been published and requires your acknowledgment.
        </p>
        
        <div style='background: #f8f9fa; border-left: 4px solid #2d6cdf; padding: 16px; margin: 24px 0;'>
          <h3 style='margin: 0 0 8px 0; color: #2d6cdf;'>{policy.name}</h3>
          <p style='margin: 0; color: #666;'>{policy.description or 'No description provided'}</p>
        </div>
        
        <div style='background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 16px; margin: 24px 0;'>
          <p style='margin: 0; font-size: 14px; color: #856404;'>
            <b>⏰ Deadline:</b> {deadline_str}
          </p>
        </div>
        
        <p style='font-size: 16px; color: #333;'>
          Please log into the Leave Management System to read and acknowledge this policy within 5 days.
        </p>
        
        <a href='#' style='display: inline-block; margin: 24px 0 8px 0; padding: 12px 32px; background: #2d6cdf; color: #fff; border-radius: 4px; text-decoration: none; font-size: 16px; font-weight: bold;'>
          View Policy
        </a>
        
        <p style='font-size: 15px; color: #333; margin-top: 32px;'>Best Regards,<br>Leave Management System Team</p>
      </div>
    </body>
    </html>
    """
    
    send_email_background(subject, body, [to_email], html=html)


async def generate_and_send_signed_pdf(db: Session, acknowledgment: PolicyAcknowledgment, policy: Policy, user: User):
    """Generate a signed PDF copy with original policy content and send it to the user"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import tempfile
        import os
        from datetime import datetime
        
        # Create temporary file for the signed PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_path = temp_file.name
        
        # Create the PDF document
        doc = SimpleDocTemplate(temp_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1  # Center alignment
        )
        story.append(Paragraph(f"{policy.name} - SIGNED COPY", title_style))
        story.append(Spacer(1, 20))
        
        # Policy Information Header
        policy_info = [
            ['Policy Name:', policy.name],
            ['Document:', policy.file_name],
            ['Description:', policy.description or 'N/A'],
            ['Published Date:', policy.created_at.strftime('%B %d, %Y')],
        ]
        
        policy_table = Table(policy_info, colWidths=[2*inch, 4*inch])
        policy_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(policy_table)
        story.append(Spacer(1, 30))
        
        # Extract and include original policy content
        try:
            # Import the text extraction functions from policy router
            from app.api.v1.routers.policy import extract_pdf_text, extract_docx_text
            
            policy_content = ""
            if policy.file_type.lower() == 'pdf':
                policy_content = extract_pdf_text(policy.file_path)
            elif policy.file_type.lower() in ['doc', 'docx']:
                policy_content = extract_docx_text(policy.file_path)
            
            if policy_content:
                # Add policy content section
                story.append(Paragraph("POLICY CONTENT", styles['Heading2']))
                story.append(Spacer(1, 15))
                
                # Split content into paragraphs and add them
                content_style = ParagraphStyle(
                    'PolicyContent',
                    parent=styles['Normal'],
                    fontSize=10,
                    leading=14,
                    spaceAfter=12,
                    leftIndent=0,
                    rightIndent=0
                )
                
                # Split content into paragraphs (by double line breaks)
                paragraphs = policy_content.split('\n\n')
                for para in paragraphs:
                    para = para.strip()
                    if para:
                        # Replace single line breaks with spaces for better formatting
                        para = para.replace('\n', ' ')
                        story.append(Paragraph(para, content_style))
                
                story.append(PageBreak())  # Start signature section on new page
            
        except Exception as e:
            print(f"Could not extract policy content: {e}")
            # Continue without content if extraction fails
            story.append(Paragraph("Policy content could not be extracted. Please refer to the original document.", styles['Normal']))
            story.append(Spacer(1, 30))
        
        # Signature Section
        signature_title_style = ParagraphStyle(
            'SignatureTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            textColor=colors.darkblue,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("ELECTRONIC ACKNOWLEDGMENT AND SIGNATURE", signature_title_style))
        story.append(Spacer(1, 20))
        
        # Acknowledgment Statement
        statement_style = ParagraphStyle(
            'Statement',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=20,
            leftIndent=20,
            rightIndent=20,
            borderWidth=1,
            borderColor=colors.grey,
            borderPadding=15,
            backColor=colors.lightgrey
        )
        
        statement_text = f"""
        I, {user.name}, hereby acknowledge that I have read, understood, and agree to comply with
        the policy titled "{policy.name}". I understand the requirements, procedures, and guidelines
        outlined in this policy and acknowledge my responsibility to adhere to them.
        
        This electronic acknowledgment was provided on {acknowledgment.acknowledged_at.strftime('%B %d, %Y at %I:%M %p UTC')}
        and has the same legal effect as a handwritten signature.
        """
        
        story.append(Paragraph(statement_text, statement_style))
        story.append(Spacer(1, 30))
        
        # Signature Details
        signature_info = [
            ['Employee Name:', user.name],
            ['Employee Email:', user.email],
            ['Acknowledgment Date:', acknowledgment.acknowledged_at.strftime('%B %d, %Y at %I:%M %p UTC')],
            ['Signature Method:', acknowledgment.signature_method.replace('_', ' ').title()],
            ['Digital Signature ID:', str(acknowledgment.id)],
            ['Verification Code:', f"ACK-{str(acknowledgment.id)[:8].upper()}"],
        ]
        
        signature_table = Table(signature_info, colWidths=[2.5*inch, 3.5*inch])
        signature_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(Paragraph("Signature Details", styles['Heading2']))
        story.append(Spacer(1, 10))
        story.append(signature_table)
        story.append(Spacer(1, 30))
        
        # Signature Line
        signature_line_text = f"""
        <br/><br/>
        Acknowledged and signed by: {user.name}<br/>
        Date: {acknowledgment.acknowledged_at.strftime('%B %d, %Y at %I:%M %p UTC')}<br/>
        <br/>
        ________________________________<br/>
        Electronic Signature<br/>
        """
        
        signature_line_style = ParagraphStyle(
            'SignatureLine',
            parent=styles['Normal'],
            fontSize=12,
            leading=16,
            spaceAfter=20,
            leftIndent=50,
            rightIndent=50,
            alignment=0  # Left alignment
        )
        
        story.append(Paragraph(signature_line_text, signature_line_style))
        story.append(Spacer(1, 20))
        
        # Footer
        footer_text = f"""
        This document contains the original policy content with electronic acknowledgment signature.
        Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')} by the Leave Management System.
        For verification purposes, please contact the HR department with the verification code: ACK-{str(acknowledgment.id)[:8].upper()}
        """
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=1  # Center alignment
        )
        
        story.append(Paragraph(footer_text, footer_style))
        
        # Build the PDF
        doc.build(story)
        
        # Send email with signed PDF attachment
        subject = f"Policy Acknowledgment Confirmation: {policy.name}"
        
        body = f"""
Hello {user.name},

Thank you for acknowledging the policy "{policy.name}".

Please find attached your signed policy acknowledgment certificate for your records.

Acknowledgment Details:
- Policy: {policy.name}
- Acknowledged on: {acknowledgment.acknowledged_at.strftime('%B %d, %Y at %I:%M %p UTC')}
- Verification Code: ACK-{str(acknowledgment.id)[:8].upper()}

Best Regards,
Leave Management System Team
"""
        
        html = f"""
        <html>
        <body style='font-family: Arial, sans-serif; background: #f9f9f9; padding: 24px;'>
          <div style='max-width: 600px; margin: auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #eee; padding: 32px;'>
            <h2 style='color: #28a745; margin-top: 0;'>✅ Policy Acknowledgment Confirmed</h2>
            <p style='font-size: 16px; color: #333;'>
              Hello {user.name},<br><br>
              Thank you for acknowledging the policy "<strong>{policy.name}</strong>".
            </p>
            
            <div style='background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; padding: 16px; margin: 24px 0;'>
              <h3 style='margin: 0 0 8px 0; color: #155724;'>Acknowledgment Details</h3>
              <p style='margin: 4px 0; color: #155724;'><strong>Policy:</strong> {policy.name}</p>
              <p style='margin: 4px 0; color: #155724;'><strong>Acknowledged on:</strong> {acknowledgment.acknowledged_at.strftime('%B %d, %Y at %I:%M %p UTC')}</p>
              <p style='margin: 4px 0; color: #155724;'><strong>Verification Code:</strong> ACK-{str(acknowledgment.id)[:8].upper()}</p>
            </div>
            
            <p style='font-size: 16px; color: #333;'>
              Please find attached your signed policy acknowledgment certificate for your records.
            </p>
            
            <p style='font-size: 15px; color: #333; margin-top: 32px;'>Best Regards,<br>Leave Management System Team</p>
          </div>
        </body>
        </html>
        """
        
        # Send email with attachment
        filename = f"Policy_Acknowledgment_{policy.name.replace(' ', '_')}_{user.name.replace(' ', '_')}.pdf"
        
        send_email_background(
            subject=subject,
            body=body,
            to_emails=[user.email],
            html=html,
            attachments=[(temp_path, filename)]
        )
        
        # Clean up temporary file after a delay (email sending is async)
        import threading
        def cleanup():
            import time
            time.sleep(60)  # Wait 1 minute before cleanup
            try:
                os.unlink(temp_path)
            except:
                pass
        
        threading.Thread(target=cleanup).start()
        
    except ImportError:
        # ReportLab not available, send simple confirmation email
        subject = f"Policy Acknowledgment Confirmation: {policy.name}"
        body = f"""
Hello {user.name},

Thank you for acknowledging the policy "{policy.name}".

Acknowledgment Details:
- Policy: {policy.name}
- Acknowledged on: {acknowledgment.acknowledged_at.strftime('%B %d, %Y at %I:%M %p UTC')}
- Verification Code: ACK-{str(acknowledgment.id)[:8].upper()}

Best Regards,
Leave Management System Team
"""
        send_email_background(subject, body, [user.email])
        
    except Exception as e:
        # Log error and send simple confirmation
        print(f"Error generating signed PDF: {e}")
        subject = f"Policy Acknowledgment Confirmation: {policy.name}"
        body = f"""
Hello {user.name},

Thank you for acknowledging the policy "{policy.name}".

Your acknowledgment has been recorded successfully.

Best Regards,
Leave Management System Team
"""
        send_email_background(subject, body, [user.email])


def _build_acknowledgment_response(db: Session, acknowledgment: PolicyAcknowledgment) -> PolicyAcknowledmentRead:
    """Helper function to build PolicyAcknowledmentRead response with related data"""
    
    # Get related data
    policy = db.query(Policy).filter(Policy.id == acknowledgment.policy_id).first()
    user = db.query(User).filter(User.id == acknowledgment.user_id).first()
    
    return PolicyAcknowledmentRead(
        id=acknowledgment.id,
        policy_id=acknowledgment.policy_id,
        user_id=acknowledgment.user_id,
        acknowledged_at=acknowledgment.acknowledged_at,
        ip_address=acknowledgment.ip_address,
        user_agent=acknowledgment.user_agent,
        signature_data=acknowledgment.signature_data,
        signature_method=acknowledgment.signature_method,
        notification_sent_at=acknowledgment.notification_sent_at,
        notification_read_at=acknowledgment.notification_read_at,
        reminder_count=acknowledgment.reminder_count,
        is_acknowledged=acknowledgment.is_acknowledged,
        acknowledgment_deadline=acknowledgment.acknowledgment_deadline,
        created_at=acknowledgment.created_at,
        updated_at=acknowledgment.updated_at,
        policy_name=policy.name if policy else None,
        user_name=user.name if user else None,
        user_email=user.email if user else None
    )