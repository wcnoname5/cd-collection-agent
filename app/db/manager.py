"""
Database Manager - High-level batch DB operations

Usage:
    from app.db.manager import insert_cds_batch, get_session
    from etl.importer import import_excel
    from etl.normalizer import normalize_record, validate_records
    
    session = get_session()
    raw_records = import_excel("data/albums.xlsx")
    normalized = [normalize_record(r) for r in raw_records]
    valid_records, invalid = validate_records(normalized)
    count = insert_cds_batch(session, valid_records)
"""

from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging

logger = logging.getLogger(__name__)


def insert_cds_batch(db: Session, records: List[Dict[str, Any]]) -> int:
    """
    Batch insert CD records into the database.
    
    Args:
        db: SQLAlchemy session
        records: List of CD dictionaries
    
    Returns:
        Number of successfully inserted records
    
    Raises:
        Exception: If batch insert fails
    """
    from app.db.models import CD
    from app import schemas
    
    inserted_count = 0
    failed_records = []
    
    for idx, record in enumerate(records):
        try:
            # Create Pydantic schema for validation
            cd_create = schemas.CDCreate(**record)
            
            # Create model instance
            db_cd = CD(**cd_create.dict())
            db.add(db_cd)
            inserted_count += 1
            
        except (ValueError, TypeError, IntegrityError) as e:
            logger.warning(f"Failed to insert record {idx}: {record} - {e}")
            failed_records.append({"record": record, "error": str(e)})
            continue
    
    try:
        db.commit()
        logger.info(f"Batch insert: {inserted_count} successful, {len(failed_records)} failed")
        return inserted_count
    
    except Exception as e:
        db.rollback()
        logger.error(f"Batch commit failed: {e}")
        raise


def insert_cd_single(db: Session, record: Dict[str, Any]) -> bool:
    """
    Insert a single CD record.
    
    Args:
        db: SQLAlchemy session
        record: CD dictionary
    
    Returns:
        True if successful, False otherwise
    """
    from app.db.models import CD
    from app import schemas
    
    try:
        cd_create = schemas.CDCreate(**record)
        db_cd = CD(**cd_create.dict())
        db.add(db_cd)
        db.commit()
        logger.info(f"Inserted: {record.get('artist')} - {record.get('title')}")
        return True
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to insert record: {record} - {e}")
        return False


def upsert_cd(db: Session, record: Dict[str, Any]) -> Tuple[bool, Any]:
    """
    Insert or update a CD record (by artist + title).
    
    Args:
        db: SQLAlchemy session
        record: CD dictionary
    
    Returns:
        Tuple of (success: bool, cd_model: CD or None)
    """
    from app.db.models import CD
    from app import schemas
    
    try:
        artist = record.get("artist", "").lower().strip()
        title = record.get("title", "").lower().strip()
        
        # Check if exists
        existing = db.query(CD).filter(
            CD.artist.ilike(artist),
            CD.title.ilike(title)
        ).first()
        
        if existing:
            # Update existing
            for key, value in record.items():
                if value is not None and hasattr(existing, key):
                    setattr(existing, key, value)
            logger.info(f"Updated: {artist} - {title}")
        else:
            # Insert new
            cd_create = schemas.CDCreate(**record)
            existing = CD(**cd_create.dict())
            db.add(existing)
            logger.info(f"Inserted: {artist} - {title}")
        
        db.commit()
        return True, existing
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to upsert record: {record} - {e}")
        return False, None


def delete_cd(db: Session, cd_id: int) -> bool:
    """
    Delete a CD by ID.
    
    Args:
        db: SQLAlchemy session
        cd_id: CD ID
    
    Returns:
        True if successful, False otherwise
    """
    from app.db.models import CD
    
    try:
        cd = db.query(CD).filter(CD.id == cd_id).first()
        if not cd:
            logger.warning(f"CD {cd_id} not found")
            return False
        
        db.delete(cd)
        db.commit()
        logger.info(f"Deleted CD {cd_id}")
        return True
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete CD {cd_id}: {e}")
        return False