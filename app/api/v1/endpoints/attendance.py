from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import math
import hmac
import hashlib
import time

from ....db.session import get_db
from ....models.attendance import Attendance, AttendanceStatus, VerificationMethod
from ....models.class_session import ClassSession
from ....models.user import User, UserRole
from ....schemas.attendance import AttendanceMark, AttendanceOut, AttendanceSummary, ManualAttendanceMark
from ....schemas.class_session import ClassSessionOut
from ....schemas.course import CourseOut
from ....models.course import Course
from .users import get_current_user
from sqlalchemy import select
from ....models.enrollment import enrollment_association
from ....core.limiter import limiter
from ....services.websocket_manager import manager

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
@limiter.limit("5/minute")
async def mark_attendance(
    request: Request,
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
    
    def generate_token(step: int, secret: str) -> str:
        h = hmac.new(secret.encode(), str(step).encode(), hashlib.sha256)
        hex_digest = h.hexdigest().upper()
        return hex_digest[:8]

    # Check current and previous step to allow for clock drift/network latency
    valid_tokens = [
        generate_token(time_step, session.qr_code_content),
        generate_token(time_step - 1, session.qr_code_content)
    ]
    
    if attendance.qr_code_content not in valid_tokens:
        raise HTTPException(status_code=400, detail="Invalid or Expired QR Code")
    
    distance = get_distance(attendance.latitude, attendance.longitude, session.latitude, session.longitude)
    # Add a 10m buffer to the geofence radius to account for minor GPS floating/jitter
    if distance > (session.geofence_radius + 10):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Outside geofence area. Distance: {distance:.1f}m, Radius: {session.geofence_radius}m. "
                f"Session coords: ({session.latitude:.6f}, {session.longitude:.6f}). "
                f"Your coords: ({attendance.latitude:.6f}, {attendance.longitude:.6f})."
            )
        )
    
    # 3. Verify Enrollment
    if current_user not in session.course.students:
        raise HTTPException(
            status_code=403, 
            detail=f"Tactical Error: Identity not enrolled in module '{session.course.name}'. Enrollment is mandatory for attendance synchronization."
        )

    # 4. Determine Status (Always Present when scanned as requested)
    status = AttendanceStatus.present
    
    # 5. Check if already marked
    existing = db.query(Attendance).filter(
        Attendance.student_id == current_user.id,
        Attendance.session_id == attendance.session_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Attendance already recorded for this session.")

    # Fetch section for this student in this course
    enrollment = db.execute(
        select(enrollment_association.c.section)
        .where(
            (enrollment_association.c.user_id == current_user.id) &
            (enrollment_association.c.course_id == session.course_id)
        )
    ).first()
    section = enrollment.section if enrollment else None

    new_attendance = Attendance(
        student_id=current_user.id,
        session_id=attendance.session_id,
        status=status,
        timestamp=datetime.utcnow(),
        location_lat=attendance.latitude,
        location_lng=attendance.longitude,
        device_fingerprint=attendance.device_fingerprint,
        verification_method=attendance.verification_method,
    )
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)

    # Broadcast update via WebSocket
    await manager.broadcast_to_session(attendance.session_id, {
        "type": "attendance_recorded",
        "student": {
            "id": current_user.id,
            "name": current_user.name,
            "student_id": current_user.student_id,
            "status": status.value,
            "timestamp": new_attendance.timestamp.isoformat(),
            "attendance_id": new_attendance.id,
            "section": section
        }
    })

    return new_attendance

