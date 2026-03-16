from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.course import Course
from ....models.user import User, UserRole
from ....schemas.course import CourseCreate, CourseOut, EnrollmentRequest
from .users import get_current_user

router = APIRouter()

@router.get("/", response_model=List[CourseOut])
def get_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Course).filter(Course.lecturer_id == current_user.id).all()

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

@router.post("/{course_id}/enroll", status_code=status.HTTP_200_OK)
def enroll_students(
    course_id: int,
    enrollment: EnrollmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.lecturer:
        raise HTTPException(status_code=403, detail="Only lecturers can enroll students")
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this course")

    added_count = 0
    for student_data in enrollment.students:
        # Check if user already exists by student_id
        student = db.query(User).filter(User.student_id == student_data.student_id).first()
        
        if not student:
            # Create a placeholder user
            # We generate a dummy email and password since they haven't "registered" themselves yet
            dummy_email = f"{student_data.student_id}@classtrack.placeholder"
            student = User(
                name=student_data.name,
                email=dummy_email,
                student_id=student_data.student_id,
                role=UserRole.student,
                hashed_password="placeholder_not_for_login"
            )
            db.add(student)
            db.flush() # Get the ID

        # Link to course if not already linked
        if student not in course.students:
            course.students.append(student)
            added_count += 1

    db.commit()
    return {"message": f"Successfully enrolled {added_count} students", "total_enrolled": len(course.students)}
