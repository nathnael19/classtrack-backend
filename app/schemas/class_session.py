from pydantic import BaseModel, field_validator
from datetime import datetime, timezone
from typing import Optional

from ..models.class_session import SessionStatus


class ClassSessionCreate(BaseModel):
    """
    Request schema for creating/updating sessions.
    This includes the secret QR seed; it must never be returned to clients.
    """

    room: str
    start_time: datetime
    end_time: datetime
    qr_code_content: str
    latitude: float
    longitude: float
    geofence_radius: float
    status: SessionStatus = SessionStatus.scheduled
    topic: Optional[str] = None
    notes: Optional[str] = None
    section: Optional[str] = None
    course_id: int

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def ensure_utc(cls, v):
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        if isinstance(v, str) and "Z" not in v and "+" not in v:
            return f"{v}Z"
        return v


class ClassSessionOut(BaseModel):
    """
    Safe response schema for sessions.
    Intentionally excludes the secret `qr_code_content`.
    """

    room: str
    start_time: datetime
    end_time: datetime
    latitude: float
    longitude: float
    geofence_radius: float
    status: SessionStatus = SessionStatus.scheduled
    topic: Optional[str] = None
    notes: Optional[str] = None
    section: Optional[str] = None

    id: int
    course_id: int
    lecturer_id: Optional[int] = None
    course_name: Optional[str] = None
    lecturer_name: Optional[str] = None
    is_present: bool = False

    # Only populated by the lecturer live endpoint.
    active_qr_token: Optional[str] = None
    active_qr_token_expires_in_seconds: Optional[int] = None

    class Config:
        from_attributes = True
        extra = "ignore"


class SessionStudentOut(BaseModel):
    id: int
    name: str
    student_id: Optional[str] = None  # Student code (e.g. S-1001)
    status: Optional[str] = None  # present, late, absent, or None
    timestamp: Optional[datetime] = None
    section: Optional[str] = None

    class Config:
        from_attributes = True
