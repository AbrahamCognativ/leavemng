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

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '../../uploads')
UPLOAD_DIR = os.path.abspath(UPLOAD_DIR)
LEAVE_UPLOADS_DIR = os.path.join(UPLOAD_DIR, 'leave_documents')
PROFILE_UPLOADS_DIR = os.path.join(UPLOAD_DIR, 'profile_images')
os.makedirs(LEAVE_UPLOADS_DIR, exist_ok=True)
os.makedirs(PROFILE_UPLOADS_DIR, exist_ok=True)

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
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    # Only the user themselves or HR/Admin can upload
    # ICs can only upload for themselves
    if str(current_user.id) != str(user_id):
        # Only HR or Admin can upload for others
        if current_user.role_band not in ("HR", "Admin") and current_user.role_title not in ("HR", "Admin"):
            raise HTTPException(status_code=403, detail="Not permitted.")
    # Save profile image
    ext = os.path.splitext(file.filename)[1]
    filename = f"{user_id}{ext}"
    file_location = os.path.join(PROFILE_UPLOADS_DIR, filename)
    with open(file_location, "wb") as f:
        content = await file.read()
        f.write(content)
    user.profile_image_url = f"/uploads/profile_images/{filename}"
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

    return {"detail": "Profile image uploaded successfully.", "profile_image_url": user.profile_image_url}

