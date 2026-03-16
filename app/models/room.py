from sqlalchemy import Column, Integer, String
from ..db.session import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    building = Column(String, nullable=True)
    capacity = Column(Integer, nullable=True)
