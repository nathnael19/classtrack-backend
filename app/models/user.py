from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship
import enum
from ..db.session import Base

class UserRole(enum.Enum):
    student = "student"
    lecturer = "lecturer"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole))
    default_session_duration = Column(Integer, default=60)
    default_session_radius = Column(Integer, default=50)

    lectured_courses = relationship("Course", back_populates="lecturer")
    attendances = relationship("Attendance", back_populates="student")
