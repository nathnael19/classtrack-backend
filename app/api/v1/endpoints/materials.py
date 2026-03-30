from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Request
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
from ....core.limiter import limiter

router = APIRouter()

def sanitize_filename_for_header(filename: str) -> str:
    """
    Prevent header injection via Content-Disposition by stripping control chars
    and any path separators.
    """
    safe = os.path.basename(filename or "")
    safe = safe.replace("\r", "").replace("\n", "").replace("\0", "")
    # Keep printable chars only (simple, conservative)
    safe = "".join(ch for ch in safe if ch.isprintable() and ch not in {"\r", "\n", "\0"})
    return safe[:200] or "download"


def is_course_lecturer(user: User, course: Course) -> bool:
    """Helper to check if a user is a lecturer for a specific course."""
    if user.id == course.lecturer_id:
        return True
    return any(lecturer.id == user.id for lecturer in course.lecturers)

def is_student_enrolled(user: User, course: Course) -> bool:
    """Helper to check if a student is enrolled in a course."""
    return any(student.id == user.id for student in course.students)

@router.post("/upload", response_model=CourseMaterialOut)
@limiter.limit("5/minute")
async def upload_material(
    request: Request,
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
        
    # Security: Size Limit (50MB) - enforce regardless of UploadFile.size availability.
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Save file
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename")

    file_extension = os.path.splitext(file.filename)[1].lower()
    
    # Security: File Extension Allowlist
    ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv', '.zip', '.png', '.jpg', '.jpeg', '.mp4'}
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    MIME_ALLOWLIST_BY_EXT = {
        ".pdf": {"application/pdf"},
        ".doc": {"application/msword", "application/doc", "application/x-msword"},
        ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        ".xls": {"application/vnd.ms-excel", "application/excel", "application/x-msexcel"},
        ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        ".ppt": {"application/vnd.ms-powerpoint", "application/powerpoint", "application/x-mspowerpoint"},
        ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
        ".txt": {"text/plain"},
        ".csv": {"text/csv", "application/csv"},
        ".zip": {"application/zip", "application/x-zip-compressed", "multipart/x-zip"},
        ".png": {"image/png"},
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".mp4": {"video/mp4"},
    }

    # Validate extension+MIME when content_type is provided.
    if content_type and content_type not in MIME_ALLOWLIST_BY_EXT.get(file_extension, set()):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported MIME type '{content_type}' for extension '{file_extension}'",
        )
        
    filename = f"{uuid.uuid4()}{file_extension}"
    
    # Create course-specific directory for organization
    course_upload_dir = os.path.join(settings.UPLOADS_DIR, f"course_{course_id}")
    if not os.path.exists(course_upload_dir):
        os.makedirs(course_upload_dir)
        
    file_path = os.path.join(course_upload_dir, filename)
    
    # Read upload into memory with a strict cap, then write to disk.
    file_bytes = await file.read(MAX_FILE_SIZE + 1)
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 50MB.",
        )

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save file: {str(e)}"
        )

    file_size = len(file_bytes)
    
    # Create DB record
    # Store relative path for flexibility
    relative_path = f"uploads/course_{course_id}/{filename}"
    
    db_material = CourseMaterial(
        title=title,
        description=description,
        folder_name=folder_name,
        file_path=relative_path,
        original_filename=file.filename,
        file_type=content_type or "application/octet-stream",
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
@limiter.limit("30/minute")
def download_material(
    request: Request,
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
        
    # Use original filename if available, fallback to title + Extension.
    # Sanitize before using in Content-Disposition.
    if material.original_filename:
        filename = sanitize_filename_for_header(material.original_filename)
    else:
        filename = sanitize_filename_for_header(material.title)
        _, existing_ext = os.path.splitext(filename)
        if not existing_ext:
            _, file_ext = os.path.splitext(material.file_path)
            filename = sanitize_filename_for_header(f"{filename}{file_ext}")

    return FileResponse(
        path=full_path, 
        filename=filename,
        media_type=material.file_type or "application/octet-stream",
        headers={
            "X-Content-Type-Options": "nosniff",
        },
    )
