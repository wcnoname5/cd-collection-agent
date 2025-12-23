"""
Database initialization and reset utilities.

Usage:
    from app.db.init_db import reset_db, clear_all_records, get_record_count
    
    # Full reset: drop and recreate all tables
    reset_db()
    
    # Delete all records but keep tables
    clear_all_records()
    
    # Get current record count
    count = get_record_count()
"""

import logging
from app.db.database import engine, Base, SessionLocal
from app.db.models import CD

logger = logging.getLogger(__name__)


def init_db():
    """
    Initialize the database by creating all tables.
    Safe to call multiple times (only creates if tables don't exist).
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")


def reset_db():
    """
    Completely reset the database:
    1. Drop all existing tables
    2. Recreate all tables (fresh/empty)
    
    Use this for clean testing environments.
    """
    logger.warning("🔴 Resetting database - dropping all tables")
    Base.metadata.drop_all(bind=engine)
    
    logger.info("Creating fresh database tables")
    Base.metadata.create_all(bind=engine)
    
    logger.info("✅ Database reset complete - all tables dropped and recreated")


def clear_all_records():
    """
    Delete all records from the database while keeping table structure intact.
    
    Use this to test with empty data without full reset.
    
    Returns:
        Number of records deleted
    """
    db = SessionLocal()
    try:
        count = db.query(CD).delete()
        db.commit()
        logger.info(f"🗑️ Deleted {count} CD records - database now empty")
        return count
    except Exception as e:
        db.rollback()
        logger.error(f"Error clearing records: {e}")
        raise
    finally:
        db.close()
