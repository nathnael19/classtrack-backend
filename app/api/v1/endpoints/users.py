from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ....db.session import get_db
from ....core.config import settings

from ....models.user import User
from ....schemas.user import UserOut, UserUpdate
from ....core.security import get_password_hash

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
    if obj_in.password is not None:
        current_user.hashed_password = get_password_hash(obj_in.password)
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
