from pydantic import BaseModel
from typing import Optional

class RoomBase(BaseModel):
    name: str
    building: Optional[str] = None
    capacity: Optional[int] = None

class RoomCreate(RoomBase):
    pass

class RoomOut(RoomBase):
    id: int

    class Config:
        from_attributes = True
