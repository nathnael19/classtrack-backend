from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
import shutil
import os
import uuid
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ....db.session import get_db
from ....core.config import settings

from ....models.user import User
from ....schemas.user import UserOut, UserUpdate
from ....core.security import get_password_hash, verify_password

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
