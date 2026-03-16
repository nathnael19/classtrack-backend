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
    
    # Mock data for rates/changes as they require historical aggregation
    return {
        "total_courses": total_courses,
        "active_sessions_today": active_sessions_today,
        "students_present_today": students_present_today,
        "avg_attendance_rate": 89.5,  # Mock for now
        "attendance_change": "+2.4% this week",
        "is_positive": True
    }

@router.get("/weekly-trend", response_model=List[ChartDataPoint])
def get_weekly_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # This would aggregate attendance rate per day
    # For simplicity, returning mock data matched to frontend expected format
    return [
        {"name": "Mon", "rate": 75, "rate2": 80},
        {"name": "Tue", "rate": 85, "rate2": 82},
        {"name": "Wed", "rate": 90, "rate2": 85},
        {"name": "Thu", "rate": 82, "rate2": 83},
        {"name": "Fri", "rate": 95, "rate2": 89},
    ]

@router.get("/course-distribution", response_model=List[CourseDistribution])
def get_course_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Count sessions or students per course
    courses = db.query(Course).filter(Course.lecturer_id == current_user.id).all()
    result = []
    for course in courses:
        # Just a dummy count for now
        result.append({
            "name": course.code,
            "students": 100 + course.id * 10
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
