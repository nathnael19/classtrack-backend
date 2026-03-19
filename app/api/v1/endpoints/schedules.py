from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ....db.session import get_db
from ....models.user import User, UserRole
from ....models.course_schedule import CourseSchedule
from ....schemas.course_schedule import CourseScheduleOut
from .users import get_current_user
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from ....models.enrollment import enrollment_association

router = APIRouter()

@router.get("/mine", response_model=List[CourseScheduleOut])
def get_my_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.lecturer:
        # Teachers see all schedules they are assigned to
        return db.query(CourseSchedule).options(
            joinedload(CourseSchedule.course),
            joinedload(CourseSchedule.lecturer)
        ).filter(CourseSchedule.lecturer_id == current_user.id).all()
    
    # Students see schedules for courses they are enrolled in, 
    # matched by their specific section in that course.
    
    # 1. Get student's enrollments with sections
    enrollments = db.execute(
        select(enrollment_association.c.course_id, enrollment_association.c.section)
        .where(enrollment_association.c.user_id == current_user.id)
    ).fetchall()
    
    if not enrollments:
        return []
    
    # 2. Query schedules matching course_id AND section
    schedules = []
    for course_id, section in enrollments:
        course_schedules = db.query(CourseSchedule).options(
            joinedload(CourseSchedule.course),
            joinedload(CourseSchedule.lecturer)
        ).filter(
            CourseSchedule.course_id == course_id,
            (CourseSchedule.section == section) | (CourseSchedule.section == None)
        ).all()
        schedules.extend(course_schedules)
    
    return schedules
