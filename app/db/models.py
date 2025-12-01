# from sqlalchemy.ext.declarative import declarative_base

# Base = declarative_base()
from sqlalchemy import Column, Integer, String, JSON
from .database import Base

class CD(Base):
    __tablename__ = "cds"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    artist = Column(String, index=True)
    year = Column(Integer)
    genre = Column(String)
    style = Column(String)
    tracklist = Column(JSON)
    labels = Column(JSON)
    formats = Column(JSON)
    images = Column(JSON)
    discogs_id = Column(String)
