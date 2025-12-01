from pydantic import BaseModel

class CD(BaseModel):
    id: int
    title: str
    artist: str
