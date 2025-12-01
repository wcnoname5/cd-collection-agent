from pydantic import BaseModel
from typing import Optional

class CDBase(BaseModel):
    title: str
    artist: str
    year: Optional[int] = None
    genre: Optional[str] = None
    style: Optional[str] = None
    tracklist: Optional[str] = None
    labels: Optional[str] = None
    formats: Optional[str] = None
    images: Optional[str] = None
    discogs_id: Optional[str] = None

class CDCreate(CDBase):
    pass

class CD(CDBase):
    id: int
    class Config:
        orm_mode = True # from_attributes
