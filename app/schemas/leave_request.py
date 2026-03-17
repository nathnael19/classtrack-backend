from pydantic import BaseModel
from typing import Optional
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
