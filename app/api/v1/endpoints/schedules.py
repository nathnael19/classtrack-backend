from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from ....db.session import get_db
from ....models.user import User, UserRole
from ....models.course_schedule import CourseSchedule
from ....schemas.course_schedule import CourseScheduleOut
from .users import get_current_user
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload
from ....models.enrollment import enrollment_association

router = APIRouter()

@router.get("/mine", response_model=List[CourseScheduleOut])
def get_my_schedules(
    skip: int = 0,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.lecturer:
        # Teachers see all schedules they are assigned to
        return db.query(CourseSchedule).options(
            joinedload(CourseSchedule.course),
            joinedload(CourseSchedule.lecturer)
        ).filter(CourseSchedule.lecturer_id == current_user.id).offset(skip).limit(limit).all()
    
    # Students see schedules for courses they are enrolled in, 
    # matched by their specific section in that course.
    
    # 1. Get student's enrollments with sections
    enrollments = db.execute(
        select(enrollment_association.c.course_id, enrollment_association.c.section)
        .where(enrollment_association.c.user_id == current_user.id)
    ).fetchall()
    
    if not enrollments:
        return []
    
    # 2. Query schedules matching course_id AND section in a single query
    conditions = []
    for course_id, section in enrollments:
        conditions.append(
            (CourseSchedule.course_id == course_id) &
            ((CourseSchedule.section == section) | (CourseSchedule.section == None))
        )
    
    if not conditions:
        return []

    return db.query(CourseSchedule).options(
        joinedload(CourseSchedule.course),
        joinedload(CourseSchedule.lecturer)
    ).filter(or_(*conditions)).offset(skip).limit(limit).all()
