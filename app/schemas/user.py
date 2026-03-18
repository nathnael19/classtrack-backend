from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from ..models.user import UserRole

class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole
    student_id: Optional[str] = None
    profile_picture_url: Optional[str] = None
    department_id: Optional[int] = None
    last_active_at: Optional[datetime] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    default_session_duration: Optional[int] = None
    default_session_radius: Optional[int] = None
    department_id: Optional[int] = None

class UserOut(UserBase):
    id: int
    default_session_duration: int
    default_session_radius: int
    department_name: Optional[str] = None

    class Config:
        from_attributes = True
