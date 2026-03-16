from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.course import Course
from ....models.user import User, UserRole
from ....schemas.course import CourseCreate, CourseOut
from .users import get_current_user

router = APIRouter()

@router.get("/", response_model=List[CourseOut])
def get_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Course).all()

@router.post("/", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    course_in: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.lecturer:
        raise HTTPException(status_code=403, detail="Only lecturers can create courses")
    
    db_course = Course(
        name=course_in.name,
        code=course_in.code,
        lecturer_id=current_user.id
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

@router.get("/{course_id}", response_model=CourseOut)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course
