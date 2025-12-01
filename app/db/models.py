# from sqlalchemy.ext.declarative import declarative_base

# Base = declarative_base()
from sqlalchemy import Column, Integer, String
from .database import Base

class CD(Base):
    __tablename__ = "cds"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    artist = Column(String, index=True)
    year = Column(Integer)
    genre = Column(String)
    style = Column(String)
    tracklist = Column(String)
    labels = Column(String)
    formats = Column(String)
    images = Column(String)
    discogs_id = Column(String)
