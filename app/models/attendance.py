from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
import datetime
from ..db.session import Base

class AttendanceStatus(enum.Enum):
    present = "present"
    late = "late"
    absent = "absent"

class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("class_sessions.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(Enum(AttendanceStatus))

    student = relationship("User", back_populates="attendances")
    session = relationship("ClassSession", back_populates="attendances")
