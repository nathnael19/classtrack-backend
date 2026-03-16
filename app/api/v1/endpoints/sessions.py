from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ....db.session import get_db
from ....models.class_session import ClassSession
from ....models.attendance import Attendance, AttendanceStatus
from ....models.course import Course
from ....models.user import User, UserRole
from ....schemas.class_session import ClassSessionCreate, ClassSessionOut
from .users import get_current_user

router = APIRouter()

@router.get("/", response_model=List[ClassSessionOut])
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(ClassSession).all()

# ⚠️ IMPORTANT: Specific string routes MUST come BEFORE wildcard /{session_id} routes
@router.get("/active", response_model=List[ClassSessionOut])
def get_active_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    now = datetime.utcnow()
    return db.query(ClassSession).filter(
        ClassSession.start_time <= now,
        ClassSession.end_time >= now
    ).all()

@router.get("/active-lecturer", response_model=ClassSessionOut)
def get_active_lecturer_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the most recently started active session for the currently logged-in lecturer.
    NOTE: This route must appear BEFORE /{session_id} to avoid being swallowed by it.
    """
    now = datetime.utcnow()

    print(f"DEBUG /active-lecturer: lecturer_id={current_user.id}, now={now}")

    session = db.query(ClassSession).filter(
        ClassSession.course.has(lecturer_id=current_user.id),
        ClassSession.start_time <= now,
        ClassSession.end_time >= now
    ).order_by(ClassSession.start_time.desc()).first()

    if not session:
        # Extra diagnostics: check if any session exists for this lecturer at all
        any_session = db.query(ClassSession).filter(
            ClassSession.course.has(lecturer_id=current_user.id)
        ).order_by(ClassSession.start_time.desc()).first()

        if any_session:
            print(f"DEBUG: Latest session for lecturer: id={any_session.id}, start={any_session.start_time}, end={any_session.end_time}")
        else:
            print("DEBUG: No sessions found for this lecturer at all.")

        raise HTTPException(status_code=404, detail="No active session found")

    print(f"DEBUG: Found active session id={session.id}")
    return session

@router.post("/", response_model=ClassSessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    session_in: ClassSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.lecturer:
        raise HTTPException(status_code=403, detail="Only lecturers can create sessions")
    
    course = db.query(Course).filter(Course.id == session_in.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to create sessions for this course")

    db_session = ClassSession(**session_in.dict())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@router.get("/{session_id}", response_model=ClassSessionOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.patch("/{session_id}/stop", response_model=ClassSessionOut)
def stop_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually end a session by setting its end_time to now.
    """
    session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if session.course.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    session.end_time = datetime.utcnow()
    
    # NEW: Mark absentees for the stopped session
    enrolled_students = session.course.students
    marked_student_ids = [a.student_id for a in session.attendances]
    
    for student in enrolled_students:
        if student.id not in marked_student_ids:
            absent_attendance = Attendance(
                student_id=student.id,
                session_id=session.id,
                status=AttendanceStatus.absent,
                timestamp=datetime.utcnow()
            )
            db.add(absent_attendance)
    
    db.commit()
    db.refresh(session)
    return session
