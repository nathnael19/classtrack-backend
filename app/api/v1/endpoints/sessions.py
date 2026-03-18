from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ....db.session import get_db
from ....models.class_session import ClassSession, SessionStatus
from ....models.attendance import Attendance, AttendanceStatus
from ....models.course import Course
from ....models.user import User, UserRole
from ....schemas.class_session import ClassSessionCreate, ClassSessionOut, SessionStudentOut
from .users import get_current_user

router = APIRouter()

@router.get("/{session_id}/students", response_model=List[SessionStudentOut])
def get_session_students(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.lecturer:
        raise HTTPException(status_code=403, detail="Only lecturers can view detailed enrollment")
    
    session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Authorized?
    course = session.course
    is_authorized = (course.lecturer_id == current_user.id) or (current_user in course.lecturers)
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized for this course")
    
    # Get all enrolled students
    students = course.students
    
    # Get all attendance records for this session
    attendance_map = {
        a.student_id: a for a in db.query(Attendance).filter(Attendance.session_id == session_id).all()
    }
    
    result = []
    for s in students:
        att = attendance_map.get(s.id)
        result.append({
            "id": s.id,
            "name": s.name,
            "student_id": s.student_id,
            "status": att.status.value if att else None,
            "timestamp": att.timestamp if att else None
        })
    
    return result

def populate_is_present(sessions: List[ClassSession], user_id: int, db: Session):
    """
    Populate is_present field for a list of sessions for a specific student.
    """
    if not sessions:
        return
    
    # Get all sessions where this student is marked present
    present_session_ids = {
        a[0] for a in db.query(Attendance.session_id)
        .filter(
            Attendance.student_id == user_id,
            Attendance.status == AttendanceStatus.present,
            Attendance.session_id.in_([s.id for s in sessions])
        ).all()
    }
    
    for s in sessions:
        s.is_present = s.id in present_session_ids

def mark_absentees(session: ClassSession, db: Session):
    """
    Mark all enrolled students who haven't scanned as absent.
    """
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
    
    session.status = SessionStatus.completed
    db.commit()

@router.get("/", response_model=List[ClassSessionOut])
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    query = db.query(ClassSession)
    
    if current_user.role == UserRole.student:
        course_ids = [c.id for c in current_user.enrolled_courses]
        query = query.filter(ClassSession.course_id.in_(course_ids))
    elif current_user.role == UserRole.lecturer:
        # Only see sessions owned by this lecturer
        # Fallback for old sessions that don't have lecturer_id yet
        query = query.filter(
            or_(
                ClassSession.lecturer_id == current_user.id,
                (ClassSession.lecturer_id == None) & ClassSession.course.has(lecturer_id=current_user.id)
            )
        )
        
    if start_date:
        query = query.filter(ClassSession.start_time >= start_date)
    if end_date:
        query = query.filter(ClassSession.end_time <= end_date)
        
    sessions = query.order_by(ClassSession.start_time.asc()).all()
    
    if current_user.role == UserRole.student:
        populate_is_present(sessions, current_user.id, db)
        
    return sessions

# ⚠️ IMPORTANT: Specific string routes MUST come BEFORE wildcard /{session_id} routes
@router.get("/active", response_model=List[ClassSessionOut])
def get_active_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    now = datetime.utcnow()
    # Lazy cleanup: Find sessions that are "active" but past their end_time
    expired_sessions = db.query(ClassSession).filter(
        ClassSession.status == SessionStatus.active,
        ClassSession.end_time < now
    ).all()
    
    for session in expired_sessions:
        mark_absentees(session, db)

    query = db.query(ClassSession).filter(
        ClassSession.start_time <= now,
        ClassSession.end_time >= now,
        ClassSession.status != SessionStatus.completed
    )
    
    if current_user.role == UserRole.student:
        # Filter sessions for courses the student is enrolled in
        course_ids = [c.id for c in current_user.enrolled_courses]
        query = query.filter(ClassSession.course_id.in_(course_ids))
    
    sessions = query.all()
    
    if current_user.role == UserRole.student:
        populate_is_present(sessions, current_user.id, db)
        
    return sessions

@router.get("/upcoming", response_model=List[ClassSessionOut])
def get_upcoming_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    now = datetime.utcnow()
    query = db.query(ClassSession).filter(ClassSession.start_time > now)
    
    if current_user.role == UserRole.student:
        course_ids = [c.id for c in current_user.enrolled_courses]
        query = query.filter(ClassSession.course_id.in_(course_ids))
    
    sessions = query.order_by(ClassSession.start_time.asc()).limit(10).all()
    
    if current_user.role == UserRole.student:
        populate_is_present(sessions, current_user.id, db)
        
    return sessions

from sqlalchemy import or_

@router.get("/active-lecturer", response_model=ClassSessionOut)
def get_active_lecturer_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    now = datetime.utcnow()
    # Filter by direct lecturer_id OR fallback to course lead lecturer for old sessions
    session = db.query(ClassSession).filter(
        or_(
            ClassSession.lecturer_id == current_user.id,
            (ClassSession.lecturer_id == None) & ClassSession.course.has(lecturer_id=current_user.id)
        ),
        ClassSession.start_time <= now,
        ClassSession.end_time >= now
    ).order_by(ClassSession.start_time.desc()).first()

    if not session:
        raise HTTPException(status_code=404, detail="No active session found")
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
    
    # Check if user is lead lecturer OR one of the assigned lecturers
    is_authorized = (course.lecturer_id == current_user.id) or (current_user in course.lecturers)
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized to create sessions for this course")

    db_session = ClassSession(**session_in.dict(), lecturer_id=current_user.id)
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
    mark_absentees(session, db)
    db.refresh(session)
    return session
