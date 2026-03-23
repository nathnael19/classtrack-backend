from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List

from ....db.session import get_db
from ....models.user import User, UserRole
from ....models.course import Course
from ....models.class_session import ClassSession
from ....models.attendance import Attendance
from ....schemas.admin_analytics import AdminDashboardFull, AdminDashboardStats, AdminChartPoint, AdminCourseEngagement, AdminActivityLog, AdminSystemHealth
from .users import get_current_user

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

    # 3. Course Engagement (Top 5)
    engagement = db.query(
        Course.code,
        func.count(Attendance.id).label('students')
    ).join(ClassSession, ClassSession.course_id == Course.id)\
     .join(Attendance, Attendance.session_id == ClassSession.id)\
     .group_by(Course.code)\
     .order_by(func.count(Attendance.id).desc())\
     .limit(5).all()
    
    course_engagement = [AdminCourseEngagement(name=e.code, students=e.students) for e in engagement]
    
    # Fallback for course engagement if no attendance
    if not course_engagement:
        courses = db.query(Course).limit(5).all()
        course_engagement = [AdminCourseEngagement(name=c.code, students=0) for c in courses]

    # 4. Recent Activity (Placeholder logic)
    # Since we don't have an Activity model, we can use recently created users/courses
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(2).all()
    recent_courses = db.query(Course).order_by(Course.id.desc()).limit(2).all()
    
    recent_activity = []
    for u in recent_users:
        recent_activity.append(AdminActivityLog(
            id=u.id, 
            action="New identity node", 
            detail=f"User {u.name} integrated", 
            time="Recent", 
            icon="Users", 
            color="text-emerald-500", 
            bg="bg-emerald-500/10"
        ))
    for c in recent_courses:
        recent_activity.append(AdminActivityLog(
            id=100 + c.id, 
            action="Course expansion", 
            detail=f"Course {c.code} published", 
            time="Recent", 
            icon="BookOpen", 
            color="text-blue-500", 
            bg="bg-blue-500/10"
        ))

    return AdminDashboardFull(
        stats=AdminDashboardStats(
            total_users=total_users,
            total_courses=total_courses,
            live_sessions=live_sessions,
            security_alerts=0, # Placeholder
            user_growth_change=user_growth_change,
            course_growth_change="+0%", # Placeholder
            is_growth_positive=True
        ),
        user_growth=user_growth,
        course_engagement=course_engagement,
        recent_activity=recent_activity,
        system_health=AdminSystemHealth(
            api_cluster=98, 
            database=100, 
            storage_core=85
        )
    )
