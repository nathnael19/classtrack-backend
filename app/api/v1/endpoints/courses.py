from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.course import Course
from ....models.class_session import ClassSession
from ....models.attendance import Attendance
from ....models.user import User, UserRole
from ....schemas.course import CourseCreate, CourseOut, CourseDetailOut, EnrollmentRequest, StudentActivityOut
from .users import get_current_user
from ....models.course_schedule import CourseSchedule
from ....schemas.course_schedule import CourseScheduleCreate, CourseScheduleOut
from sqlalchemy import insert, select, update
from ....models.enrollment import enrollment_association

router = APIRouter()

@router.get("/", response_model=List[CourseOut])
def get_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.admin:
        return db.query(Course).all()
    if current_user.role == UserRole.lecturer:
        return db.query(Course).filter(Course.lecturer_id == current_user.id).all()
    # For students, return enrolled courses
    return current_user.enrolled_courses

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

@router.get("/{course_id}", response_model=CourseDetailOut)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Verify authorization
    if course.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this course")

    # Get sessions related to this course
    sessions = db.query(ClassSession).filter(ClassSession.course_id == course_id).all()
    session_ids = [s.id for s in sessions]
    total_sessions = len(sessions)

    student_activities = []
    total_attendance_sum = 0
    
    # Get sections for students in this course
    enrollment_sections = {
        row.user_id: row.section for row in db.execute(
            select(enrollment_association.c.user_id, enrollment_association.c.section)
            .where(enrollment_association.c.course_id == course_id)
        ).fetchall()
    }

    for student in course.students:
        # Count attendance for this student in this course's sessions
        attendance_count = db.query(Attendance).filter(
            Attendance.student_id == student.id,
            Attendance.session_id.in_(session_ids)
        ).count() if session_ids else 0

        attendance_rate = (attendance_count / total_sessions * 100) if total_sessions > 0 else 0
        
        # Get last seen (latest attendance in this course)
        last_attendance = db.query(Attendance).filter(
            Attendance.student_id == student.id,
            Attendance.session_id.in_(session_ids)
        ).order_by(Attendance.timestamp.desc()).first() if session_ids else None

        # Determine status
        status = "Inactive"
        if attendance_rate >= 80:
            status = "Consistent"
        elif attendance_rate >= 50:
            status = "Moderate"
        elif attendance_count > 0:
            status = "At Risk"

        student_activities.append(StudentActivityOut(
            id=student.id,
            name=student.name,
            student_id=student.student_id,
            attendance_count=attendance_count,
            total_sessions=total_sessions,
            attendance_rate=attendance_rate,
            last_seen=last_attendance.timestamp if last_attendance else None,
            status=status,
            section=enrollment_sections.get(student.id)
        ))
        total_attendance_sum += attendance_rate

    avg_attendance = (total_attendance_sum / len(course.students)) if course.students else 0

    # Build the response
    return CourseDetailOut(
        id=course.id,
        name=course.name,
        code=course.code,
        lecturer_id=course.lecturer_id,
        student_count=len(course.students),
        total_sessions=total_sessions,
        average_attendance=avg_attendance,
        students=student_activities,
        schedules=course.schedules
    )

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

        # Link to course with section
        existing_enrollment = db.execute(
            enrollment_association.select().where(
                (enrollment_association.c.user_id == student.id) &
                (enrollment_association.c.course_id == course_id)
            )
        ).first()

        if not existing_enrollment:
            section_to_enroll = student_data.section or student.section
            stmt = insert(enrollment_association).values(
                user_id=student.id,
                course_id=course_id,
                section=section_to_enroll
            )
            db.execute(stmt)
            added_count += 1
        elif existing_enrollment.section != student_data.section:
            stmt = update(enrollment_association).where(
                (enrollment_association.c.user_id == student.id) &
                (enrollment_association.c.course_id == course_id)
            ).values(section=student_data.section)
            db.execute(stmt)

    db.commit()
    return {"message": f"Successfully enrolled {added_count} students", "total_enrolled": len(course.students)}

@router.post("/{course_id}/schedules", response_model=CourseScheduleOut, status_code=status.HTTP_201_CREATED)
def create_course_schedule(
    course_id: int,
    schedule_in: CourseScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.lecturer:
        raise HTTPException(status_code=403, detail="Only lecturers can manage schedules")
    
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this course")
    
    db_schedule = CourseSchedule(
        **schedule_in.dict(),
        course_id=course_id,
        lecturer_id=current_user.id
    )
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.lecturer:
        raise HTTPException(status_code=403, detail="Only lecturers can manage schedules")
    
    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if schedule.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this schedule")
    
    db.delete(schedule)
    db.commit()
    return None

