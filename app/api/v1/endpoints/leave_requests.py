from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.leave_request import LeaveRequest, LeaveRequestStatus
from ....models.user import User, UserRole
from ....models.class_session import ClassSession
from ....models.attendance import Attendance, AttendanceStatus, VerificationMethod
from ....schemas.leave_request import LeaveRequestCreate, LeaveRequestOut, LeaveRequestReview, LeaveRequestWithDetails
from ....services.notifications import create_notification
from .users import get_current_user
from datetime import datetime

router = APIRouter()


def _can_review_leave_request(user: User, leave_request: LeaveRequest, db: Session) -> bool:
    """Lecturers who teach the session's course or admins can review."""
    if user.role == UserRole.admin:
        return True
    if user.role != UserRole.lecturer:
        return False
    session = db.query(ClassSession).filter(ClassSession.id == leave_request.session_id).first()
    if not session or not session.course:
        return False
    course = session.course
    return (
        course.lecturer_id == user.id
        or user in course.lecturers
    )


@router.get("/", response_model=List[LeaveRequestWithDetails])
def get_leave_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy.orm import joinedload
    query = db.query(LeaveRequest).options(
        joinedload(LeaveRequest.student),
        joinedload(LeaveRequest.session).joinedload(ClassSession.course),
    )
    if current_user.role.name == "student":
        query = query.filter(LeaveRequest.student_id == current_user.id)
    requests = query.all()
    result = []
    for req in requests:
        data = LeaveRequestWithDetails.model_validate(req)
        if req.student:
            data.student_name = req.student.name
        if req.session and req.session.course:
            data.course_name = req.session.course.name
            data.session_start = req.session.start_time
            data.session_room = req.session.room
        result.append(data)
    return result


@router.post("/", response_model=LeaveRequestOut, status_code=status.HTTP_201_CREATED)
def create_leave_request(
    request_in: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Check if student is marked as ABSENT for this session
    attendance = db.query(Attendance).filter(
        Attendance.student_id == current_user.id,
        Attendance.session_id == request_in.session_id
    ).first()
    
    if not attendance or attendance.status != AttendanceStatus.absent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave requests can only be submitted for sessions where you are marked as ABSENT."
        )

    # 2. Prevent duplicate requests
    existing_req = db.query(LeaveRequest).filter(
        LeaveRequest.student_id == current_user.id,
        LeaveRequest.session_id == request_in.session_id
    ).first()
    
    if existing_req:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A leave request already exists for this session."
        )

    db_req = LeaveRequest(**request_in.dict(), student_id=current_user.id)
    db.add(db_req)
    db.commit()
    db.refresh(db_req)
    return db_req


@router.patch("/{request_id}", response_model=LeaveRequestOut)
def review_leave_request(
    request_id: int,
    review_in: LeaveRequestReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve or reject a leave request. Only lecturers of the session's course or admins."""
    if review_in.status not in (LeaveRequestStatus.approved, LeaveRequestStatus.rejected):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be approved or rejected"
        )
    db_req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not db_req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if db_req.status != LeaveRequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave request has already been reviewed"
        )
    if not _can_review_leave_request(current_user, db_req, db):
        raise HTTPException(status_code=403, detail="Not authorized to review this leave request")
    db_req.status = review_in.status
    db_req.reviewed_by = current_user.id
    
    # If approved, update attendance to present
    if review_in.status == LeaveRequestStatus.approved:
        attendance = db.query(Attendance).filter(
            Attendance.student_id == db_req.student_id,
            Attendance.session_id == db_req.session_id
        ).first()
        
        if attendance:
            attendance.status = AttendanceStatus.present
            attendance.timestamp = datetime.utcnow()
            attendance.verification_method = VerificationMethod.manual_override
            
    db.commit()
    db.refresh(db_req)

    # Notify the student
    status_text = "approved" if review_in.status == LeaveRequestStatus.approved else "rejected"
    create_notification(
        db,
        user_id=db_req.student_id,
        title="Leave Request " + status_text.capitalize(),
        message=f"Your leave request for the session has been {status_text}.",
    )

    return db_req
