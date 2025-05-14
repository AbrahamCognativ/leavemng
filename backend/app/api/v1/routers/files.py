from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import List
import os
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timezone
from app.db.session import get_db
from app.models.leave_document import LeaveDocument
from app.models.leave_request import LeaveRequest
from app.models.user import User
from app.deps.permissions import get_current_user, require_role

# Get upload directory from settings but handle Docker vs local environment
from app.settings import get_settings
settings = get_settings()

# Check if the configured path is accessible
config_path = getattr(settings, 'UPLOAD_DIR', '/app/api/uploads')
try:
    # Try to create a test directory to see if we have write access
    test_path = os.path.join(config_path, 'test_access')
    os.makedirs(test_path, exist_ok=True)
    os.rmdir(test_path)  # Clean up after test
    
    # If we get here, the path is writable
    UPLOAD_DIR = config_path
    print(f"[INFO] Using configured upload directory: {UPLOAD_DIR}")
    
except (OSError, PermissionError):
    # Fall back to a local path if the configured path is not accessible
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '../../uploads')
    UPLOAD_DIR = os.path.abspath(UPLOAD_DIR)
    print(f"[INFO] Falling back to local upload directory: {UPLOAD_DIR}")

# Create subdirectories
LEAVE_UPLOADS_DIR = os.path.join(UPLOAD_DIR, 'leave_documents')
PROFILE_UPLOADS_DIR = os.path.join(UPLOAD_DIR, 'profile_images')

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LEAVE_UPLOADS_DIR, exist_ok=True)
os.makedirs(PROFILE_UPLOADS_DIR, exist_ok=True)

print(f"[INFO] Using upload directory: {UPLOAD_DIR}")
print(f"[INFO] Profile images directory: {PROFILE_UPLOADS_DIR}")

router = APIRouter()

def can_access_leave_request(db: Session, leave_request_id: UUID, current_user: User):
    leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == leave_request_id).first()
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    # Only requester, their manager, HR, or Admin can access
    if (
        current_user.role_band not in ("HR", "Admin")
        and current_user.role_title not in ("HR", "Admin")
        and str(leave_request.user_id) != str(current_user.id)
        and str(getattr(leave_request, 'user', None).manager_id if hasattr(leave_request, 'user') else None) != str(current_user.id)
    ):
        raise HTTPException(status_code=403, detail="Not permitted.")
    return leave_request

@router.post("/upload/{leave_request_id}", tags=["files"])
async def upload_file(
    leave_request_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    leave_request = can_access_leave_request(db, leave_request_id, current_user)
    LEAVE_UPLOADS_DIR = os.path.join(UPLOAD_DIR, "leave_documents")
    req_dir = os.path.join(LEAVE_UPLOADS_DIR, str(leave_request_id))
    os.makedirs(req_dir, exist_ok=True)
    file_location = os.path.join(req_dir, file.filename)
    with open(file_location, "wb") as f:
        content = await file.read()
        f.write(content)
    # Store metadata
    leave_doc = LeaveDocument(
        request_id=leave_request_id,
        file_path=file_location,
        file_name=file.filename,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(leave_doc)
    db.commit()
    db.refresh(leave_doc)
    return {"filename": file.filename, "detail": "File uploaded successfully.", "document_id": str(leave_doc.id)}

@router.get("/download/{leave_request_id}/{document_id}", tags=["files"])
def download_file(
    leave_request_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    leave_request = can_access_leave_request(db, leave_request_id, current_user)
    doc = db.query(LeaveDocument).filter(LeaveDocument.id == document_id, LeaveDocument.request_id == leave_request_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(doc.file_path, filename=doc.file_name)

@router.get("/list/{leave_request_id}", tags=["files"])
def list_files(
    leave_request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    leave_request = can_access_leave_request(db, leave_request_id, current_user)
    docs = db.query(LeaveDocument).filter(LeaveDocument.request_id == leave_request_id).all()
    return [
        {"document_id": str(d.id), "file_name": d.file_name, "uploaded_at": d.uploaded_at} for d in docs
    ]

@router.delete("/delete/{leave_request_id}/{document_id}", tags=["files"])
def delete_file(
    leave_request_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    leave_request = can_access_leave_request(db, leave_request_id, current_user)
    doc = db.query(LeaveDocument).filter(LeaveDocument.id == document_id, LeaveDocument.request_id == leave_request_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    os.remove(doc.file_path)
    db.delete(doc)
    db.commit()
    return {"detail": "File deleted successfully."}

@router.post("/upload-profile-image/{user_id}", tags=["files"])
async def upload_profile_image(
    user_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
            
        # Check permissions
        # Only the user themselves or HR/Admin can upload
        # ICs can only upload for themselves
        if str(current_user.id) != str(user_id):
            # Only HR or Admin can upload for others
            if current_user.role_band not in ("HR", "Admin") and current_user.role_title not in ("HR", "Admin"):
                raise HTTPException(status_code=403, detail="Not permitted.")
                
        # Validate file type
        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp", ".gif"]
        ext = os.path.splitext(file.filename)[1].lower()
        
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )
            
        # Save profile image
        filename = f"{user_id}{ext}"
        file_location = os.path.join(PROFILE_UPLOADS_DIR, filename)
        
        # Read file content
        content = await file.read()
        
        # Ensure it's not empty
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded.")
            
        # Write file to disk
        with open(file_location, "wb") as f:
            f.write(content)
            
        # Update user record with profile image URL
        # Ensure the URL is correctly formatted for static file serving
        profile_image_url = f"/uploads/profile_images/{filename}"
        user.profile_image_url = profile_image_url
        db.commit()
        
        # Log profile image upload in audit logs
        from app.utils.audit import create_audit_log
        create_audit_log(
            db=db,
            user_id=str(current_user.id),
            action="upload_profile_image",
            resource_type="user",
            resource_id=str(user_id),
            metadata={
                "uploaded_by": current_user.email,
                "self_upload": str(current_user.id) == str(user_id),
                "file_type": ext,
                "file_path": file_location
            }
        )
        
        print(f"[INFO] Profile image uploaded successfully for user {user_id}: {profile_image_url}")
        
        # Return success response with the URL
        return {
            "detail": "Profile image uploaded successfully.", 
            "profile_image_url": profile_image_url,
            "success": True
        }
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        # Log any other errors
        print(f"[ERROR] Failed to upload profile image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload profile image: {str(e)}")
