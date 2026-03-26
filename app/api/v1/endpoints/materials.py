from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
from datetime import datetime

from ....db.session import get_db
from ....core.config import settings
from ....models.user import User, UserRole
from ....models.course import Course
from ....models.course_material import CourseMaterial
from ....schemas.course_material import CourseMaterialOut
from .users import get_current_user

router = APIRouter()

def is_course_lecturer(user: User, course: Course) -> bool:
    """Helper to check if a user is a lecturer for a specific course."""
    if user.id == course.lecturer_id:
        return True
    return any(lecturer.id == user.id for lecturer in course.lecturers)

def is_student_enrolled(user: User, course: Course) -> bool:
    """Helper to check if a student is enrolled in a course."""
    return any(student.id == user.id for student in course.students)

@router.post("/upload", response_model=CourseMaterialOut)
async def upload_material(
    course_id: int = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    folder_name: Optional[str] = Form("General"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is a lecturer
    if current_user.role != UserRole.lecturer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only lecturers can upload materials"
        )
    
    # Fetch course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if this lecturer is assigned to this course
    if not is_course_lecturer(current_user, course):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload materials for this course"
        )
        
    # Security: Size Limit (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large. Maximum size is 50MB.")
    
    # Save file
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    # Security: File Extension Allowlist
    ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv', '.zip', '.png', '.jpg', '.jpeg', '.mp4'}
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    filename = f"{uuid.uuid4()}{file_extension}"
    
    # Create course-specific directory for organization
    course_upload_dir = os.path.join(settings.UPLOADS_DIR, f"course_{course_id}")
    if not os.path.exists(course_upload_dir):
        os.makedirs(course_upload_dir)
        
    file_path = os.path.join(course_upload_dir, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save file: {str(e)}"
        )
    finally:
        file.file.close()
        
    # Get file size
    file_size = os.path.getsize(file_path)
    
    # Create DB record
    # Store relative path for flexibility
    relative_path = f"uploads/course_{course_id}/{filename}"
    
    db_material = CourseMaterial(
        title=title,
        description=description,
        folder_name=folder_name,
        file_path=relative_path,
        original_filename=file.filename,
        file_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        course_id=course_id,
        uploader_id=current_user.id
    )
    
    db.add(db_material)
    db.commit()
    db.refresh(db_material)
    
    return db_material

@router.get("/course/{course_id}", response_model=List[CourseMaterialOut])
def list_course_materials(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    # Check permissions
    is_lecturer = is_course_lecturer(current_user, course)
    is_enrolled = is_student_enrolled(current_user, course)
    
    if current_user.role != UserRole.admin and not is_lecturer and not is_enrolled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access materials for this course"
        )
        
    return db.query(CourseMaterial).filter(CourseMaterial.course_id == course_id).all()

@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    material = db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
        
    course = db.query(Course).filter(Course.id == material.course_id).first()
    
    # Only the lecturer(s) can delete. Admins cannot (as per user request "only teacher will upload... other users only have access to read and download")
    # Wait, the user said "i don't want admins to upload... other users only have access to read and download".
    # This implies admins can't delete either? Or maybe admins can delete but not upload?
    # Usually admins can delete. But I'll follow the strict "only teacher" rule for mutations.
    
    if not is_course_lecturer(current_user, course):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course lecturers can delete materials"
        )
        
    # Delete file from filesystem
    full_path = os.path.join(settings.STATIC_DIR, material.file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
        
    db.delete(material)
    db.commit()
    return None

@router.get("/{material_id}/download", response_class=FileResponse)
def download_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    material = db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
        
    course = db.query(Course).filter(Course.id == material.course_id).first()
    
    # Check permissions
    is_lecturer = is_course_lecturer(current_user, course)
    is_enrolled = is_student_enrolled(current_user, course)
    
    if current_user.role != UserRole.admin and not is_lecturer and not is_enrolled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to download materials for this course"
        )
        
    # Get the file path
    full_path = os.path.join(settings.STATIC_DIR, material.file_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found on server")
        
    # Use original filename if available, fallback to title + Extension
    if material.original_filename:
        filename = material.original_filename
    else:
        filename = material.title
        _, existing_ext = os.path.splitext(filename)
        if not existing_ext:
            _, file_ext = os.path.splitext(material.file_path)
            filename = f"{filename}{file_ext}"

    return FileResponse(
        path=full_path, 
        filename=filename, 
        media_type=material.file_type
    )
