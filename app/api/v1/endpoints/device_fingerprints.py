from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.device_fingerprint import DeviceFingerprint
from ....models.user import User
from ....schemas.device_fingerprint import DeviceFingerprintCreate, DeviceFingerprintOut
from .users import get_current_user

router = APIRouter()

@router.get("/me", response_model=List[DeviceFingerprintOut])
def get_my_devices(
    skip: int = 0,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(DeviceFingerprint).filter(DeviceFingerprint.student_id == current_user.id).offset(skip).limit(limit).all()

@router.post("/", response_model=DeviceFingerprintOut, status_code=status.HTTP_201_CREATED)
def register_device(
    device_in: DeviceFingerprintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if device_in.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only register devices for yourself")
        
    db_device = DeviceFingerprint(**device_in.dict())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device
