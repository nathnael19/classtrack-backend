from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.term import Term
from ....models.user import User, UserRole
from ....schemas.term import TermCreate, TermOut
from .users import get_current_user

router = APIRouter()

@router.get("/", response_model=List[TermOut])
def get_terms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Term).order_by(Term.start_date.desc()).all()

@router.post("/", response_model=TermOut, status_code=status.HTTP_201_CREATED)
def create_term(
    term_in: TermCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can create terms")
    
    db_term = Term(**term_in.dict())
    db.add(db_term)
    db.commit()
    db.refresh(db_term)
    return db_term

@router.get("/{term_id}", response_model=TermOut)
def get_term(
    term_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    term = db.query(Term).filter(Term.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")
    return term
