from pydantic import BaseModel
from datetime import datetime

class ClassSessionBase(BaseModel):
    room: str
    start_time: datetime
    end_time: datetime
    qr_code_content: str
    latitude: float
    longitude: float
    geofence_radius: float

class ClassSessionOut(ClassSessionBase):
    id: int
    course_id: int

    class Config:
        from_attributes = True
