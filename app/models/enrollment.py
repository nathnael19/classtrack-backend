from sqlalchemy import Table, Column, Integer, ForeignKey
from ..db.session import Base

enrollment_association = Table(
    "enrollments",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("course_id", Integer, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True)
)
