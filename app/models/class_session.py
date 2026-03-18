from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Enum, Text
from sqlalchemy.orm import relationship
import enum
from ..db.session import Base

class SessionStatus(enum.Enum):
    scheduled = "scheduled"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"

class ClassSession(Base):
    __tablename__ = "class_sessions"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    room = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    qr_code_content = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    geofence_radius = Column(Float, default=100.0) # in meters
    status = Column(Enum(SessionStatus), default=SessionStatus.scheduled)
    topic = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    course = relationship("Course", back_populates="sessions")
    attendances = relationship("Attendance", back_populates="session")

    @property
    def course_name(self) -> str:
        return self.course.name if self.course else "Unknown Course"

    @property
    def lecturer_name(self) -> str:
        return self.course.lecturer.full_name if self.course and self.course.lecturer else "N/A"
