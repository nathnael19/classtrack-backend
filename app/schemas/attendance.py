from pydantic import BaseModel
from datetime import datetime
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
    timestamp: datetime
    status: AttendanceStatus

    class Config:
        from_attributes = True
