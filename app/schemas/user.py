from pydantic import BaseModel, EmailStr
from typing import Optional
from ..models.user import UserRole

class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: UserRole

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    default_session_duration: Optional[int] = None
    default_session_radius: Optional[int] = None

class UserOut(UserBase):
    id: int
    default_session_duration: int
    default_session_radius: int

    class Config:
        from_attributes = True
