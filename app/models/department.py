from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from ..db.session import Base

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    organization = relationship("Organization", backref="departments")
    users = relationship("User", back_populates="department")
    courses = relationship("Course", back_populates="department")
