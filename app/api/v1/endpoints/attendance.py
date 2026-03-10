from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import math

from ....db.session import get_db
from ....models.attendance import Attendance, AttendanceStatus
from ....models.class_session import ClassSession
from ....models.user import User, UserRole
from ....schemas.attendance import AttendanceMark, AttendanceOut
from ....schemas.class_session import ClassSessionOut
from ....schemas.course import CourseOut
from ....models.course import Course
from .users import get_current_user

router = APIRouter()

# Helper function for distance calculation
def get_distance(lat1, lon1, lat2, lon2):
    # Haversine formula
    R = 6371e3  # radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@router.get("/courses", response_model=List[CourseOut])
def get_student_courses(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Not authorized")
    return db.query(Course).all()

@router.get("/sessions", response_model=List[ClassSessionOut])
def get_upcoming_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(ClassSession).all()

@router.post("/mark", response_model=AttendanceOut)
def mark_attendance(
    attendance: AttendanceMark,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    session = db.query(ClassSession).filter(ClassSession.id == attendance.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 1. Validate QR Code
    if session.qr_code_content != attendance.qr_code_content:
        raise HTTPException(status_code=400, detail="Invalid QR Code")
    
    # 2. Validate Geofence
    distance = get_distance(attendance.latitude, attendance.longitude, session.latitude, session.longitude)
    if distance > session.geofence_radius:
        raise HTTPException(status_code=400, detail=f"Outside geofence area. Distance: {distance:.2f}m")
    
    # 3. Check if already marked
    existing = db.query(Attendance).filter(
        Attendance.student_id == current_user.id,
        Attendance.session_id == attendance.session_id
    ).first()
    if existing:
        return existing

    # 4. Determine Status
    status = AttendanceStatus.present
    
    new_attendance = Attendance(
        student_id=current_user.id,
        session_id=attendance.session_id,
        status=status,
        timestamp=datetime.utcnow()
    )
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)
    return new_attendance

@router.get("/history", response_model=List[AttendanceOut])
def get_attendance_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Attendance).filter(Attendance.student_id == current_user.id).all()
