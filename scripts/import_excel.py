"""Import an Excel file of CDs into the project.

This script supports two modes:
 - direct: write rows directly to the local SQLAlchemy DB used by the app (default)
 - api: POST rows to a running FastAPI instance at /cds/ (useful to exercise app logic)

Usage examples:
  # direct DB write (default)
  python scripts/import_excel.py data/albums.xlsx

  # POST to API
  python scripts/import_excel.py data/albums.xlsx --mode api --api-url http://localhost:8000

Excel file requirements:
  - Header row with columns (case-insensitive): artist, title, year

Dependencies: pandas, requests (for API mode)
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def import_direct(path: Path) -> int:
    """Import rows directly into the app's SQLite DB using SQLAlchemy."""
    try:
        import pandas as pd
    except Exception:
        print("Install pandas: pip install pandas openpyxl")
        raise

    from app.db.database import engine, Base, SessionLocal
    from app.db.models import CD

    # ensure tables exist
    Base.metadata.create_all(bind=engine)

    df = pd.read_excel(path)
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"artist", "title", "year"}
    if not required.issubset(set(df.columns)):
        print(f"Excel must contain columns: {required}. Found: {list(df.columns)}")
        return 2

    session = SessionLocal()
    inserted = 0
    try:
        for _, row in df.iterrows():
            artist = None if pd.isna(row.get("artist")) else str(row.get("artist")).strip()
            title = None if pd.isna(row.get("title")) else str(row.get("title")).strip()
            year_val = row.get("year")
            try:
                year = int(year_val) if not pd.isna(year_val) else None
            except Exception:
                year = None

            if not title and not artist:
                continue

            cd = CD(title=title, artist=artist, year=year)
            session.add(cd)
            inserted += 1

        session.commit()
        print(f"Inserted {inserted} rows into the database.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return 0


def import_api(path: Path, api_url: str) -> int:
    """POST rows to the API endpoint `/cds/`. Expects the API to be running."""
    try:
        import pandas as pd
    except Exception:
        print("Install pandas: pip install pandas openpyxl")
        raise

    try:
        import requests
    except Exception:
        print("Install requests: pip install requests")
        raise

    df = pd.read_excel(path)
    df.columns = [c.lower().strip() for c in df.columns]

    required = {"artist", "title", "year"}
    if not required.issubset(set(df.columns)):
        print(f"Excel must contain columns: {required}. Found: {list(df.columns)}")
        return 2

    endpoint = api_url.rstrip("/") + "/cds/"
    inserted = 0
    session = requests.Session()
    for _, row in df.iterrows():
        payload = {
            "artist": None if pd.isna(row.get("artist")) else str(row.get("artist")).strip(),
            "title": None if pd.isna(row.get("title")) else str(row.get("title")).strip(),
        }
        year_val = row.get("year")
        try:
            year = int(year_val) if not pd.isna(year_val) else None
        except Exception:
            year = None
        payload["year"] = year

        if not payload["title"] and not payload["artist"]:
            continue

        r = session.post(endpoint, json=payload)
        if r.status_code in (200, 201):
            inserted += 1
        else:
            print(f"Failed to POST row: {payload} -> status {r.status_code}: {r.text}")

    print(f"Posted {inserted} rows to {endpoint}")
    return 0

# BASE_URL = "http://127.0.0.1:8000"
# BASE_URL = "http://localhost:8000"

def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Import albums from Excel into DB or API")
    p.add_argument("xlsx", type=Path, help="Path to Excel file")
    p.add_argument("--mode", choices=("direct", "api"), default="direct", help="Import mode: direct DB write or POST to API")
    p.add_argument("--api-url", default="http://127.0.0.1:8000", help="Base URL of running API (used with --mode api)")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    path = args.xlsx
    if not path.exists():
        print(f"File not found: {path}")
        return 2

    if args.mode == "direct":
        return import_direct(path)
    else:
        return import_api(path, args.api_url)


if __name__ == "__main__":
    raise SystemExit(main())
