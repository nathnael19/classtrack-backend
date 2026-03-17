from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from ..db.session import Base
from .enrollment import enrollment_association

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    code = Column(String, unique=True, index=True)
    lecturer_id = Column(Integer, ForeignKey("users.id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    description = Column(Text, nullable=True)
    term_id = Column(Integer, ForeignKey("terms.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    credit_hours = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

    organization = relationship("Organization", back_populates="courses")
    term = relationship("Term", back_populates="courses")
    department = relationship("Department", back_populates="courses")
    lecturer = relationship("User", back_populates="lecturer_courses")
    sessions = relationship("ClassSession", back_populates="course")
    students = relationship("User", secondary=enrollment_association, backref="enrolled_courses")

    @hybrid_property
    def student_count(self) -> int:
        return len(self.students)
