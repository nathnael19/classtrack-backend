from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ....db.session import get_db
from ....models.organization import Organization
from ....models.user import User
from .users import get_current_user
from pydantic import BaseModel

router = APIRouter()

class OrganizationBase(BaseModel):
    name: str
    domain: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationOut(OrganizationBase):
    id: int
    class Config:
        from_attributes = True

@router.post("/", response_model=OrganizationOut)
def create_organization(
    org: OrganizationCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create organizations")
    
    db_org = Organization(name=org.name, domain=org.domain)
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org

@router.get("/", response_model=List[OrganizationOut])
def list_organizations(db: Session = Depends(get_db)):
    return db.query(Organization).all()
