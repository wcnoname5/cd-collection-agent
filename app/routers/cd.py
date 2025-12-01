# Backend API for CD Collection Agent
from fastapi import APIRouter, Depends
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