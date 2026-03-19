from pydantic import BaseModel
from datetime import time
from typing import Optional

class CourseScheduleBase(BaseModel):
    section: str
    day_of_week: int # 0=Monday, 6=Sunday
    start_time: time
    end_time: time
    room: str

class CourseScheduleCreate(CourseScheduleBase):
    pass

class CourseScheduleOut(CourseScheduleBase):
    id: int
    course_id: int
    lecturer_id: int
    course_name: str
    lecturer_name: str

    class Config:
        from_attributes = True
