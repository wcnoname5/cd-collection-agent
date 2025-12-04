"""
CD Service - Database operations for CD collection
This module provides CRUD operations for the CD collection,
replacing the FastAPI router endpoints with direct Python functions.
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db import models
from app import schemas


def create_cd(db: Session, cd_data: schemas.CDCreate) -> models.CD:
    """Create a new CD in the database"""
    db_cd = models.CD(**cd_data.dict())
    db.add(db_cd)
    db.commit()
    db.refresh(db_cd)
    return db_cd


def get_cd_by_id(db: Session, cd_id: int) -> Optional[models.CD]:
    """Retrieve a CD by its ID"""
    return db.query(models.CD).filter(models.CD.id == cd_id).first()


def search_cds_by_title(db: Session, title: str) -> List[models.CD]:
    """Search CDs by title (case-insensitive partial match)"""
    return db.query(models.CD).filter(models.CD.title.ilike(f"%{title}%")).all()


def search_cds_by_artist(db: Session, artist: str) -> List[models.CD]:
    """Search CDs by artist (case-insensitive partial match)"""
    return db.query(models.CD).filter(models.CD.artist.ilike(f"%{artist}%")).all()


def get_all_cds(db: Session) -> List[models.CD]:
    """Get all CDs in the collection"""
    return db.query(models.CD).all()


def search_cds_vector(
    db: Session, 
    query: str, 
    embedding_model, 
    chroma_collection,
    n_results: int = 5
) -> List[models.CD]:
    """
    Search CDs by semantic embedding against the project's Chroma collection.
    
    Args:
        db: Database session
        query: Search query string
        embedding_model: Embedding model with encode method
        chroma_collection: ChromaDB collection
        n_results: Number of results to return (default 5)
    
    Returns:
        List of CD objects ordered by similarity
    """
    if not query:
        return []
    
    # Compute embedding
    try:
        # Try encode method first (sentence-transformers)
        embedding = embedding_model.encode([query])[0]
    except Exception:
        try:
            # Try embed_query method (some langchain models)
            embedding = embedding_model.embed_query(query)
        except Exception:
            return []
    
    # Query Chroma for top-k results
    try:
        results = chroma_collection.query(query_embeddings=[embedding], n_results=n_results)
    except Exception:
        return []
    
    # Extract IDs from results
    ids = []
    try:
        ids_out = results.get("ids") if isinstance(results, dict) else None
        if ids_out and len(ids_out) > 0:
            ids = ids_out[0]
    except Exception:
        ids = []
    
    # Convert to integers
    db_ids = []
    for i in ids:
        try:
            db_ids.append(int(i))
        except Exception:
            continue
    
    if not db_ids:
        return []
    
    # Fetch matching CDs preserving ordering
    cds = db.query(models.CD).filter(models.CD.id.in_(db_ids)).all()
    
    # Sort by the order of db_ids
    id_to_cd = {c.id: c for c in cds}
    ordered = [id_to_cd[i] for i in db_ids if i in id_to_cd]
    
    return ordered
