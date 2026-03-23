from sqlalchemy import Column, Integer, String, Enum, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from ..db.session import Base

class UserRole(enum.Enum):
    student = "student"
    lecturer = "lecturer"
    admin = "admin"

class UserState(enum.Enum):
    active = "active"
    suspended = "suspended"
    graduated = "graduated"
    on_leave = "on_leave"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.student)
    student_id = Column(String, unique=True, nullable=True)
    section = Column(String, nullable=True) # Default section for students
    
    # Extended Student Fields
    enrollment_year = Column(Integer, nullable=True)
    program = Column(String, nullable=True)
    academic_standing = Column(String, nullable=True)
    device_id = Column(String, nullable=True)
    biometric_status = Column(Boolean, default=False)
    
    # Extended Teacher Fields
    title = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)
    office_location = Column(String, nullable=True)
    office_hours = Column(String, nullable=True)
    website_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    
    # Shared Fields
    phone_number = Column(String, nullable=True)
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String, nullable=True)
    account_status = Column(String, default=UserState.active.value) # Use String enum for smooth DB mapping
    timezone = Column(String, nullable=True, default="UTC")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Legacy fields
    default_session_duration = Column(Integer, default=60)
    default_session_radius = Column(Integer, default=50)
    is_verified = Column(Boolean, default=False)
    fcm_token = Column(String, nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    profile_picture_url = Column(String, nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    last_active_at = Column(DateTime, nullable=True)

    # Password Setup Fields
    setup_password_token = Column(String, unique=True, index=True, nullable=True)
    setup_password_expires_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="users")
    department = relationship("Department", back_populates="users")
    lecturer_courses = relationship("Course", back_populates="lecturer", foreign_keys="[Course.lecturer_id]")
    attendances = relationship("Attendance", back_populates="student")
    schedules = relationship("CourseSchedule", back_populates="lecturer")

    @property
    def department_name(self):
        return self.department.name if self.department else "Not Assigned"

