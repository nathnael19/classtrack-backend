from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class DashboardStats(BaseModel):
    total_courses: int
    active_sessions_today: int
    students_present_today: int
    avg_attendance_rate: float
    attendance_change: str
    is_positive: bool

class ChartDataPoint(BaseModel):
    name: str
    rate: float
    rate2: Optional[float] = None

class CourseDistribution(BaseModel):
    name: str
    students: int

class RecentSessionSummary(BaseModel):
    id: int
    course: str
    date: datetime
    present: int
    total: int
    rate: str
    classroom: Optional[str] = None
