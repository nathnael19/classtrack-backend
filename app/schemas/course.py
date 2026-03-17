from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CourseBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    term_id: Optional[int] = None
    department_id: Optional[int] = None
    credit_hours: Optional[int] = None
    is_active: bool = True

class CourseCreate(CourseBase):
    pass

class CourseOut(CourseBase):
    id: int
    lecturer_id: int
    student_count: int = 0

    class Config:
        from_attributes = True

class StudentEnroll(BaseModel):
    name: str
    student_id: str

class EnrollmentRequest(BaseModel):
    students: List[StudentEnroll]

class StudentActivityOut(BaseModel):
    id: int
    name: str
    student_id: str
    attendance_count: int
    total_sessions: int
    attendance_rate: float
    last_seen: Optional[datetime] = None
    status: str # 'Consistent', 'At Risk', 'Inactive'

class CourseDetailOut(CourseOut):
    students: List[StudentActivityOut]
    total_sessions: int
    average_attendance: float
