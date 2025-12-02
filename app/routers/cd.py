# Backend API for CD Collection Agent
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from ..db.database import SessionLocal
from ..db import models
from .. import schemas

router = APIRouter(prefix="/cds", tags=["CDs"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.CD)
def create_cd(cd: schemas.CDCreate, db: Session = Depends(get_db)):
    db_cd = models.CD(**cd.dict())
    db.add(db_cd)
    db.commit()
    db.refresh(db_cd)
    return db_cd

# get CD by its ID
@router.get("/{cd_id}", response_model=schemas.CD)
def read_cd(cd_id: int, db: Session = Depends(get_db)):
    return db.query(models.CD).filter(models.CD.id == cd_id).first()

# get all CDs
@router.get("/", response_model=list[schemas.CD])
def read_all_cds(db: Session = Depends(get_db)):
    return db.query(models.CD).all()


class QueryPayload(schemas.CDBase):
    # simple wrapper to validate incoming query payloads if needed
    # we'll only use the `title` field as a fallback, but accept raw query via `query` below
    pass


@router.get("/search_vector", response_model=list[schemas.CD])
async def search_vector(query: str, request: Request, db: Session = Depends(get_db)):
    """Search CDs by semantic embedding against the project's Chroma collection.

    Use as GET /cds/search_vector?query=jazz+piano
    Uses `request.app.state.embedding_model` and `request.app.state.chroma_collection`.
    """
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing 'query' parameter")

    # Get embedding model and chroma collection from app state
    embedding_model = getattr(request.app.state, "embedding_model", None)
    chroma = getattr(request.app.state, "chroma_collection", None)

    if embedding_model is None or chroma is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Embedding model or Chroma collection not configured on the app state")

    # Compute embedding (best-effort; different embedding APIs vary)
    try:
        # many embedding models expose an `encode` method that accepts list[str]
        embedding = embedding_model.encode([query])[0]
    except Exception:
        try:
            # some models use embed_query or embed_documents
            embedding = embedding_model.embed_query(query)
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Failed to create embedding with the configured model")

    # Query Chroma for top-k results
    try:
        results = chroma.query(query_embeddings=[embedding], n_results=5)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Chroma query failed")

    # results expected to be dict-like with 'ids'
    ids = []
    try:
        ids_out = results.get("ids") if isinstance(results, dict) else None
        if ids_out and len(ids_out) > 0:
            ids = ids_out[0]
    except Exception:
        ids = []

    # normalize ids to ints where possible
    db_ids = []
    for i in ids:
        try:
            db_ids.append(int(i))
        except Exception:
            # skip non-int ids — depending on how you stored metadata you may need to map differently
            continue

    if not db_ids:
        return []

    # fetch matching CDs preserving ordering
    cds = db.query(models.CD).filter(models.CD.id.in_(db_ids)).all()

    # sort cds by the order of db_ids
    id_to_cd = {c.id: c for c in cds}
    ordered = [id_to_cd[i] for i in db_ids if i in id_to_cd]

    return ordered