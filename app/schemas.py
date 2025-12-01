from pydantic import BaseModel
from typing import Optional

class CDBase(BaseModel):
    title: str
    artist: str
    year: Optional[int] = None
    genre: Optional[str] = None
    style: Optional[str] = None
    tracklist: Optional[list[str]] = None
    labels: Optional[list[str]] = None
    formats: Optional[list[str]] = None
    images: Optional[list[str]] = None
    discogs_id: Optional[str] = None

class CDCreate(CDBase):
    pass

class CD(CDBase):
    id: int
    class Config:
        orm_mode = True # from_attributes
