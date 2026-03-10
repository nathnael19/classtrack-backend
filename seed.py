from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.session import SessionLocal, engine
from app.db import base
from app.core import security
from app.models.user import User, UserRole
from app.models.course import Course
from app.models.class_session import ClassSession

def seed_db():
    db = SessionLocal()
    
    # 1. Clear existing data
    base.Base.metadata.drop_all(bind=engine)
    base.Base.metadata.create_all(bind=engine)

    # 2. Create Lecturer
    lecturer_password = security.get_password_hash("lecturer123")
    lecturer = User(
        name="Dr. Smith",
        email="smith@university.edu",
        hashed_password=lecturer_password,
        role=UserRole.lecturer
    )
    db.add(lecturer)
    db.commit()
    db.refresh(lecturer)

    # 3. Create Student
    student_password = security.get_password_hash("student123")
    student = User(
        name="John Doe",
        email="john@student.edu",
        hashed_password=student_password,
        role=UserRole.student
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    # 4. Create Course
    course = Course(
        name="Introduction to Computer Science",
        code="CS101",
        lecturer_id=lecturer.id
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    # 5. Create Class Session
    # Set session time to start now and end in 2 hours
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=2)
    
    session = ClassSession(
        course_id=course.id,
        room="Room 402",
        start_time=start_time,
        end_time=end_time,
        qr_code_content="CS101-SESSION-2026-03-11",
        latitude=9.032, # Example coordinates
        longitude=38.751,
        geofence_radius=500.0 # Large radius for testing
    )
    db.add(session)
    db.commit()
    
    print("Database seeded successfully!")
    print(f"Lecturer login: smith@university.edu / lecturer123")
    print(f"Student login: john@student.edu / student123")
    print(f"Session QR: CS101-SESSION-2026-03-11")
    
    db.close()

if __name__ == "__main__":
    seed_db()
