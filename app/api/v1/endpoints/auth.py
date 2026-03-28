from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import secrets

from ....db.session import get_db
from ....core import security
from ....core.config import settings
from ....models.user import User, UserRole
from ....schemas.user import UserCreate, UserOut, PasswordSetupSchema
from ....schemas.token import Token
from ....core.limiter import limiter
from ....core.email import send_password_reset_email

router = APIRouter()


@router.post("/register", response_model=UserOut)
@limiter.limit("5/minute")
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    db_user_email = db.query(User).filter(User.email == user.email).first()
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = security.get_password_hash(user.password)

    # STUDENT MERGING LOGIC:
    # If the user is a student, check if a placeholder exists for their student_id
    if user.role == UserRole.student and user.student_id:
        placeholder = db.query(User).filter(
            User.student_id == user.student_id,
            User.role == UserRole.student
        ).first()

        if placeholder:
            if not placeholder.email.endswith('@classtrack.placeholder'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This Student ID is already registered to another account"
                )
            placeholder.name = user.name
            placeholder.email = user.email
            placeholder.hashed_password = hashed_password
            placeholder.department_id = user.department_id
            placeholder.section = user.section
            db.add(placeholder)
            db.commit()
            db.refresh(placeholder)
            return placeholder

    org_id = getattr(user, "organization_id", None)
    new_user = User(
        name=user.name,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role,
        student_id=user.student_id,
        department_id=user.department_id,
        section=user.section,
        organization_id=org_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
def login_for_access_token(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password")
@limiter.limit("3/hour")
def forgot_password(request: Request, email: str, db: Session = Depends(get_db)):
    """
    Sends a password reset link to the user's email.
    Always returns the same message to avoid revealing whether an account exists.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"message": "If an account exists with that email, a reset link has been sent."}

    # Generate a cryptographically secure token, valid for 1 hour
    reset_token = secrets.token_urlsafe(32)
    user.setup_password_token = reset_token
    user.setup_password_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.add(user)
    db.commit()

    send_password_reset_email(user.email, reset_token)

    return {"message": "If an account exists with that email, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(data: PasswordSetupSchema, db: Session = Depends(get_db)):
    """Complete a password reset using a token received via email."""
    user = db.query(User).filter(
        User.setup_password_token == data.token,
        User.setup_password_expires_at > datetime.utcnow()
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired. Please request a new one."
        )

    user.hashed_password = security.get_password_hash(data.new_password)
    user.setup_password_token = None
    user.setup_password_expires_at = None
    db.add(user)
    db.commit()

    return {"message": "Password updated successfully. You can now log in."}


@router.post("/setup-password")
def setup_password(data: PasswordSetupSchema, db: Session = Depends(get_db)):
    """Set a password for admin-created accounts using their setup token."""
    user = db.query(User).filter(
        User.setup_password_token == data.token,
        User.setup_password_expires_at > datetime.utcnow()
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )

    user.hashed_password = security.get_password_hash(data.new_password)
    user.setup_password_token = None
    user.setup_password_expires_at = None
    user.is_verified = True

    db.add(user)
    db.commit()

    return {"message": "Password set successfully"}
