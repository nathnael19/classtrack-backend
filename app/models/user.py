from sqlalchemy import Column, Integer, String, Enum, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
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
    profile_picture_url = Column(String, nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    last_active_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="users")
    department = relationship("Department", back_populates="users")
    lecturer_courses = relationship("Course", back_populates="lecturer", foreign_keys="[Course.lecturer_id]")
    attendances = relationship("Attendance", back_populates="student")

    @property
    def department_name(self):
        return self.department.name if self.department else "Not Assigned"
