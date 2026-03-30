from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, Float, String, UniqueConstraint
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
    __table_args__ = (
        UniqueConstraint("student_id", "session_id", name="uq_attendances_student_session"),
    )

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

    @property
    def student_name(self):
        return self.student.name if self.student else None

    @property
    def student_code(self):
        return self.student.student_id if self.student else None

    @property
    def course_name(self):
        return self.session.course.name if self.session and self.session.course else "Unknown Course"

    @property
    def session_topic(self):
        return self.session.topic if self.session else "Unknown Topic"

    @property
    def room(self):
        return self.session.room if self.session else "N/A"
