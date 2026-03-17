from sqlalchemy import Column, Integer, String, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
import enum
from ..db.session import Base

class LeaveRequestStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("class_sessions.id"))
    reason = Column(Text)
    document_url = Column(String, nullable=True)
    status = Column(Enum(LeaveRequestStatus), default=LeaveRequestStatus.pending)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    student = relationship("User", foreign_keys=[student_id], backref="leave_requests")
    session = relationship("ClassSession", backref="leave_requests")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
