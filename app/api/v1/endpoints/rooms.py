from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.room import Room
from ....schemas.room import RoomOut, RoomCreate
from .users import get_current_user
from ....models.user import User

router = APIRouter()

@router.get("/", response_model=List[RoomOut])
def get_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all available facilities for session allocation.
    """
    return db.query(Room).all()

@router.post("/", response_model=RoomOut)
def create_room(
    room_in: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Provision a new facility (Admin/Staff only logic could be added here).
    """
    db_room = Room(**room_in.dict())
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room
