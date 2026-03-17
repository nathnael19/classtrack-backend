from pydantic import BaseModel
from typing import Optional
from ..models.room import RoomType, RoomStatus

class RoomBase(BaseModel):
    name: str
    building: Optional[str] = None
    capacity: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius: Optional[float] = 100.0
    type: RoomType = RoomType.lecture_hall
    status: RoomStatus = RoomStatus.active

class RoomCreate(RoomBase):
    pass

class RoomOut(RoomBase):
    id: int

    class Config:
        from_attributes = True
