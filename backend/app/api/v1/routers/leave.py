from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.leave_request import LeaveRequestRead, LeaveRequestCreate
from app.models.leave_request import LeaveRequest
from app.db.session import get_db
from uuid import UUID

router = APIRouter()

@router.get("/", response_model=list[LeaveRequestRead])
def list_leave_requests(db: Session = Depends(get_db)):
    requests = db.query(LeaveRequest).all()
    return [LeaveRequestRead.from_orm(req) for req in requests]

@router.post("/", response_model=LeaveRequestRead)
def create_leave_request(req: LeaveRequestCreate, db: Session = Depends(get_db)):
    db_req = LeaveRequest(**req.dict())
    db.add(db_req)
    try:
        db.commit()
        db.refresh(db_req)
    except Exception as e:
        db.rollback()
        if hasattr(e, 'orig') and hasattr(e.orig, 'diag') and 'unique' in str(e.orig).lower():
            raise HTTPException(status_code=400, detail="Duplicate leave request")
        raise HTTPException(status_code=500, detail="Internal server error")
    return LeaveRequestRead.from_orm(db_req)

@router.get("/{request_id}", response_model=LeaveRequestRead)
def get_leave_request(request_id: UUID, db: Session = Depends(get_db)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return LeaveRequestRead.from_orm(req)

@router.put("/{request_id}", response_model=LeaveRequestRead)
def update_leave_request(request_id: UUID, req_update: LeaveRequestCreate, db: Session = Depends(get_db)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    for k, v in req_update.dict().items():
        setattr(req, k, v)
    try:
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not update leave request")
    return LeaveRequestRead.from_orm(req)

@router.patch("/{request_id}/approve", response_model=LeaveRequestRead)
def approve_leave_request(request_id: UUID, db: Session = Depends(get_db)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")
    req.status = "approved"
    try:
        db.commit()
        db.refresh(req)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not approve leave request")
    return LeaveRequestRead.from_orm(req)
