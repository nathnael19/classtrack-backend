from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AdminDashboardStats(BaseModel):
    total_users: int
    total_courses: int
    live_sessions: int
    security_alerts: int
    user_growth_change: str
    course_growth_change: str
    is_growth_positive: bool

class AdminChartPoint(BaseModel):
    name: str
    users: int

class AdminCourseEngagement(BaseModel):
    name: str
    students: int

class AdminActivityLog(BaseModel):
    id: int
    action: str
    detail: str
    time: str
    icon: str
    color: str
    bg: str

class AdminSystemHealth(BaseModel):
    api_cluster: int
    database: int
    storage_core: int

class AdminDashboardFull(BaseModel):
    stats: AdminDashboardStats
    user_growth: List[AdminChartPoint]
    course_engagement: List[AdminCourseEngagement]
    recent_activity: List[AdminActivityLog]
    system_health: AdminSystemHealth
