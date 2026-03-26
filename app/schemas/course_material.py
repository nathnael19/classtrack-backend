from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CourseMaterialBase(BaseModel):
    title: str
    description: Optional[str] = None

class CourseMaterialCreate(CourseMaterialBase):
    course_id: int

class CourseMaterialUpdate(CourseMaterialBase):
    pass

class CourseMaterialOut(CourseMaterialBase):
    id: int
    file_path: str
    original_filename: Optional[str]
    file_type: str
    file_size: int
    course_id: int
    uploader_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
