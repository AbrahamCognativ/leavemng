from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from app.db.session import get_db
from app.models.user_document import UserDocument
from app.models.user import User
from app.schemas.user_document import (
    UserDocumentCreate, UserDocumentUpdate, UserDocumentRead, 
    UserDocumentListItem, MyDocumentListItem, UserDocumentStats
)
from app.deps.permissions import get_current_user, require_role, get_current_user_from_token_param, UserInToken
from app.settings import get_settings
from typing import List, Optional
import uuid
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

router = APIRouter()

# Create uploads directory for user documents
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '../../uploads')
USER_DOCUMENTS_DIR = os.path.join(UPLOAD_DIR, 'user_documents')
os.makedirs(USER_DOCUMENTS_DIR, exist_ok=True)

ALLOWED_FILE_TYPES = {
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
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


@router.post("/", response_model=UserDocumentRead, tags=["user-documents"],
             dependencies=[Depends(require_role(["HR", "Admin", "Manager"]))])
async def create_user_document(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    user_id: str = Form(...),
    document_type: Optional[str] = Form(None),
    send_email_notification: bool = Form(True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a document for a specific user (Admin/HR/Manager only)"""
    
    # Validate file type
    file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
    if file_extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_FILE_TYPES.keys())}"
        )
    
    # Validate user_id
    try:
        target_user_uuid = uuid.UUID(user_id)
        target_user = db.query(User).filter(
            User.id == target_user_uuid,
            User.is_active == True
        ).first()
        if not target_user:
            raise HTTPException(status_code=400, detail="Target user not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_name = f"{file_id}_{file.filename}"
    file_path = os.path.join(USER_DOCUMENTS_DIR, file_name)
    
    # Save file
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        file_size = len(content)
        file_size_str = get_file_size_string(file_size)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Create user document record
    user_document = UserDocument(
        name=name,
        description=description,
        file_path=file_path,
        file_name=file.filename,
        file_type=file_extension,
        file_size=file_size_str,
        user_id=target_user_uuid,
        document_type=document_type,
        send_email_notification=send_email_notification,
        created_by=current_user.id
    )
    
    db.add(user_document)
    db.commit()
    db.refresh(user_document)
    
    # Log audit
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="create_user_document",
        resource_type="user_document",
        resource_id=str(user_document.id),
        metadata={
            "document_name": name,
            "target_user_id": str(target_user_uuid),
            "target_user_email": target_user.email,
            "file_name": file.filename,
            "file_type": file_extension,
            "document_type": document_type
        }
    )
    
    # Send email notification if requested
    if send_email_notification:
        try:
            await send_document_notification_email(target_user, user_document, current_user)
            user_document.email_sent_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as e:
            # Log error but don't fail the document creation
            import logging
            logging.error(f"Failed to send document notification email: {e}")
    
    return _build_user_document_response(db, user_document)


@router.get("/", response_model=List[UserDocumentListItem], tags=["user-documents"],
            dependencies=[Depends(require_role(["HR", "Admin", "Manager"]))])
def list_user_documents(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all user documents (Admin/HR/Manager only)"""
    
    query = db.query(UserDocument).filter(UserDocument.is_active == True)
    
    # Filter by user_id if provided
    if user_id:
        try:
            user_uuid = uuid.UUID(user_id)
            query = query.filter(UserDocument.user_id == user_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Filter by document_type if provided
    if document_type:
        query = query.filter(UserDocument.document_type == document_type)
    
    documents = query.options(
        joinedload(UserDocument.user),
        joinedload(UserDocument.creator)
    ).order_by(desc(UserDocument.created_at)).all()
    
    result = []
    for doc in documents:
        result.append(UserDocumentListItem(
            id=doc.id,
            name=doc.name,
            description=doc.description,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            document_type=doc.document_type,
            user_id=doc.user_id,
            user_name=doc.user.name,
            user_email=doc.user.email,
            email_sent_at=doc.email_sent_at,
            created_by=doc.created_by,
            creator_name=doc.creator.name,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        ))
    
    return result


@router.get("/my-documents", response_model=List[MyDocumentListItem], tags=["user-documents"])
def get_my_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's documents"""
    
    documents = db.query(UserDocument).options(
        joinedload(UserDocument.creator)
    ).filter(
        UserDocument.user_id == current_user.id,
        UserDocument.is_active == True
    ).order_by(desc(UserDocument.created_at)).all()
    
    result = []
    for doc in documents:
        result.append(MyDocumentListItem(
            id=doc.id,
            name=doc.name,
            description=doc.description,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            document_type=doc.document_type,
            created_at=doc.created_at,
            creator_name=doc.creator.name
        ))
    
    return result


@router.get("/{document_id}", response_model=UserDocumentRead, tags=["user-documents"])
def get_user_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific user document"""
    
    document = db.query(UserDocument).filter(
        UserDocument.id == document_id,
        UserDocument.is_active == True
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions: user can view their own documents, admin/hr/manager can view all
    if (document.user_id != current_user.id and 
        current_user.role_band not in ["Admin", "HR", "Manager"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return _build_user_document_response(db, document)


@router.put("/{document_id}", response_model=UserDocumentRead, tags=["user-documents"],
            dependencies=[Depends(require_role(["HR", "Admin", "Manager"]))])
def update_user_document(
    document_id: uuid.UUID,
    document_update: UserDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user document metadata (Admin/HR/Manager only)"""
    
    document = db.query(UserDocument).filter(
        UserDocument.id == document_id,
        UserDocument.is_active == True
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update fields
    update_data = document_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    document.updated_by = current_user.id
    document.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(document)
    
    # Log audit
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="update_user_document",
        resource_type="user_document",
        resource_id=str(document.id),
        metadata={
            "document_name": document.name,
            "updated_fields": list(update_data.keys())
        }
    )
    
    return _build_user_document_response(db, document)


@router.delete("/{document_id}", tags=["user-documents"],
               dependencies=[Depends(require_role(["HR", "Admin"]))])
def delete_user_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete a user document (Admin/HR only)"""
    
    document = db.query(UserDocument).filter(
        UserDocument.id == document_id,
        UserDocument.is_active == True
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Soft delete
    document.is_active = False
    document.updated_by = current_user.id
    document.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    # Log audit
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="delete_user_document",
        resource_type="user_document",
        resource_id=str(document.id),
        metadata={
            "document_name": document.name,
            "target_user_id": str(document.user_id),
            "file_name": document.file_name
        }
    )
    
    return {"detail": "Document deleted successfully"}


@router.get("/{document_id}/download", tags=["user-documents"])
def download_user_document(
    document_id: uuid.UUID,
    inline: bool = False,
    db: Session = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user_from_token_param)
):
    """Download user document file"""
    
    document = db.query(UserDocument).filter(
        UserDocument.id == document_id,
        UserDocument.is_active == True
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions: user can download their own documents, admin/hr/manager can download all
    if (document.user_id != current_user.id and 
        current_user.role_band not in ["Admin", "HR", "Manager"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Document file not found")
    
    # Log audit
    from app.utils.audit import create_audit_log
    create_audit_log(
        db=db,
        user_id=str(current_user.id),
        action="view_user_document" if inline else "download_user_document",
        resource_type="user_document",
        resource_id=str(document.id),
        metadata={
            "document_name": document.name,
            "file_name": document.file_name,
            "inline_view": inline
        }
    )
    
    # Set appropriate headers for inline viewing vs download
    if inline:
        response = FileResponse(
            document.file_path,
            media_type=ALLOWED_FILE_TYPES.get(document.file_type, 'application/octet-stream'),
            headers={
                "Content-Disposition": f"inline; filename={document.file_name}",
                "X-Frame-Options": "ALLOWALL",
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "Authorization, Content-Type"
            }
        )
        return response
    else:
        return FileResponse(
            document.file_path,
            filename=document.file_name,
            media_type=ALLOWED_FILE_TYPES.get(document.file_type, 'application/octet-stream')
        )


@router.get("/{document_id}/preview", tags=["user-documents"])
def preview_user_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: UserInToken = Depends(get_current_user_from_token_param)
):
    """Generate and serve a PDF preview of the user document"""
    
    document = db.query(UserDocument).filter(
        UserDocument.id == document_id,
        UserDocument.is_active == True
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check permissions
    if (document.user_id != current_user.id and 
        current_user.role_band not in ["Admin", "HR", "Manager"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Document file not found")
    
    # If it's already a PDF, serve it directly
    if document.file_type.lower() == 'pdf':
        # Log audit
        from app.utils.audit import create_audit_log
        create_audit_log(
            db=db,
            user_id=str(current_user.id),
            action="preview_user_document",
            resource_type="user_document",
            resource_id=str(document.id),
            metadata={
                "document_name": document.name,
                "file_name": document.file_name,
                "preview_type": "direct_pdf"
            }
        )
        
        return FileResponse(
            document.file_path,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={document.file_name}",
                "X-Frame-Options": "ALLOWALL",
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "Authorization, Content-Type"
            }
        )
    
    # For DOCX files, convert to PDF
    elif document.file_type.lower() in ['doc', 'docx']:
        try:
            from app.utils.document_converter import DocumentConverter
            
            if not DocumentConverter.is_conversion_available():
                raise HTTPException(
                    status_code=500,
                    detail="Document conversion not available. Please download the file instead."
                )
            
            preview_pdf_path = DocumentConverter.ensure_preview_exists(document.file_path)
            
            # Log audit
            from app.utils.audit import create_audit_log
            create_audit_log(
                db=db,
                user_id=str(current_user.id),
                action="preview_user_document",
                resource_type="user_document",
                resource_id=str(document.id),
                metadata={
                    "document_name": document.name,
                    "file_name": document.file_name,
                    "preview_type": "docx_to_pdf_conversion"
                }
            )
            
            preview_filename = f"{Path(document.file_name).stem}_preview.pdf"
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
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate preview: {str(e)}. Please try downloading the file instead."
            )
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Preview not supported for file type: {document.file_type}. Please download the file instead."
        )


@router.get("/stats/overview", response_model=UserDocumentStats, tags=["user-documents"],
            dependencies=[Depends(require_role(["HR", "Admin", "Manager"]))])
def get_user_documents_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user documents statistics (Admin/HR/Manager only)"""
    
    # Total documents
    total_documents = db.query(UserDocument).filter(UserDocument.is_active == True).count()
    
    # Documents by type
    type_counts = db.query(
        UserDocument.document_type,
        func.count(UserDocument.id).label('count')
    ).filter(
        UserDocument.is_active == True
    ).group_by(UserDocument.document_type).all()
    
    documents_by_type = {}
    for doc_type, count in type_counts:
        documents_by_type[doc_type or 'Other'] = count
    
    # Recent uploads (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_uploads = db.query(UserDocument).filter(
        UserDocument.is_active == True,
        UserDocument.created_at >= thirty_days_ago
    ).count()
    
    # Total users with documents
    total_users_with_documents = db.query(UserDocument.user_id).filter(
        UserDocument.is_active == True
    ).distinct().count()
    
    return UserDocumentStats(
        total_documents=total_documents,
        documents_by_type=documents_by_type,
        recent_uploads=recent_uploads,
        total_users_with_documents=total_users_with_documents
    )


async def send_document_notification_email(target_user: User, document: UserDocument, uploader: User):
    """Send document notification email to user with document attachment"""
    
    from app.settings import get_settings
    from app.utils.email_utils import send_email_with_attachment
    
    settings = get_settings()
    
    subject = f"New Document Available: {document.name}"
    
    body = f"""
Hello {target_user.name},

A new document has been uploaded to your account and is attached to this email:

📄 Document: {document.name}
📝 Description: {document.description or 'No description provided'}
📅 Uploaded: {document.created_at.strftime('%B %d, %Y at %I:%M %p UTC')}
👤 Uploaded by: {uploader.name}
📎 File: {document.file_name} ({document.file_size})

The document is attached to this email for your convenience. You can also view and download it by logging into the Leave Management System.

Best Regards,
Leave Management System Team
"""
    
    html = f"""
    <html>
    <body style='font-family: Arial, sans-serif; background: #f9f9f9; padding: 24px;'>
      <div style='max-width: 600px; margin: auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #eee; padding: 32px;'>
        <h2 style='color: #2d6cdf; margin-top: 0;'>📄 New Document Available</h2>
        <p style='font-size: 16px; color: #333;'>
          Hello {target_user.name},<br><br>
          A new document has been uploaded to your account and is attached to this email.
        </p>
        
        <div style='background: #f8f9fa; border-left: 4px solid #2d6cdf; padding: 16px; margin: 24px 0;'>
          <h3 style='margin: 0 0 8px 0; color: #2d6cdf;'>{document.name}</h3>
          <p style='margin: 0; color: #666;'>{document.description or 'No description provided'}</p>
        </div>
        
        <div style='background: #e7f3ff; border: 1px solid #b3d9ff; border-radius: 4px; padding: 16px; margin: 24px 0;'>
          <p style='margin: 4px 0; color: #0066cc;'><strong>📅 Uploaded:</strong> {document.created_at.strftime('%B %d, %Y at %I:%M %p UTC')}</p>
          <p style='margin: 4px 0; color: #0066cc;'><strong>👤 Uploaded by:</strong> {uploader.name}</p>
          <p style='margin: 4px 0; color: #0066cc;'><strong>📎 File:</strong> {document.file_name} ({document.file_size})</p>
        </div>
        
        <div style='background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 16px; margin: 24px 0;'>
          <p style='margin: 0; color: #856404;'><strong>📎 Attachment:</strong> The document is attached to this email for your convenience.</p>
        </div>
        
        <p style='font-size: 16px; color: #333;'>
          You can also view and download this document by logging into the Leave Management System.
        </p>
        
        <a href='{settings.SITE_URL}/#/docs' style='display: inline-block; margin: 24px 0 8px 0; padding: 12px 32px; background: #2d6cdf; color: #fff; border-radius: 4px; text-decoration: none; font-size: 16px; font-weight: bold;'>
          View My Documents
        </a>
        
        <p style='font-size: 15px; color: #333; margin-top: 32px;'>Best Regards,<br>Leave Management System Team</p>
      </div>
    </body>
    </html>
    """
    
    # Send email with document attachment
    send_email_with_attachment(
        subject=subject,
        body=body,
        recipients=[target_user.email],
        html=html,
        attachment_path=document.file_path,
        attachment_name=document.file_name
    )


def _build_user_document_response(db: Session, document: UserDocument) -> UserDocumentRead:
    """Helper function to build UserDocumentRead response with related data"""
    
    # Get related data
    user = db.query(User).filter(User.id == document.user_id).first()
    creator = db.query(User).filter(User.id == document.created_by).first()
    updater = None
    if document.updated_by:
        updater = db.query(User).filter(User.id == document.updated_by).first()
    
    return UserDocumentRead(
        id=document.id,
        name=document.name,
        description=document.description,
        file_path=document.file_path,
        file_name=document.file_name,
        file_type=document.file_type,
        file_size=document.file_size,
        user_id=document.user_id,
        document_type=document.document_type,
        send_email_notification=document.send_email_notification,
        email_sent_at=document.email_sent_at,
        created_by=document.created_by,
        updated_by=document.updated_by,
        created_at=document.created_at,
        updated_at=document.updated_at,
        is_active=document.is_active,
        user_name=user.name if user else None,
        user_email=user.email if user else None,
        creator_name=creator.name if creator else None,
        updater_name=updater.name if updater else None
    )