from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import math
import hmac
import hashlib
import time

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
    
    # 1. Validate Rotating QR Token
    # The session's qr_code_content is used as a secret seed
    # Token rotates every 2 minutes (120 seconds)
    rotation_interval = 120
    timestamp = int(time.time())
    time_step = timestamp // rotation_interval
    
    def generate_token(step, secret):
        h = hmac.new(secret.encode(), str(step).encode(), hashlib.sha256)
        return h.hexdigest().upper()[:8]

    # Check current and previous step to allow for clock drift/network latency
    valid_tokens = [
        generate_token(time_step, session.qr_code_content),
        generate_token(time_step - 1, session.qr_code_content)
    ]
    
    if attendance.qr_code_content not in valid_tokens:
        raise HTTPException(status_code=400, detail="Invalid or Expired QR Code")
    
    distance = get_distance(attendance.latitude, attendance.longitude, session.latitude, session.longitude)
    if distance > session.geofence_radius:
        raise HTTPException(status_code=400, detail=f"Outside geofence area. Distance: {distance:.2f}m")
    
    # 3. Verify Enrollment
    if current_user not in session.course.students:
        raise HTTPException(
            status_code=403, 
            detail=f"Tactical Error: Identity not enrolled in module '{session.course.name}'. Enrollment is mandatory for attendance synchronization."
        )

    # 4. Check if already marked
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

@router.get("/session/{session_id}", response_model=List[AttendanceOut])
def get_session_attendance(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve all attendance records for a specific session.
    Only the lecturer of the course or an admin should ideally see this.
    """
    # 1. Verify session exists
    session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # 2. Verify ownership (lecturer)
    if session.course.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this session's attendance")
        
    records = db.query(Attendance).filter(Attendance.session_id == session_id).all()
    
    # Manually populate student details for the response
    for r in records:
        r.student_name = r.student.full_name
        r.student_code = r.student.student_id
        
    return records
