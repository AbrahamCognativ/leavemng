from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models.policy import Policy
from app.models.org_unit import OrgUnit
from app.models.user import User
from app.schemas.policy import PolicyCreate, PolicyUpdate, PolicyRead, PolicyListItem
from app.deps.permissions import get_current_user, require_role, get_current_user_from_token_param, UserInToken
from app.settings import get_settings
from typing import List, Optional
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path
from jose import jwt

SECRET_KEY = get_settings().SECRET_KEY
ALGORITHM = "HS256"

router = APIRouter()

# Create uploads directory for policies
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '../../uploads')
POLICY_UPLOADS_DIR = os.path.join(UPLOAD_DIR, 'policies')
os.makedirs(POLICY_UPLOADS_DIR, exist_ok=True)

ALLOWED_FILE_TYPES = {
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'ppt': 'application/vnd.ms-powerpoint',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png'
}


def get_file_size_string(size_bytes: int) -> str:
    """Convert file size in bytes to human readable string"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


@router.post("/", response_model=PolicyRead, tags=["policies"],
             dependencies=[Depends(require_role(["HR", "Admin", "Manager"]))])
async def create_policy(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    org_unit_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new policy with file upload"""
    
    # Validate file type
    file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
    if file_extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_FILE_TYPES.keys())}"
        )
    
    # Validate org_unit_id if provided
    org_unit_uuid = None
    if org_unit_id and org_unit_id.strip() and org_unit_id != "null":
        try:
            org_unit_uuid = uuid.UUID(org_unit_id)
            org_unit = db.query(OrgUnit).filter(OrgUnit.id == org_unit_uuid).first()
            if not org_unit:
                raise HTTPException(status_code=400, detail="Organization unit not found")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid organization unit ID")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_name = f"{file_id}_{file.filename}"
    file_path = os.path.join(POLICY_UPLOADS_DIR, file_name)
    
    # Save file
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        file_size = len(content)
        file_size_str = get_file_size_string(file_size)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Create policy record
    policy = Policy(
        name=name,
        description=description,
        file_path=file_path,
        file_name=file.filename,
        file_type=file_extension,
        file_size=file_size_str,
        org_unit_id=org_unit_uuid,
        created_by=current_user.id
    )
    
    db.add(policy)
    db.commit()
    db.refresh(policy)
    
    # Log audit
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="create_policy",
        resource_type="policy",
        resource_id=str(policy.id),
        metadata={
            "policy_name": name,
            "file_name": file.filename,
            "file_type": file_extension,
            "org_unit_id": str(org_unit_uuid) if org_unit_uuid else None
        }
    )
    
    # Auto-send notifications to all users for new policy
    try:
        from app.api.v1.routers.policy_acknowledgment import send_policy_notification_email
        from datetime import timedelta
        from app.models.policy_acknowledgment import PolicyAcknowledgment
        
        # Get all users that should be notified (excluding system users)
        system_emails = ['user@example.com', 'scheduler@cognativ.com']
        if org_unit_uuid:
            users = db.query(User).filter(
                User.org_unit_id == org_unit_uuid,
                User.is_active == True,
                ~User.email.in_(system_emails)
            ).all()
        else:
            users = db.query(User).filter(
                User.is_active == True,
                ~User.email.in_(system_emails)
            ).all()
        
        # Calculate deadline (5 days from now)
        deadline = datetime.now(timezone.utc) + timedelta(days=5)
        
        # Create acknowledgment records and send notifications
        for user in users:
            # Create acknowledgment record with pending status
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
            except Exception as e:
                # Log error but continue with other users
                import logging
                logging.error(f"Failed to send policy notification email to {user.email}: {e}")
        
        db.commit()
        
    except Exception as e:
        # Log error but don't fail the policy creation
        import logging
        logging.error(f"Failed to send policy notifications: {e}")
    
    return _build_policy_response(db, policy)


