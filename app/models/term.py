from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from ..db.session import Base

class Term(Base):
    __tablename__ = "terms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # e.g. Fall 2026
    start_date = Column(Date)
    end_date = Column(Date)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)

    organization = relationship("Organization", backref="terms")
    courses = relationship("Course", back_populates="term")
