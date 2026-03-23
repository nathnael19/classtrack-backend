from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from ..models.leave_request import LeaveRequestStatus

class LeaveRequestBase(BaseModel):
    session_id: int
    reason: str
    document_url: Optional[str] = None

class LeaveRequestCreate(LeaveRequestBase):
    pass

class LeaveRequestOut(LeaveRequestBase):
    id: int
    student_id: int
    status: LeaveRequestStatus
    reviewed_by: Optional[int] = None

    class Config:
        from_attributes = True


class LeaveRequestWithDetails(LeaveRequestOut):
    """Enriched output with student name, course name, session date."""
    student_name: Optional[str] = None
    course_name: Optional[str] = None
    session_start: Optional[datetime] = None
    session_room: Optional[str] = None

    class Config:
        from_attributes = True


class LeaveRequestReview(BaseModel):
    status: LeaveRequestStatus  # approved | rejected