@router.get("/", response_model=List[PolicyListItem], tags=["policies"])
def list_policies(
    org_unit_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all active policies - accessible to all authenticated users"""
    
    query = db.query(Policy).filter(Policy.is_active == True)
    
    # Filter by org_unit_id if provided
    if org_unit_id:
        try:
            org_unit_uuid = uuid.UUID(org_unit_id)
            query = query.filter(Policy.org_unit_id == org_unit_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid organization unit ID")
    
    policies = query.options(
        joinedload(Policy.org_unit),
        joinedload(Policy.creator)
    ).order_by(Policy.created_at.desc()).all()
    
    result = []
    for policy in policies:
        result.append(PolicyListItem(
            id=policy.id,
            name=policy.name,
            description=policy.description,
            file_name=policy.file_name,
            file_type=policy.file_type,
            file_size=policy.file_size,
            org_unit_name=policy.org_unit.name if policy.org_unit else "All Organizations",
            creator_name=policy.creator.name,
            created_at=policy.created_at,
            updated_at=policy.updated_at
        ))
    
    return result


@router.get("/{policy_id}", response_model=PolicyRead, tags=["policies"])
def get_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific policy - accessible to all authenticated users"""
    
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return _build_policy_response(db, policy)


@router.put("/{policy_id}", response_model=PolicyRead, tags=["policies"],
            dependencies=[Depends(require_role(["HR", "Admin", "Manager"]))])
def update_policy(
    policy_id: uuid.UUID,
    policy_update: PolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a policy (metadata only, not the file)"""
    
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Validate org_unit_id if provided
    if policy_update.org_unit_id is not None:
        if policy_update.org_unit_id:
            org_unit = db.query(OrgUnit).filter(OrgUnit.id == policy_update.org_unit_id).first()
            if not org_unit:
                raise HTTPException(status_code=400, detail="Organization unit not found")
    
    # Update fields
    update_data = policy_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)
    
    policy.updated_by = current_user.id
    policy.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(policy)
    
    # Log audit
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="update_policy",
        resource_type="policy",
        resource_id=str(policy.id),
        metadata={
            "policy_name": policy.name,
            "updated_fields": list(update_data.keys())
        }
    )
    
    return _build_policy_response(db, policy)


@router.delete("/{policy_id}", tags=["policies"],
               dependencies=[Depends(require_role(["HR", "Admin"]))])
def delete_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete a policy (Admin/HR only)"""
    
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Soft delete
    policy.is_active = False
    policy.updated_by = current_user.id
    policy.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    # Log audit
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="delete_policy",
        resource_type="policy",
        resource_id=str(policy.id),
        metadata={
            "policy_name": policy.name,
            "file_name": policy.file_name
        }
    )
    
    return {"detail": "Policy deleted successfully"}


@router.get("/{policy_id}/download", tags=["policies"])
def download_policy_file(
    policy_id: uuid.UUID,
    inline: bool = False,
    db: Session = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user_from_token_param)
):
    """Download policy file - accessible to all authenticated users"""
    
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if not os.path.exists(policy.file_path):
        raise HTTPException(status_code=404, detail="Policy file not found")
    
    # Log audit
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="view_policy" if inline else "download_policy",
        resource_type="policy",
        resource_id=str(policy.id),
        metadata={
            "policy_name": policy.name,
            "file_name": policy.file_name,
            "inline_view": inline
        }
    )
    
    # Set appropriate headers for inline viewing vs download
    if inline:
        # For inline viewing (iframe), set Content-Disposition to inline
        response = FileResponse(
            policy.file_path,
            media_type=ALLOWED_FILE_TYPES.get(policy.file_type, 'application/octet-stream'),
            headers={
                "Content-Disposition": f"inline; filename={policy.file_name}",
                "X-Frame-Options": "ALLOWALL",  # Allow iframe embedding for document viewing
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*",  # Allow cross-origin requests
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "Authorization, Content-Type"
            }
        )
        return response
    else:
        # For download, use attachment disposition
        return FileResponse(
            policy.file_path,
            filename=policy.file_name,
            media_type=ALLOWED_FILE_TYPES.get(policy.file_type, 'application/octet-stream')
        )


@router.get("/{policy_id}/preview", tags=["policies"])
def preview_policy_file(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user_from_token_param)
):
    """Generate and serve a PDF preview of the policy file - supports DOCX to PDF conversion"""
    
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if not os.path.exists(policy.file_path):
        raise HTTPException(status_code=404, detail="Policy file not found")
    
    # If it's already a PDF, serve it directly
    if policy.file_type.lower() == 'pdf':
        # Log audit
        from app.utils.audit import create_audit_log
        create_audit_log(
            db=db,
            user_id=str(current_user.id),
            action="preview_policy",
            resource_type="policy",
            resource_id=str(policy.id),
            metadata={
                "policy_name": policy.name,
                "file_name": policy.file_name,
                "preview_type": "direct_pdf"
            }
        )
        
        return FileResponse(
            policy.file_path,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={policy.file_name}",
                "X-Frame-Options": "ALLOWALL",
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "Authorization, Content-Type"
            }
        )
    
    # For DOCX files, convert to PDF
    elif policy.file_type.lower() in ['doc', 'docx']:
        try:
            from app.utils.document_converter import DocumentConverter
            
            # Check if conversion is available
            if not DocumentConverter.is_conversion_available():
                raise HTTPException(
                    status_code=500,
                    detail="Document conversion not available. Please download the file instead."
                )
            
            # Generate or get existing preview PDF
            preview_pdf_path = DocumentConverter.ensure_preview_exists(policy.file_path)
            
            # Log audit
            from app.utils.audit import create_audit_log
            create_audit_log(
                db=db,
                user_id=str(current_user.id),
                action="preview_policy",
                resource_type="policy",
                resource_id=str(policy.id),
                metadata={
                    "policy_name": policy.name,
                    "file_name": policy.file_name,
                    "preview_type": "docx_to_pdf_conversion"
                }
            )
            
            # Serve the converted PDF
            preview_filename = f"{Path(policy.file_name).stem}_preview.pdf"
            return FileResponse(
                preview_pdf_path,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename={preview_filename}",
                    "X-Frame-Options": "ALLOWALL",
                    "Cache-Control": "no-cache",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type"
                }
            )
            
        except Exception as e:
            # Log the error
            from app.utils.audit import create_audit_log
            create_audit_log(
                db=db,
                user_id=str(current_user.id),
                action="preview_policy_failed",
                resource_type="policy",
                resource_id=str(policy.id),
                metadata={
                    "policy_name": policy.name,
                    "file_name": policy.file_name,
                    "error": str(e)
                }
            )
            
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate preview: {str(e)}. Please try downloading the file instead."
            )
    
    else:
        # For other file types, return an error
        raise HTTPException(
            status_code=400,
            detail=f"Preview not supported for file type: {policy.file_type}. Please download the file instead."
        )


