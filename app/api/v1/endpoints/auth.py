from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from ....db.session import get_db
from ....core import security
from ....core.config import settings

from ....models.user import User, UserRole
from ....schemas.user import UserCreate, UserOut
from ....schemas.token import Token

router = APIRouter()

@router.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if a user with this email already exists
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
            # If the found user is NOT a placeholder (i.e. already has a real email),
            # then someone else has already registered with this student ID.
            if not placeholder.email.endswith('@classtrack.placeholder'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="This Student ID is already registered to another account"
                )
            
            # Update the placeholder account
            placeholder.name = user.name
            placeholder.email = user.email
            placeholder.hashed_password = hashed_password
            placeholder.department_id = user.department_id
            db.add(placeholder)
            db.commit()
            db.refresh(placeholder)
            return placeholder

    # Create new user if no placeholder found or if role is lecturer
    new_user = User(
        name=user.name,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role,
        student_id=user.student_id,
        department_id=user.department_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/token", response_model=Token)
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
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
def forgot_password(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if user exists for security
        return {"message": "If an account exists, a reset link has been sent."}
    
    # Stub: In a real app, generate a token, save to DB, and send email
    print(f"DEBUG: Password reset requested for {email}")
    return {"message": "Password reset email sent."}

@router.post("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    # Stub: In a real app, validate the token
    print(f"DEBUG: Email verification token received: {token}")
    return {"message": "Email verified successfully."}