@router.post("/manual", response_model=AttendanceOut)
async def manual_mark_attendance(
    attendance_in: ManualAttendanceMark,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.lecturer:
        raise HTTPException(status_code=403, detail="Only lecturers can mark attendance manually")
    
    session = db.query(ClassSession).filter(ClassSession.id == attendance_in.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify lecturer is authorized for this course
    course = session.course
    is_authorized = (course.lecturer_id == current_user.id) or (current_user in course.lecturers)
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized to mark attendance for this course")
    
    # Check if student exists and is enrolled
    student = db.query(User).filter(User.id == attendance_in.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    if student not in course.students:
        raise HTTPException(status_code=400, detail="Student is not enrolled in this course")

    # Check if already marked
    existing = db.query(Attendance).filter(
        Attendance.student_id == student.id,
        Attendance.session_id == session.id
    ).first()
    
    if existing:
        existing.status = attendance_in.status
        existing.verification_method = VerificationMethod.manual_override
        existing.timestamp = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    # Fetch section
    enrollment = db.execute(
        select(enrollment_association.c.section)
        .where(
            (enrollment_association.c.user_id == student.id) &
            (enrollment_association.c.course_id == session.course_id)
        )
    ).first()
    section = enrollment.section if enrollment else None

    new_attendance = Attendance(
        student_id=student.id,
        session_id=session.id,
        status=attendance_in.status,
        verification_method=VerificationMethod.manual_override,
        timestamp=datetime.utcnow()
    )
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)

    # Broadcast update via WebSocket
    # We use a background task to not block the response
    import asyncio
    asyncio.create_task(manager.broadcast_to_session(session.id, {
        "type": "attendance_recorded",
        "student": {
            "id": student.id,
            "name": student.name,
            "student_id": student.student_id,
            "status": new_attendance.status.value,
            "timestamp": new_attendance.timestamp.isoformat(),
            "attendance_id": new_attendance.id,
            "section": section
        }
    }))

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
    
    # Add sections to records
    # Fetch sections for all students in this course
    sections_map = {
        row.user_id: row.section for row in db.execute(
            select(enrollment_association.c.user_id, enrollment_association.c.section)
            .where(enrollment_association.c.course_id == session.course_id)
        ).fetchall()
    }
    
    for record in records:
        record.section = sections_map.get(record.student_id)
        
    return records

from datetime import datetime, timedelta
# ... (existing imports)

@router.get("/summary", response_model=AttendanceSummary)
def get_attendance_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Only students have attendance summaries")
        
    attendances = db.query(Attendance).filter(Attendance.student_id == current_user.id).all()
    
    total = len(attendances)
    present = len([a for a in attendances if a.status == AttendanceStatus.present])
    absent_total = len([a for a in attendances if a.status == AttendanceStatus.absent])
    
    now = datetime.utcnow()
    absent_this_month = len([
        a for a in attendances 
        if a.status == AttendanceStatus.absent 
        and a.timestamp.month == now.month 
        and a.timestamp.year == now.year
    ])
    
    # Bug fix: If total is 0, percent is 0.0
    percent = (present / total) if total > 0 else 0.0
    
    # Weekly stats for the last 5 weeks
    weekly_stats = []
    # Find the Monday of the current week (local 00:00)
    current_monday = now - timedelta(days=now.weekday())
    current_monday = current_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for i in range(4, -1, -1):
        week_start = current_monday - timedelta(weeks=i)
        week_end = week_start + timedelta(days=7)
        
        week_attendances = [
            a for a in attendances 
            if week_start <= a.timestamp < week_end
        ]
        
        if not week_attendances:
            weekly_stats.append(0.0)
        else:
            w_total = len(week_attendances)
            w_present = len([a for a in week_attendances if a.status == AttendanceStatus.present])
            weekly_stats.append(w_present / w_total)

    # Standing logic
    if total == 0:
        standing = "No Records"
    elif percent >= 0.9:
        standing = "Excellent Standing"
    elif percent >= 0.75:
        standing = "Great Standing"
    elif percent >= 0.6:
        standing = "Good Standing"
    else:
        standing = "Low Attendance"
        
    # Message logic
    if total == 0:
        message = "No classes recorded yet."
    elif absent_this_month == 0:
        message = "Perfect attendance this month!"
    elif absent_this_month == 1:
        message = "You missed only 1 class this month."
    else:
        message = f"You missed {absent_this_month} classes this month."
        
    return {
        "percent": percent,
        "status": standing,
        "message": message,
        "total_classes": total,
        "present_count": present,
        "absent_count": absent_total,
        "weekly_stats": weekly_stats
    }
