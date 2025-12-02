"""Build embeddings for CDs and store them in a persistent Chroma collection.

Usage:
  python -m scripts.build_embeddings

Requirements:
  pip install sentence-transformers chromadb numpy

This script reads the SQLite DB used by the app (./cds.db), builds text
representations for each CD, embeds them with SentenceTransformer and stores
the vectors + metadata in a persistent Chroma collection at `data/chroma`.
"""

from pathlib import Path
import sqlite3
from typing import List
from app.db.database import DB_FILE_PATH

# db can further be customized further if needed
DB_PATH = Path(DB_FILE_PATH)  # matches app/db/database.py -> sqlite:///./cds.db
CHROMA_PATH = Path("data") / "chroma"
COLLECTION_NAME = "cds"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 128


def load_rows():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Ensure your DB exists and path matches.")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, title, artist, year, genre, style FROM cds")
    rows = cur.fetchall()
    conn.close()
    return rows


def chunked(iterable: List, size: int):
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


def main():
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        raise SystemExit("Install sentence-transformers: pip install sentence-transformers")

    try:
        import chromadb
    except Exception:
        raise SystemExit("Install chromadb: pip install chromadb")

    model = SentenceTransformer(MODEL_NAME)

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(COLLECTION_NAME)

    rows = load_rows()
    if not rows:
        print("No rows found in DB. Nothing to index.")
        return

    ids = [str(r["id"]) for r in rows]
    documents = [f"{(r['artist'] or '')} - {(r['title'] or '')}" for r in rows]
    metadatas = [
        {
            "id": int(r["id"]),
            "title": r["title"],
            "artist": r["artist"],
            "year": r["year"],
            "genre": r["genre"],
            "style": r["style"],
        }
        for r in rows
    ]

    # embed in batches
    embeddings = []
    for chunk in chunked(documents, BATCH_SIZE):
        emb = model.encode(chunk, show_progress_bar=False, convert_to_numpy=True)
        embeddings.extend(emb.tolist())

    # Upsert into chroma (use upsert if available)
    try:
        # try upsert (safer if existing ids present)
        collection.upsert(ids=ids, metadatas=metadatas, documents=documents, embeddings=embeddings)
    except Exception:
        # fallback to add (may fail if ids already exist)
        try:
            collection.add(ids=ids, metadatas=metadatas, documents=documents, embeddings=embeddings)
        except Exception as e:
            raise

    print("Done building embeddings. Collection size:", collection.count())


if __name__ == "__main__":
    main()
