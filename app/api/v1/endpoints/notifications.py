from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.notification import Notification
from ....models.user import User, UserRole
from ....schemas.notification import NotificationCreate, NotificationOut
from .users import get_current_user

router = APIRouter()


@router.get("/", response_model=List[NotificationOut])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()


@router.post("/", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
def create_notification_via_api(
    notif_in: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Only admins can create notifications via API. Use backend service for automated notifications."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can create notifications via API")
    db_notif = Notification(**notif_in.dict())
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)
    return db_notif

@router.patch("/{notif_id}/read", response_model=NotificationOut)
def mark_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if not notif or notif.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif
