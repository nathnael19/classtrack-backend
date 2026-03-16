from pydantic import BaseModel
from typing import List

class CourseBase(BaseModel):
    name: str
    code: str

class CourseCreate(CourseBase):
    pass

class CourseOut(CourseBase):
    id: int
    lecturer_id: int

    class Config:
        from_attributes = True

class StudentEnroll(BaseModel):
    name: str
    student_id: str

class EnrollmentRequest(BaseModel):
    students: List[StudentEnroll]
