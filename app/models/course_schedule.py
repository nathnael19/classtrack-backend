from sqlalchemy import Column, Integer, String, ForeignKey, Time
from sqlalchemy.orm import relationship
from ..db.session import Base

class CourseSchedule(Base):
    __tablename__ = "course_schedules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    lecturer_id = Column(Integer, ForeignKey("users.id"))
    section = Column(String)
    day_of_week = Column(Integer) # 0=Monday, 6=Sunday
    start_time = Column(Time)
    end_time = Column(Time)
    room = Column(String)

    course = relationship("Course", back_populates="schedules")
    lecturer = relationship("User", back_populates="schedules")

    @property
    def course_name(self) -> str:
        return self.course.name if self.course else "Unknown Course"

    @property
    def lecturer_name(self) -> str:
        return self.lecturer.name if self.lecturer else "Unknown Lecturer"
