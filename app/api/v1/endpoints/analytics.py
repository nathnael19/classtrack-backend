from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime, timedelta

from ....db.session import get_db
from ....models.attendance import Attendance
from ....models.room import Room
from ....models.class_session import ClassSession
from ....models.course import Course
from ....models.user import User
from ....schemas.analytics import DashboardStats, ChartDataPoint, CourseDistribution, RecentSessionSummary, EngagementPoint, PeakPeriod
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
        
        # Previous period comparison
        prev_start = day_start - timedelta(days=7)
        prev_end = day_end - timedelta(days=7)
        
        def get_rate(start, end):
            sessions = db.query(ClassSession).join(Course).filter(
                Course.lecturer_id == current_user.id,
                ClassSession.start_time >= start,
                ClassSession.start_time < end
            ).count()
            if sessions == 0: return 0
            present = db.query(Attendance).join(ClassSession).join(Course).filter(
                Course.lecturer_id == current_user.id,
                ClassSession.start_time >= start,
                ClassSession.start_time < end
            ).count()
            return (present / (sessions * 100) * 100)
            
        trend.append({
            "name": day_start.strftime("%a"),
            "rate": round(get_rate(day_start, day_end), 1),
            "rate2": round(get_rate(prev_start, prev_end), 1)
        })
    
    return trend

@router.get("/engagement-profile", response_model=List[EngagementPoint])
def get_engagement_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mocked engagement profile logic based on status distribution.
    In a real app, you'd check arrival time vs session start time.
    """
    return [
        {"name": "On Time", "value": 82, "color": "#10b981"},
        {"name": "Late", "value": 12, "color": "#f59e0b"},
        {"name": "Absent", "value": 6, "color": "#ef4444"},
    ]

@router.get("/peak-periods", response_model=List[PeakPeriod])
def get_peak_periods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Simulated peak arrival periods.
    """
    return [
        {"time": "08:00 AM", "volume": 92, "icon": "Clock", "color": "from-emerald-400 to-emerald-600"},
        {"time": "10:00 AM", "volume": 85, "icon": "Clock", "color": "from-blue-400 to-blue-600"},
        {"time": "12:00 PM", "volume": 60, "icon": "Clock", "color": "from-amber-400 to-amber-600"},
        {"time": "02:00 PM", "volume": 78, "icon": "Clock", "color": "from-indigo-400 to-indigo-600"},
        {"time": "04:00 PM", "volume": 42, "icon": "Clock", "color": "from-rose-400 to-rose-600"},
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
    current_user: User = Depends(get_current_user),
    course_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None)
):
    query = db.query(ClassSession).join(Course).filter(
        Course.lecturer_id == current_user.id
    )

    if course_id:
        query = query.filter(ClassSession.course_id == course_id)
    
    if q:
        query = query.filter(
            or_(
                Course.name.ilike(f"%{q}%"),
                Course.code.ilike(f"%{q}%"),
                ClassSession.room.ilike(f"%{q}%")
            )
        )

    sessions = query.order_by(ClassSession.start_time.desc()).all()
    
    result = []
    for s in sessions:
        present_count = db.query(Attendance).filter(Attendance.session_id == s.id).count()
        # Fallback to capacity from Room model if available, else 100
        room_obj = db.query(Room).filter(Room.name == s.room).first()
        total_count = room_obj.capacity if (room_obj and room_obj.capacity) else 100
        
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

@router.get("/session-context")
def get_session_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns strategic data for the session creation page, 
    including the last session's performance.
    """
    last_session = db.query(ClassSession).join(Course).filter(
        Course.lecturer_id == current_user.id
    ).order_by(ClassSession.start_time.desc()).first()
    
    if not last_session:
        return {
            "last_course": "N/A",
            "success_rate": "0%",
            "total_scans": 0,
            "outliers": 0
        }
    
    present_count = db.query(Attendance).filter(Attendance.session_id == last_session.id).count()
    total_count = 100 # Mock capacity
    rate = f"{(present_count / total_count * 100):.1f}%" if total_count > 0 else "0%"
    
    return {
        "last_course": last_session.course.code,
        "success_rate": rate,
        "total_scans": present_count,
        "outliers": round(present_count * 0.05) # Mock outliers as 5% of scans
    }
