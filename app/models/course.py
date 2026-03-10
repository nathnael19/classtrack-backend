from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from ..db.session import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    code = Column(String, unique=True, index=True)
    lecturer_id = Column(Integer, ForeignKey("users.id"))

    lecturer = relationship("User", back_populates="lectured_courses")
    sessions = relationship("ClassSession", back_populates="course")
