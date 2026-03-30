from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query, Request
from typing import List, Optional
import shutil
import os
import uuid
import io
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from PIL import Image, UnidentifiedImageError
import mimetypes
from fastapi.responses import FileResponse

from ....db.session import get_db
from ....core.config import settings

from ....models.user import User, UserRole, UserState
from ....schemas.user import UserOut, UserUpdate, UserCreateAdmin
from ....core.security import get_password_hash, verify_password
from ....core.email import send_setup_password_email
from ....core.limiter import limiter
from datetime import datetime, timedelta

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    # Block access for non-active accounts
    if user.account_status not in (UserState.active.value, None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.account_status}. Contact your administrator.",
        )

    return user

@router.get("/me", response_model=UserOut)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserOut)
def update_user_me(
    obj_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if obj_in.name is not None:
        current_user.name = obj_in.name
    if obj_in.email is not None:
        current_user.email = obj_in.email

    if obj_in.new_password is not None:
        if obj_in.current_password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to set a new password"
            )
        if not verify_password(obj_in.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        current_user.hashed_password = get_password_hash(obj_in.new_password)
    if obj_in.default_session_duration is not None:
        current_user.default_session_duration = obj_in.default_session_duration
    if obj_in.default_session_radius is not None:
        current_user.default_session_radius = obj_in.default_session_radius
    if obj_in.department_id is not None:
        current_user.department_id = obj_in.department_id

    # Extended student fields
    if obj_in.enrollment_year is not None:
        current_user.enrollment_year = obj_in.enrollment_year
    if obj_in.program is not None:
        current_user.program = obj_in.program
    if obj_in.academic_standing is not None:
        current_user.academic_standing = obj_in.academic_standing
    if obj_in.device_id is not None:
        current_user.device_id = obj_in.device_id
    if obj_in.biometric_status is not None:
        current_user.biometric_status = obj_in.biometric_status

    # Extended teacher fields
    if obj_in.title is not None:
        current_user.title = obj_in.title
    if obj_in.bio is not None:
        current_user.bio = obj_in.bio
    if obj_in.employment_type is not None:
        current_user.employment_type = obj_in.employment_type
    if obj_in.office_location is not None:
        current_user.office_location = obj_in.office_location
    if obj_in.office_hours is not None:
        current_user.office_hours = obj_in.office_hours
    if obj_in.website_url is not None:
        current_user.website_url = obj_in.website_url
    if obj_in.linkedin_url is not None:
        current_user.linkedin_url = obj_in.linkedin_url

    # Shared fields
    if obj_in.phone_number is not None:
        current_user.phone_number = obj_in.phone_number
    if obj_in.emergency_contact_name is not None:
        current_user.emergency_contact_name = obj_in.emergency_contact_name
    if obj_in.emergency_contact_phone is not None:
        current_user.emergency_contact_phone = obj_in.emergency_contact_phone
    if obj_in.date_of_birth is not None:
        current_user.date_of_birth = obj_in.date_of_birth
    if obj_in.gender is not None:
        current_user.gender = obj_in.gender
    if obj_in.account_status is not None:
        current_user.account_status = obj_in.account_status
    if obj_in.timezone is not None:
        current_user.timezone = obj_in.timezone

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/me/profile-picture", response_model=UserOut)
@limiter.limit("5/minute")
async def upload_profile_picture(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Strict allowlist: reject SVG and other active-content types.
    allowed_content_types = {"image/png", "image/jpeg"}
    if not file.content_type or file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image type. Allowed: image/png, image/jpeg",
        )

    # Enforce server-side size limit.
    file_bytes = await file.read()
    if len(file_bytes) > settings.PROFILE_PICTURES_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum is {settings.PROFILE_PICTURES_MAX_BYTES} bytes.",
        )

    # Re-encode image with Pillow to remove embedded active content.
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()  # Ensure it's a real image
        img = Image.open(io.BytesIO(file_bytes))
        img.load()
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image data",
        )

    if file.content_type == "image/jpeg":
        # Normalize to RGB and save as JPEG.
        img = img.convert("RGB")
        ext = ".jpg"
        save_format = "JPEG"
    else:
        # Normalize to RGBA and save as PNG.
        img = img.convert("RGBA")
        ext = ".png"
        save_format = "PNG"

    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(settings.PROFILE_PICTURES_DIR, filename)

    try:
        img.save(file_path, format=save_format, optimize=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save image: {str(e)}",
        )

    # Store only the filename (not a public URL).
    current_user.profile_picture_url = filename
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/profile-picture")
def get_profile_picture(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.profile_picture_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile picture not found")

    filename = os.path.basename(current_user.profile_picture_url)
    # Prefer the new private storage location.
    full_path = os.path.join(settings.PROFILE_PICTURES_DIR, filename)

    media_type = mimetypes.guess_type(full_path)[0] or "image/png"
    if not os.path.exists(full_path):
        # Backward compatibility: serve legacy static/uploads content if present.
        legacy_path = os.path.join(settings.UPLOADS_DIR, filename)
        if not os.path.exists(legacy_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile picture not found")
        full_path = legacy_path
        media_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"

    return FileResponse(
        path=full_path,
        media_type=media_type,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )

@router.get("/lecturers", response_model=List[UserOut])
def list_lecturers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List lecturers for co-lecturer assignment. Lecturers and admins can access."""
    if current_user.role not in (UserRole.admin, UserRole.lecturer):
        raise HTTPException(status_code=403, detail="Not authorized")
    return db.query(User).filter(User.role == UserRole.lecturer).all()


@router.get("/", response_model=List[UserOut])
def list_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List users with filtering and search. Admin only.
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )

    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    if q:
        search = f"%{q}%"
        query = query.filter(
            (User.name.ilike(search)) | (User.email.ilike(search))
        )
    
    users = query.offset(skip).limit(limit).all()
    return users

@router.post("/admin/create-user", response_model=UserOut)
def create_user_admin(
    user_in: UserCreateAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new user by an admin. The user will not have a password set.
    A setup token is generated and sent via email.
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists"
        )
    
    # Generate setup token
    setup_token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Create user - use organization_id from body or current user's org
    org_id = getattr(user_in, "organization_id", None) or current_user.organization_id
    user_data = getattr(user_in, "model_dump", lambda: user_in.dict())()
    user_data = {k: v for k, v in user_data.items() if k not in ("organization_id", "password")}
    new_user = User(
        **user_data,
        organization_id=org_id,
        setup_password_token=setup_token,
        setup_password_expires_at=expires_at,
        hashed_password="!",  # Placeholder
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send email
    send_setup_password_email(new_user.email, setup_token)
    
    return new_user

@router.get("/{user_id}", response_model=UserOut)
def get_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserOut)
def update_user_admin(
    user_id: int,
    obj_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if obj_in.name is not None:
        user.name = obj_in.name
    if obj_in.email is not None:
        user.email = obj_in.email
    if obj_in.role is not None:
        user.role = obj_in.role
    if obj_in.account_status is not None:
        user.account_status = obj_in.account_status
    if obj_in.department_id is not None:
        user.department_id = obj_in.department_id

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot purge your own identity")
        
    db.delete(user)
    db.commit()
    return None
