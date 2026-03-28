import resend
from sqlalchemy.orm import Session
from datetime import datetime
from .core.celery_app import celery_app
from .core.config import settings
from .db.session import SessionLocal
from .models.user import User, UserRole
from .models.course import Course
from .models.attendance import Attendance, AttendanceStatus
from .models.class_session import ClassSession, SessionStatus

# Configure Resend
resend.api_key = settings.RESEND_API_KEY

@celery_app.task(name="app.tasks.analyze_attendance_nightly")
def analyze_attendance_nightly():
    """
    Nightly task to scan all student enrollments and flag those with low attendance.
    """
    db = SessionLocal()
    try:
        # 1. Get all active courses
        courses = db.query(Course).filter(Course.is_active == True).all()
        
        for course in courses:
            # 2. Get completed sessions for this course
            completed_sessions = db.query(ClassSession).filter(
                ClassSession.course_id == course.id,
                ClassSession.status == SessionStatus.completed
            ).all()
            
            total_sessions = len(completed_sessions)
            if total_sessions == 0:
                continue
                
            session_ids = [s.id for s in completed_sessions]
            
            # 3. Analyze each student in the course
            for student in course.students:
                # Count present or late as 'attended'
                attendance_count = db.query(Attendance).filter(
                    Attendance.student_id == student.id,
                    Attendance.session_id.in_(session_ids),
                    Attendance.status.in_([AttendanceStatus.present, AttendanceStatus.late])
                ).count()
                
                attendance_rate = (attendance_count / total_sessions)
                
                # Flag if below 75%
                if attendance_rate < 0.75:
                    send_attendance_warning_email.delay(
                        student.email,
                        student.name,
                        course.name,
                        attendance_rate * 100
                    )
    finally:
        db.close()

@celery_app.task(name="app.tasks.send_attendance_warning_email")
def send_attendance_warning_email(email: str, name: str, course_name: str, rate: float):
    """
    Sends a warning email to a student using Resend.
    """
    if not settings.RESEND_API_KEY:
        print(f"DEBUG: Skipping email to {email} - No Resend API Key.")
        return

    subject = f"Attendance Warning: {course_name}"
    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px; background-color: #fcfcfc;">
        <h2 style="color: #6366f1; border-bottom: 2px solid #6366f1; padding-bottom: 10px;">ClassTrack Attendance Alert</h2>
        <p>Hello <strong>{name}</strong>,</p>
        <p>Our records show that your current attendance in <strong>{course_name}</strong> has fallen to <span style="color: #ef4444; font-size: 1.2em; font-weight: bold;">{rate:.1f}%</span>.</p>
        <p style="background-color: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; color: #b91c1c; font-weight: bold;">
            Note: A minimum of 75% attendance is required to remain in good standing for this module.
        </p>
        <p>Consistent attendance is vital for tactical academic success. Please ensure you attend upcoming sessions to improve your synchronization with the course material.</p>
        <p>If you believe this is a technical error, please contact your module lecturer immediately.</p>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="font-size: 11px; color: #94a3b8; text-align: center; text-transform: uppercase; letter-spacing: 1px;">
            Sent by ClassTrack Automation Engine • Secure Identity Node
        </p>
    </div>
    """
    
    try:
        resend.Emails.send({{
            "from": "ClassTrack <onboarding@resend.dev>", # Using Resend sandbox sender for safety
            "to": [email],
            "subject": subject,
            "html": html_content
        }})
        print(f"DEBUG: Successfully sent attendance warning to {email}")
    except Exception as e:
        print(f"ERROR: Failed to send email to {email}: {str(e)}")
