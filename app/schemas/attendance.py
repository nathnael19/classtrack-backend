from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from ..models.attendance import AttendanceStatus, VerificationMethod

class AttendanceMark(BaseModel):
    session_id: int
    qr_code_content: str
    latitude: float
    longitude: float
    device_fingerprint: Optional[str] = None
    verification_method: VerificationMethod = VerificationMethod.qr_scan

class ManualAttendanceMark(BaseModel):
    session_id: int
    student_id: int
    status: AttendanceStatus = AttendanceStatus.present
    note: Optional[str] = None

class AttendanceOut(BaseModel):
    id: int
    session_id: int
    student_id: int
    student_name: Optional[str] = None
    student_code: Optional[str] = None
    timestamp: datetime
    status: AttendanceStatus
    course_name: Optional[str] = None
    session_topic: Optional[str] = None
    room: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    device_fingerprint: Optional[str] = None
    verification_method: VerificationMethod = VerificationMethod.qr_scan

    class Config:
        from_attributes = True

class AttendanceSummary(BaseModel):
    percent: float
    status: str
    message: str
    total_classes: int
    present_count: int
    absent_count: int
    weekly_stats: List[float] = [] # Last 5 weeks percentages
