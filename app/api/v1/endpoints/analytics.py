from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
import csv
import io
from datetime import datetime, timedelta

from ....db.session import get_db
from ....models.attendance import Attendance, AttendanceStatus
from ....models.room import Room
from ....models.class_session import ClassSession
from ....models.course import Course
from ....models.user import User
from ....models.enrollment import enrollment_association
from ....schemas.analytics import DashboardStats, ChartDataPoint, CourseDistribution, RecentSessionSummary, EngagementPoint, PeakPeriod
from .users import get_current_user

router = APIRouter()


def _get_attendance_rate(db: Session, lecturer_id: int, start: datetime, end: datetime) -> float:
    """Computes attendance rate (%) for a lecturer in a time window.
    Uses enrolled student count per session as the denominator — NOT room capacity.
    """
    sessions = (
        db.query(ClassSession)
        .join(Course)
        .filter(
            Course.lecturer_id == lecturer_id,
            ClassSession.start_time >= start,
            ClassSession.start_time < end,
        )
        .all()
    )
    if not sessions:
        return 0.0

    total_potential = 0
    for session in sessions:
        enrolled_count = db.query(func.count()).select_from(enrollment_association).filter(
            enrollment_association.c.course_id == session.course_id
        ).scalar() or 0
        total_potential += enrolled_count

    if total_potential == 0:
        return 0.0

    present = (
        db.query(Attendance)
        .join(ClassSession)
        .join(Course)
        .filter(
            Course.lecturer_id == lecturer_id,
            ClassSession.start_time >= start,
            ClassSession.start_time < end,
        )
        .count()
    )
    return round((present / total_potential) * 100, 1)


def _get_session_total(db: Session, session: ClassSession) -> int:
    """Returns the number of enrolled students for a session's course.
    This is the correct denominator for attendance rate calculations.
    """
    enrolled = db.query(func.count()).select_from(enrollment_association).filter(
        enrollment_association.c.course_id == session.course_id
    ).scalar() or 0
    return enrolled if enrolled > 0 else 1

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
    
    last_week_start = today_start - timedelta(days=7)
    current_rate = _get_attendance_rate(db, current_user.id, last_week_start, today_end)
    prev_rate = _get_attendance_rate(db, current_user.id, last_week_start - timedelta(days=7), last_week_start)
    
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
        prev_start = day_start - timedelta(days=7)
        prev_end = day_end - timedelta(days=7)
            
        trend.append({
            "name": day_start.strftime("%a"),
            "rate": round(_get_attendance_rate(db, current_user.id, day_start, day_end), 1),
            "rate2": round(_get_attendance_rate(db, current_user.id, prev_start, prev_end), 1)
        })
    
    return trend

@router.get("/engagement-profile", response_model=List[EngagementPoint])
def get_engagement_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attendance_stats = db.query(
        Attendance.status,
        func.count(Attendance.id).label('count')
    ).join(ClassSession).join(Course).filter(
        Course.lecturer_id == current_user.id
    ).group_by(Attendance.status).all()
    
    total = sum(stat.count for stat in attendance_stats)
    if total == 0:
        return [
            {"name": "On Time", "value": 0, "color": "#10b981"},
            {"name": "Late", "value": 0, "color": "#f59e0b"},
            {"name": "Absent", "value": 0, "color": "#ef4444"},
        ]
        
    status_map = {stat.status: stat.count for stat in attendance_stats}
    
    return [
        {"name": "On Time", "value": round((status_map.get(AttendanceStatus.present, 0) / total) * 100), "color": "#10b981"},
        {"name": "Late", "value": round((status_map.get(AttendanceStatus.late, 0) / total) * 100), "color": "#f59e0b"},
        {"name": "Absent", "value": round((status_map.get(AttendanceStatus.absent, 0) / total) * 100), "color": "#ef4444"},
    ]

@router.get("/peak-periods", response_model=List[PeakPeriod])
def get_peak_periods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Group attendance by hour of the day
    peaks = db.query(
        func.extract('hour', Attendance.timestamp).label('hour'),
        func.count(Attendance.id).label('count')
    ).join(ClassSession).join(Course).filter(
        Course.lecturer_id == current_user.id
    ).group_by('hour').order_by('hour').all()
    
    max_count = max([p.count for p in peaks]) if peaks else 1
    
    result = []
    for p in peaks:
        hour = int(p.hour)
        am_pm = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0: display_hour = 12
        
        result.append({
            "time": f"{display_hour:02d}:00 {am_pm}",
            "volume": round((p.count / max_count) * 100),
            "icon": "Clock",
            "color": "from-blue-400 to-indigo-600"
        })
        
    return result if result else [
        {"time": "No Data", "volume": 0, "icon": "Clock", "color": "from-gray-400 to-gray-600"}
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
        total_count = _get_session_total(db, s)
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
        total_count = _get_session_total(db, s)
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
    total_count = _get_session_total(db, last_session)
    rate = f"{(present_count / total_count * 100):.1f}%" if total_count > 0 else "0%"
    
    return {
        "last_course": last_session.course.code,
        "success_rate": rate,
        "total_scans": present_count,
        "outliers": 0  # Reserved for future anomaly detection
    }
