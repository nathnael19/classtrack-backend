from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from ....db.session import get_db
from ....models.term import Term
from ....models.user import User, UserRole
from ....schemas.term import TermCreate, TermOut, TermUpdate
from .users import get_current_user

router = APIRouter()

@router.get("/", response_model=List[TermOut])
def get_terms(
    skip: int = 0,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Term).order_by(Term.start_date.desc()).offset(skip).limit(limit).all()

@router.post("/", response_model=TermOut, status_code=status.HTTP_201_CREATED)
def create_term(
    term_in: TermCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can create terms")

    org_id = term_in.organization_id or current_user.organization_id
    db_term = Term(
        name=term_in.name,
        year=term_in.year,
        status=term_in.status,
        start_date=term_in.start_date,
        end_date=term_in.end_date,
        organization_id=org_id,
    )
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

@router.put("/{term_id}", response_model=TermOut)
def update_term(
    term_id: int,
    term_in: TermUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can update terms")
    
    db_term = db.query(Term).filter(Term.id == term_id).first()
    if not db_term:
        raise HTTPException(status_code=404, detail="Term not found")
    
    update_data = term_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_term, field, value)
    
    db.commit()
    db.refresh(db_term)
    return db_term
