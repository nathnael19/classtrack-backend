from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DeviceFingerprintBase(BaseModel):
    device_id: str
    device_model: Optional[str] = None

class DeviceFingerprintCreate(DeviceFingerprintBase):
    student_id: int

class DeviceFingerprintOut(DeviceFingerprintBase):
    id: int
    student_id: int
    last_used_at: datetime
    is_trusted: bool

    class Config:
        from_attributes = True
