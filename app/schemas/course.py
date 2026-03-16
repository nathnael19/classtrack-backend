from pydantic import BaseModel

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
