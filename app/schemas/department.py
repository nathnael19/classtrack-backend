from pydantic import BaseModel
from typing import Optional

class DepartmentBase(BaseModel):
    name: str
    head: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    organization_id: Optional[int] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    head: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    organization_id: Optional[int] = None

class DepartmentOut(DepartmentBase):
    id: int
    organization_id: Optional[int] = None
    user_count: int = 0
    course_count: int = 0

    class Config:
        from_attributes = True
