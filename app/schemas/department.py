from pydantic import BaseModel
from typing import Optional

class DepartmentBase(BaseModel):
    name: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentOut(DepartmentBase):
    id: int
    organization_id: Optional[int] = None

    class Config:
        from_attributes = True
