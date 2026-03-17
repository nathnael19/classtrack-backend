from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.leave_request import LeaveRequest
from ....models.user import User
from ....schemas.leave_request import LeaveRequestCreate, LeaveRequestOut
from .users import get_current_user

router = APIRouter()

@router.get("/", response_model=List[LeaveRequestOut])
def get_leave_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.name == "student":
        return db.query(LeaveRequest).filter(LeaveRequest.student_id == current_user.id).all()
    # Lecturers/Admins can see all
    return db.query(LeaveRequest).all()

@router.post("/", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
def create_leave_request(
    request_in: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_req = LeaveRequest(**request_in.dict(), student_id=current_user.id)
    db.add(db_req)
    db.commit()
    db.refresh(db_req)
    return db_req
