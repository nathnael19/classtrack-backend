from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from ..db.session import Base

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    head = Column(String, nullable=True) # Head of Department
    location = Column(String, nullable=True) # Physical location
    description = Column(String, nullable=True) # Description/Vision
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    organization = relationship("Organization", backref="departments")
    users = relationship("User", back_populates="department")
    courses = relationship("Course", back_populates="department")

    @hybrid_property
    def user_count(self) -> int:
        return len(self.users)

    @hybrid_property
    def course_count(self) -> int:
        return len(self.courses)
