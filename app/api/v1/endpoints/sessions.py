from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.class_session import ClassSession
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

@router.get("/active", response_model=List[ClassSessionOut])
def get_active_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from datetime import datetime
    now = datetime.utcnow()
    # Simple active check: start_time <= now <= end_time
    # In a real app, we'd filter by student enrollment too
    return db.query(ClassSession).filter(
        ClassSession.start_time <= now,
        ClassSession.end_time >= now
    ).all()

@router.post("/", response_model=ClassSessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    session_in: ClassSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.lecturer:
        raise HTTPException(status_code=403, detail="Only lecturers can create sessions")
    
    # Verify course exists and belongs to lecturer
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
