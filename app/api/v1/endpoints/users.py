from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query
from typing import List, Optional
import shutil
import os
import uuid
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ....db.session import get_db
from ....core.config import settings

from ....models.user import User, UserRole
from ....schemas.user import UserOut, UserUpdate, UserCreateAdmin
from ....core.security import get_password_hash, verify_password
from ....core.email import send_setup_password_email
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
        
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/me/profile-picture", response_model=UserOut)
async def upload_profile_picture(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    if not file_extension:
        # Fallback for some image types
        if file.content_type == "image/jpeg": file_extension = ".jpg"
        elif file.content_type == "image/png": file_extension = ".png"
        else: file_extension = ".png"

    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.UPLOADS_DIR, filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_MESSAGE,
            detail=f"Could not save file: {str(e)}"
        )
    finally:
        file.file.close()
    
    # Update user profile_picture_url
    # Store relative URL
    current_user.profile_picture_url = f"{settings.STATIC_URL_PREFIX}/uploads/{filename}"
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return current_user

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
    
    # Create user
    new_user = User(
        **user_in.dict(),
        setup_password_token=setup_token,
        setup_password_expires_at=expires_at,
        hashed_password="!", # Place holder
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send email
    send_setup_password_email(new_user.email, setup_token)
    
    return new_user
