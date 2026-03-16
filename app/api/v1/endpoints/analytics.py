from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta

from ....db.session import get_db
from ....models.attendance import Attendance
from ....models.class_session import ClassSession
from ....models.course import Course
from ....models.user import User
from ....schemas.analytics import DashboardStats, ChartDataPoint, CourseDistribution, RecentSessionSummary
from .users import get_current_user

router = APIRouter()

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Total courses for this lecturer
    total_courses = db.query(Course).filter(Course.lecturer_id == current_user.id).count()
    
    # Active sessions today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    active_sessions_today = db.query(ClassSession).join(Course).filter(
        Course.lecturer_id == current_user.id,
        ClassSession.start_time >= today_start,
        ClassSession.start_time < today_end
    ).count()
    
    # Students present today
    students_present_today = db.query(Attendance).join(ClassSession).join(Course).filter(
        Course.lecturer_id == current_user.id,
        ClassSession.start_time >= today_start,
        ClassSession.start_time < today_end
    ).count()
    
    # Calculate attendance rate and change
    last_week_start = today_start - timedelta(days=7)
    
    def get_rate(start, end):
        total = db.query(ClassSession).join(Course).filter(
            Course.lecturer_id == current_user.id,
            ClassSession.start_time >= start,
            ClassSession.start_time < end
        ).count()
        if total == 0: return 0
        present = db.query(Attendance).join(ClassSession).join(Course).filter(
            Course.lecturer_id == current_user.id,
            ClassSession.start_time >= start,
            ClassSession.start_time < end
        ).count()
        return (present / (total * 100)) * 100 # Assuming 100 capacity for rate calc
    
    current_rate = get_rate(last_week_start, today_end)
    prev_rate = get_rate(last_week_start - timedelta(days=7), last_week_start)
    
    diff = current_rate - prev_rate
    attendance_change = f"{'+' if diff >= 0 else ''}{diff:.1f}% this week"
    
    return {
        "total_courses": total_courses,
        "active_sessions_today": active_sessions_today,
        "students_present_today": students_present_today,
        "avg_attendance_rate": round(current_rate, 1),
        "attendance_change": attendance_change,
        "is_positive": diff >= 0
    }

@router.get("/weekly-trend", response_model=List[ChartDataPoint])
def get_weekly_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    trend = []
    for i in range(6, -1, -1):
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        sessions_count = db.query(ClassSession).join(Course).filter(
            Course.lecturer_id == current_user.id,
            ClassSession.start_time >= day_start,
            ClassSession.start_time < day_end
        ).count()
        
        present_count = db.query(Attendance).join(ClassSession).join(Course).filter(
            Course.lecturer_id == current_user.id,
            ClassSession.start_time >= day_start,
            ClassSession.start_time < day_end
        ).count()
        
        rate = (present_count / (sessions_count * 100) * 100) if sessions_count > 0 else 0
        trend.append({
            "name": day_start.strftime("%a"),
            "rate": round(rate, 1)
        })
    
    return trend

@router.get("/course-distribution", response_model=List[CourseDistribution])
def get_course_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Count sessions or students per course
    courses = db.query(Course).filter(Course.lecturer_id == current_user.id).all()
    result = []
    for course in courses:
        student_count = db.query(func.count(Attendance.id)).join(ClassSession).filter(
            ClassSession.course_id == course.id
        ).scalar() or 0
        
        result.append({
            "name": course.code,
            "students": student_count
        })
    return result

@router.get("/recent-sessions", response_model=List[RecentSessionSummary])
def get_recent_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sessions = db.query(ClassSession).join(Course).filter(
        Course.lecturer_id == current_user.id
    ).order_by(ClassSession.start_time.desc()).limit(5).all()
    
    result = []
    for s in sessions:
        present_count = db.query(Attendance).filter(Attendance.session_id == s.id).count()
        total_count = 100 # Mock capacity
        rate = f"{(present_count / total_count * 100):.0f}%" if total_count > 0 else "0%"
        
        result.append({
            "id": s.id,
            "course": s.course.name,
            "date": s.start_time,
            "present": present_count,
            "total": total_count,
            "rate": rate
        })
    return result

@router.get("/sessions-report", response_model=List[RecentSessionSummary])
def get_sessions_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sessions = db.query(ClassSession).join(Course).filter(
        Course.lecturer_id == current_user.id
    ).order_by(ClassSession.start_time.desc()).all()
    
    result = []
    for s in sessions:
        present_count = db.query(Attendance).filter(Attendance.session_id == s.id).count()
        total_count = 100 # Mock capacity
        rate = f"{(present_count / total_count * 100):.0f}%" if total_count > 0 else "0%"
        
        result.append({
            "id": s.id,
            "course": f"{s.course.code} - {s.course.name}",
            "date": s.start_time,
            "present": present_count,
            "total": total_count,
            "rate": rate,
            "classroom": s.room
        })
    return result
