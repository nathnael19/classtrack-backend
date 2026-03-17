from sqlalchemy import Column, Integer, String, Float, Enum
import enum
from ..db.session import Base

class RoomType(enum.Enum):
    lecture_hall = "lecture_hall"
    lab = "lab"
    seminar_room = "seminar_room"

class RoomStatus(enum.Enum):
    active = "active"
    under_maintenance = "under_maintenance"

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    building = Column(String, nullable=True)
    capacity = Column(Integer, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    geofence_radius = Column(Float, default=100.0) # in meters
    type = Column(Enum(RoomType), default=RoomType.lecture_hall)
    status = Column(Enum(RoomStatus), default=RoomStatus.active)
