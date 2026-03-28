from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List
import os

from ....db.session import get_db
from ....models.user import User, UserRole
from ....models.course import Course
from ....models.class_session import ClassSession
from ....models.attendance import Attendance
from ....schemas.admin_analytics import AdminDashboardFull, AdminDashboardStats, AdminChartPoint, AdminCourseEngagement, AdminActivityLog, AdminSystemHealth
from .users import get_current_user
from ....core.config import settings

router = APIRouter()

@router.get("/dashboard", response_model=AdminDashboardFull)
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    # 1. Basic Stats
    total_users = db.query(User).count()
    total_courses = db.query(Course).count()
    
    now = datetime.utcnow()
    live_sessions = db.query(ClassSession).filter(ClassSession.end_time > now).count()
    
    # Growth Calculation (last 30 days vs previous 30 days)
    last_30_days = now - timedelta(days=30)
    prev_30_days = now - timedelta(days=60)
    
    current_users = db.query(User).filter(User.created_at >= last_30_days).count()
    prev_users = db.query(User).filter(User.created_at >= prev_30_days, User.created_at < last_30_days).count()
    
    if prev_users > 0:
        growth = ((current_users - prev_users) / prev_users) * 100
        user_growth_change = f"{'+' if growth >= 0 else ''}{growth:.1f}%"
    else:
        user_growth_change = "+100%" if current_users > 0 else "0%"

    # 2. User Growth Chart (last 4 weeks)
    user_growth = []
    for i in range(3, -1, -1):
        week_end = now - timedelta(weeks=i)
        week_start = week_end - timedelta(weeks=1)
        count = db.query(User).filter(User.created_at < week_end).count()
        user_growth.append(AdminChartPoint(name=f"Week {4-i}", users=count))

    # 3. Course Engagement (Top 5 by attendance volume)
    engagement = db.query(
        Course.code,
        func.count(Attendance.id).label('students')
    ).join(ClassSession, ClassSession.course_id == Course.id)\
     .join(Attendance, Attendance.session_id == ClassSession.id)\
     .group_by(Course.code)\
     .order_by(func.count(Attendance.id).desc())\
     .limit(5).all()
    
    course_engagement = [AdminCourseEngagement(name=e.code, students=e.students) for e in engagement]
    
    if not course_engagement:
        courses = db.query(Course).limit(5).all()
        course_engagement = [AdminCourseEngagement(name=c.code, students=0) for c in courses]

    # 4. Real Activity Feed — most recent users, courses, and sessions
    recent_activity = []

    recent_users = db.query(User).order_by(User.created_at.desc()).limit(2).all()
    for u in recent_users:
        time_str = u.created_at.strftime("%b %d, %H:%M") if u.created_at else "Unknown"
        recent_activity.append(AdminActivityLog(
            id=u.id,
            action="New user registered",
            detail=f"{u.name} joined as {u.role.value}",
            time=time_str,
            icon="Users",
            color="text-emerald-500",
            bg="bg-emerald-500/10"
        ))

    recent_courses = db.query(Course).order_by(Course.id.desc()).limit(2).all()
    for c in recent_courses:
        recent_activity.append(AdminActivityLog(
            id=1000 + c.id,
            action="Course created",
            detail=f"{c.code} — {c.name}",
            time="Recent",
            icon="BookOpen",
            color="text-blue-500",
            bg="bg-blue-500/10"
        ))

    recent_sessions = db.query(ClassSession).order_by(ClassSession.id.desc()).limit(2).all()
    for s in recent_sessions:
        time_str = s.start_time.strftime("%b %d, %H:%M") if s.start_time else "Unknown"
        recent_activity.append(AdminActivityLog(
            id=2000 + s.id,
            action="Attendance session",
            detail=f"Room {s.room} — {s.status if hasattr(s, 'status') else 'completed'}",
            time=time_str,
            icon="Activity",
            color="text-indigo-500",
            bg="bg-indigo-500/10"
        ))

    # Sort by ID descending as a rough recency proxy
    recent_activity.sort(key=lambda x: x.id, reverse=True)
    recent_activity = recent_activity[:6]

    # 5. Real System Health
    # DB: verify connectivity by running a fast count
    try:
        db.execute(db.get_bind().connect().execute.__func__.__code__ and __import__('sqlalchemy').text('SELECT 1'))
        db_health = 100
    except Exception:
        db_health = 0

    # Storage: percent of 10GB cap used (capped at 99%)
    try:
        uploads_dir = settings.UPLOADS_DIR
        if os.path.exists(uploads_dir):
            total_bytes = sum(
                os.path.getsize(os.path.join(root, f))
                for root, _, files in os.walk(uploads_dir)
                for f in files
            )
            storage_pct = min(int((total_bytes / (10 * 1024 ** 3)) * 100), 99)
        else:
            storage_pct = 0
    except Exception:
        storage_pct = 0

    # API health: measured as fraction of users who are active (proxy metric)
    active_users = db.query(User).filter(User.account_status == "active").count()
    api_health = min(int((active_users / max(total_users, 1)) * 100), 100) if total_users > 0 else 100

    return AdminDashboardFull(
        stats=AdminDashboardStats(
            total_users=total_users,
            total_courses=total_courses,
            live_sessions=live_sessions,
            security_alerts=0,
            user_growth_change=user_growth_change,
            course_growth_change="+0%",
            is_growth_positive=True
        ),
        user_growth=user_growth,
        course_engagement=course_engagement,
        recent_activity=recent_activity,
        system_health=AdminSystemHealth(
            api_cluster=api_health,
            database=db_health,
            storage_core=storage_pct
        )
    )
