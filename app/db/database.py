'''
Database setup using SQLAlchemy for a SQLite database.
setup the engine, sessionmaker, and base class.
'''
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use a DB file under the repository `data/` directory
DB_FILE_PATH = "data/cds.db"

# Ensure the parent directory exists so the SQLite file can be created there
db_path = Path(DB_FILE_PATH)
db_path.parent.mkdir(parents=True, exist_ok=True)

# SQLAlchemy expects a URL; use a relative path to `data/cds.db`
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path.as_posix()}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()