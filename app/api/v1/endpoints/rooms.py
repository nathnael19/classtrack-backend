from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.room import Room
from ....schemas.room import RoomOut, RoomCreate
from .users import get_current_user
from ....models.user import User, UserRole

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
    Provision a new facility. Restricted to admins only.
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can create rooms.")
    db_room = Room(**room_in.dict())
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

@router.get("/{room_id}", response_model=RoomOut)
def get_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch details for a specific facility.
    """
    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Facility not found")
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
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can update rooms.")

    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Facility not found")

    # Explicitly update only allowed fields (prevents unintended attribute mutation).
    update_data = room_in.model_dump()
    allowed_fields = {"name", "building", "capacity", "latitude", "longitude", "geofence_radius", "type", "status"}
    for field, value in update_data.items():
        if field in allowed_fields:
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
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can delete rooms.")

    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Facility not found")
        
    db.delete(db_room)
    db.commit()
    return {"message": "Facility decommissioned successfully"}
