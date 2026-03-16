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

@router.put("/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int,
    room_in: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update facility specifications.
    """
    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Facility not found")
        
    for field, value in room_in.dict().items():
        setattr(db_room, field, value)
        
    db.commit()
    db.refresh(db_room)
    return db_room

@router.delete("/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Decommission a facility.
    """
    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Facility not found")
        
    db.delete(db_room)
    db.commit()
    return {"message": "Facility decommissioned successfully"}
