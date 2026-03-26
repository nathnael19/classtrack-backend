from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db.session import Base

class CourseMaterial(Base):
    __tablename__ = "course_materials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    file_path = Column(String) # Relative to static/uploads
    original_filename = Column(String, nullable=True) # E.g., 'lecture_01.pdf'
    file_type = Column(String) # e.g., 'pdf', 'docx', 'image/png'
    file_size = Column(Integer) # in bytes
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"))
    uploader_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    course = relationship("Course", backref="materials")
    uploader = relationship("User", backref="uploaded_materials")
