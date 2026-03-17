from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, Float, String
from sqlalchemy.orm import relationship
import enum
import datetime
from ..db.session import Base

class AttendanceStatus(enum.Enum):
    present = "present"
    late = "late"
    absent = "absent"

class VerificationMethod(enum.Enum):
    qr_scan = "qr_scan"
    manual_override = "manual_override"
    beacon = "beacon"

class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("class_sessions.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(Enum(AttendanceStatus))
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    device_fingerprint = Column(String, nullable=True)
    verification_method = Column(Enum(VerificationMethod), default=VerificationMethod.qr_scan)

    student = relationship("User", back_populates="attendances")
    session = relationship("ClassSession", back_populates="attendances")