@router.get("/{policy_id}/content", tags=["policies"])
def get_policy_content(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user_from_token_param)
):
    """Extract and return text content from policy file"""
    
    policy = db.query(Policy).filter(
        Policy.id == policy_id,
        Policy.is_active == True
    ).first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if not os.path.exists(policy.file_path):
        raise HTTPException(status_code=404, detail="Policy file not found")
    
    try:
        # Extract text content based on file type
        if policy.file_type.lower() == 'pdf':
            content = extract_pdf_text(policy.file_path)
        elif policy.file_type.lower() in ['doc', 'docx']:
            content = extract_docx_text(policy.file_path)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Text extraction not supported for file type: {policy.file_type}"
            )
        
        # Log audit
        from app.utils.audit import create_audit_log
        create_audit_log(
            db=db,
            user_id=str(current_user.id),
            action="view_policy_content",
            resource_type="policy",
            resource_id=str(policy.id),
            metadata={
                "policy_name": policy.name,
                "file_name": policy.file_name,
                "content_length": len(content)
            }
        )
        
        return {
            "policy_id": str(policy.id),
            "policy_name": policy.name,
            "file_name": policy.file_name,
            "content": content,
            "file_type": policy.file_type
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract content: {str(e)}"
        )


def extract_pdf_text(file_path: str) -> str:
    """Extract text content from PDF file with improved formatting"""
    try:
        # Try pdfplumber first as it generally provides better text extraction
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    # Clean up the extracted text
                    page_text = page_text.replace('\x00', '')  # Remove null characters
                    page_text = ' '.join(page_text.split())  # Normalize whitespace
                    text += page_text + "\n\n"
            
            # Post-process the entire text
            text = text.strip()
            # Fix common extraction issues
            text = text.replace('\n\n\n', '\n\n')  # Remove excessive line breaks
            text = text.replace('  ', ' ')  # Remove double spaces
            return text
            
    except ImportError:
        # Fallback to PyPDF2 if pdfplumber is not available
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        # Clean up the extracted text
                        page_text = page_text.replace('\x00', '')  # Remove null characters
                        page_text = ' '.join(page_text.split())  # Normalize whitespace
                        text += page_text + "\n\n"
                
                # Post-process the entire text
                text = text.strip()
                # Fix common extraction issues
                text = text.replace('\n\n\n', '\n\n')  # Remove excessive line breaks
                text = text.replace('  ', ' ')  # Remove double spaces
                return text
                
        except ImportError:
            raise Exception("PDF text extraction requires PyPDF2 or pdfplumber library")


def extract_docx_text(file_path: str) -> str:
    """Extract text content from DOCX file"""
    try:
        from docx import Document
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except ImportError:
        raise Exception("DOCX text extraction requires python-docx library")


def _build_policy_response(db: Session, policy: Policy) -> PolicyRead:
    """Helper function to build PolicyRead response with related data"""
    
    # Get related data
    org_unit_name = None
    if policy.org_unit:
        org_unit_name = policy.org_unit.name
    elif policy.org_unit_id is None:
        org_unit_name = "All Organizations"
    
    creator = db.query(User).filter(User.id == policy.created_by).first()
    creator_name = creator.name if creator else "Unknown"
    
    updater_name = None
    if policy.updated_by:
        updater = db.query(User).filter(User.id == policy.updated_by).first()
        updater_name = updater.name if updater else "Unknown"
    
    return PolicyRead(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        org_unit_id=policy.org_unit_id,
        file_path=policy.file_path,
        file_name=policy.file_name,
        file_type=policy.file_type,
        file_size=policy.file_size,
        created_by=policy.created_by,
        updated_by=policy.updated_by,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        is_active=policy.is_active,
        org_unit_name=org_unit_name,
        creator_name=creator_name,
        updater_name=updater_name
    )