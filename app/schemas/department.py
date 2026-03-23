from pydantic import BaseModel
from typing import Optional

class DepartmentBase(BaseModel):
    name: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentOut(DepartmentBase):
    id: int
    organization_id: Optional[int] = None
    user_count: int = 0
    course_count: int = 0

    class Config:
        from_attributes = True
