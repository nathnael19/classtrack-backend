from pydantic import BaseModel
from typing import Optional
from datetime import date

class TermBase(BaseModel):
    name: str
    start_date: date
    end_date: date

class TermCreate(TermBase):
    pass

class TermOut(TermBase):
    id: int
    organization_id: Optional[int] = None

    class Config:
        from_attributes = True
