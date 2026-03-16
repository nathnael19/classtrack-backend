from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from ..models.attendance import AttendanceStatus

class AttendanceMark(BaseModel):
    session_id: int
    qr_code_content: str
    latitude: float
    longitude: float

class AttendanceOut(BaseModel):
    id: int
    session_id: int
    student_id: int
    student_name: Optional[str] = None
    student_code: Optional[str] = None
    timestamp: datetime
    status: AttendanceStatus

    class Config:
        from_attributes = True
