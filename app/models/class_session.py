from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from ..db.session import Base

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

    course = relationship("Course", back_populates="sessions")
    attendances = relationship("Attendance", back_populates="session")
