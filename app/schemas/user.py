from pydantic import BaseModel, EmailStr, HttpUrl
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
    
    # Extended Student Fields
    enrollment_year: Optional[int] = None
    program: Optional[str] = None
    academic_standing: Optional[str] = None
    device_id: Optional[str] = None
    biometric_status: Optional[bool] = False
    
    # Extended Teacher Fields
    title: Optional[str] = None
    bio: Optional[str] = None
    employment_type: Optional[str] = None
    office_location: Optional[str] = None
    office_hours: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    # Shared Fields
    phone_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    account_status: Optional[str] = "active"
    timezone: Optional[str] = "UTC"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    default_session_duration: Optional[int] = None
    default_session_radius: Optional[int] = None
    department_id: Optional[int] = None
    
    # Allow updates to extended fields
    enrollment_year: Optional[int] = None
    program: Optional[str] = None
    academic_standing: Optional[str] = None
    device_id: Optional[str] = None
    biometric_status: Optional[bool] = None
    
    title: Optional[str] = None
    bio: Optional[str] = None
    employment_type: Optional[str] = None
    office_location: Optional[str] = None
    office_hours: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    phone_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    account_status: Optional[str] = None
    timezone: Optional[str] = None

class UserOut(UserBase):
    id: int
    default_session_duration: int
    default_session_radius: int
    department_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

