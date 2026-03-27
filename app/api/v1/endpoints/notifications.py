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
    """Admins and Lecturers can create notifications. Lecturers can only notify their students."""
    if current_user.role == UserRole.admin:
        pass # Admins can notify anyone
    elif current_user.role == UserRole.lecturer:
        # Verify the target user is a student enrolled in one of this lecturer's courses
        from ....models.enrollment import enrollment_association
        from ....models.course import Course
        
        is_student_of_lecturer = db.query(enrollment_association).join(
            Course, Course.id == enrollment_association.c.course_id
        ).filter(
            enrollment_association.c.user_id == notif_in.user_id,
            Course.lecturer_id == current_user.id
        ).first()
        
        if not is_student_of_lecturer:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Lecturers can only notify students enrolled in their modules."
            )
    else:
        raise HTTPException(status_code=403, detail="Not authorized to create notifications")

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
