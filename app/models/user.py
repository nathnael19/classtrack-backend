from sqlalchemy import Column, Integer, String, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import enum
from ..db.session import Base

class UserRole(enum.Enum):
    student = "student"
    lecturer = "lecturer"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.student)
    student_id = Column(String, unique=True, nullable=True)
    default_session_duration = Column(Integer, default=60)
    default_session_radius = Column(Integer, default=50)
    is_verified = Column(Boolean, default=False)
    fcm_token = Column(String, nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    organization = relationship("Organization", back_populates="users")
    lecturer_courses = relationship("Course", back_populates="lecturer", foreign_keys="[Course.lecturer_id]")
    attendances = relationship("Attendance", back_populates="student")
