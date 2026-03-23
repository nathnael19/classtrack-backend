from pydantic import BaseModel
from typing import Optional
from datetime import date

class TermBase(BaseModel):
    name: str
    year: Optional[str] = None
    status: Optional[str] = "Upcoming"
    start_date: date
    end_date: date
    organization_id: Optional[int] = None

class TermCreate(TermBase):
    pass

class TermUpdate(BaseModel):
    name: Optional[str] = None
    year: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    organization_id: Optional[int] = None

class TermOut(TermBase):
    id: int
    organization_id: Optional[int] = None

    class Config:
        from_attributes = True
