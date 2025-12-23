"""
ETL Queries - Centralized database query interface

Usage:
    from sqlalchemy.orm import Session
    from etl.queries import search_cds_by_title, get_all_cds
    
    db = get_db_session()
    results = search_cds_by_title(db, "wall")
    all_cds = get_all_cds(db)
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


def get_cd_by_id(db: Session, cd_id: int) -> Optional[Any]:
    """
    Get a CD by ID.
    
    Args:
        db: SQLAlchemy session
        cd_id: CD ID
    
    Returns:
        CD model instance or None
    """
    from app.db.models import CD
    return db.query(CD).filter(CD.id == cd_id).first()


def search_cds_by_title(db: Session, title: str) -> List[Any]:
    """
    Search CDs by title (case-insensitive partial match).
    
    Args:
        db: SQLAlchemy session
        title: Search query
    
    Returns:
        List of CD model instances
    """
    from app.db.models import CD
    logger.info(f"Searching CDs by title: {title}")
    return db.query(CD).filter(CD.title.ilike(f"%{title}%")).all()


def search_cds_by_artist(db: Session, artist: str) -> List[Any]:
    """
    Search CDs by artist (case-insensitive partial match).
    
    Args:
        db: SQLAlchemy session
        artist: Artist name
    
    Returns:
        List of CD model instances
    """
    from app.db.models import CD
    logger.info(f"Searching CDs by artist: {artist}")
    return db.query(CD).filter(CD.artist.ilike(f"%{artist}%")).all()


def get_all_cds(db: Session) -> List[Any]:
    """
    Get all CDs in the collection.
    
    Args:
        db: SQLAlchemy session
    
    Returns:
        List of all CD model instances
    """
    from app.db.models import CD
    logger.info("Fetching all CDs")
    return db.query(CD).all()


def filter_cds(
    db: Session,
    artist: Optional[str] = None,
    title: Optional[str] = None,
    year: Optional[int] = None,
    genre: Optional[str] = None,
    limit: int = 100
) -> List[Any]:
    """
    Filter CDs by multiple criteria.
    
    Args:
        db: SQLAlchemy session
        artist: Artist name (partial match)
        title: Title (partial match)
        year: Release year (exact match)
        genre: Genre (partial match)
        limit: Max results
    
    Returns:
        List of CD model instances
    """
    from app.db.models import CD
    
    query = db.query(CD)
    
    if artist:
        query = query.filter(CD.artist.ilike(f"%{artist}%"))
    
    if title:
        query = query.filter(CD.title.ilike(f"%{title}%"))
    
    if year:
        query = query.filter(CD.year == year)
    
    if genre:
        query = query.filter(CD.genre.ilike(f"%{genre}%"))
    
    logger.info(
        f"Filtering CDs: artist={artist}, title={title}, year={year}, genre={genre}"
    )
    
    return query.limit(limit).all()


def count_cds(db: Session) -> int:
    """
    Get total count of CDs in collection.
    
    Args:
        db: SQLAlchemy session
    
    Returns:
        Total count
    """
    from app.db.models import CD
    count = db.query(CD).count()
    logger.info(f"Total CDs in collection: {count}")
    return count


def get_cds_by_discogs_ids(db: Session, discogs_ids: List[str]) -> List[Any]:
    """
    Get CDs by Discogs IDs.
    
    Args:
        db: SQLAlchemy session
        discogs_ids: List of Discogs IDs
    
    Returns:
        List of CD model instances
    """
    from app.db.models import CD
    logger.info(f"Fetching CDs by {len(discogs_ids)} Discogs IDs")
    return db.query(CD).filter(CD.discogs_id.in_(discogs_ids)).all()
