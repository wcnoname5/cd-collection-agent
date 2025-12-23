# ETL Flow Documentation

## Overview

The CD Collection Agent now uses a clean **ETL (Extract, Transform, Load)** pipeline that separates data processing logic from the UI layer. This enables standalone batch processing, CLI workflows, and easy testing.

---

## Architecture

### Data Flow

```
Excel/CSV File
    ↓
etl/importer.py          (Extract raw data)
    ↓
etl/normalizer.py        (Transform: validate, standardize fields)
    ↓
[Optional] etl/api_fetcher.py    (Enrich: call Discogs API)
    ↓
etl/merge.py             (Merge original + enriched)
    ↓
app/db/manager.py        (Load: insert to SQLite)
    ↓
etl/queries.py           (Query interface)
    ↓
Streamlit UI / CLI / Analysis
```

### Folder Structure

```
etl/                          # Core ETL logic (no UI dependencies)
├── __init__.py
├── importer.py              # import_excel(), import_csv()
├── normalizer.py            # normalize_record(), validate_record()
├── api_fetcher.py           # fetch_discogs_data(), search_discogs()
├── merge.py                 # merge_records()
└── queries.py               # search_cds_by_title(), get_all_cds(), etc.

app/db/
├── database.py              # SQLAlchemy engine, session
├── models.py                # CD model
├── init_db.py               # Create schema
└── manager.py               # insert_cds_batch(), upsert_cd(), delete_cd()

ui/
└── streamlit_app.py         # UI layer (uses etl/queries.py, etl/api_fetcher.py)

scripts/
└── main.py                  # CLI entry point (orchestrates ETL steps)
```

---

## Module Contracts

### etl/importer.py

**Purpose:** Read Excel/CSV files and parse raw CD data

**Functions:**
- `import_excel(file_path: str) -> List[Dict]` — Import from Excel (.xlsx, .xls)
- `import_csv(file_path: str, delimiter: str) -> List[Dict]` — Import from CSV

**Output Schema:**
```python
[
    {
        "artist": "Pink Floyd",
        "title": "The Wall",
        "year": 1979,
        "genre": "Rock",
        "style": "Progressive Rock",
        # ... other fields
    },
    ...
]
```

**Requirements:**
- Excel file must have columns: `artist`, `title` (required)
- CSV must have same columns
- Handles missing values gracefully

---

### etl/normalizer.py

**Purpose:** Validate and standardize CD record data

**Functions:**
- `normalize_record(record: Dict) -> Dict` — Normalize strings, trim whitespace, standardize fields
- `validate_record(record: Dict) -> Tuple[bool, List[str]]` — Validate required/optional fields
- `validate_records(records: List[Dict]) -> Tuple[List, List]` — Batch validate, returns (valid, invalid)

**Normalization:**
- All string fields: lowercase, trim whitespace, collapse multiple spaces
- Year: convert to int, validate range (1900-2099)
- Empty/None values: skip

**Validation Rules:**
- Required: `artist`, `title` (non-empty strings)
- Optional: `year`, `genre`, `style`, `labels`, `formats`

**Output:**
```python
# Valid
(True, [])

# Invalid
(False, ["artist is required", "year should be between 1900 and 2099"])
```

---

### etl/api_fetcher.py

**Purpose:** Enrich CD data via Discogs API

**Functions:**
- `search_discogs(artist: str, title: str, limit: int) -> List[Dict]` — Search Discogs
- `fetch_discogs_data(record: Dict, match_threshold: float) -> Dict` — Enrich single record
- `fetch_discogs_batch(records: List[Dict], delay: float) -> List[Dict]` — Batch enrich

**Enriched Fields:**
- `genre` — From Discogs (overwrites imported)
- `style` — From Discogs (overwrites imported)
- `country` — Country of release
- `formats` — CD format (e.g., "Vinyl", "CD")
- `discogs_id` — Unique Discogs release ID

**Rate Limiting:**
- Discogs: 60 requests/min (1 req/sec recommended)
- Default delay: 1 second between requests

**Returns:** Merged dict with enriched fields

---

### etl/merge.py

**Purpose:** Combine original and API-enriched records

**Functions:**
- `merge_records(original, enriched, source_priority) -> List[Dict]` — Merge lists
- `merge_record_pair(original, enriched, source_priority) -> Dict` — Merge single pair

**Priority Modes:**
- `source_priority="enriched"` (default) — Enriched data wins
- `source_priority="original"` — Original data wins if present

**Example:**
```python
original = [{"artist": "Pink Floyd", "title": "The Wall"}]
enriched = [{"artist": "Pink Floyd", "title": "The Wall", "genre": "Rock"}]
merged = merge_records(original, enriched)
# Result: [{"artist": "Pink Floyd", "title": "The Wall", "genre": "Rock"}]
```

---

### app/db/manager.py

**Purpose:** High-level batch database operations

**Functions:**
- `insert_cds_batch(db, records: List[Dict]) -> int` — Batch insert, returns count
- `insert_cd_single(db, record: Dict) -> bool` — Insert one record
- `upsert_cd(db, record: Dict) -> Tuple[bool, CD]` — Insert or update (by artist+title)
- `delete_cd(db, cd_id: int) -> bool` — Delete by ID
- `bulk_delete_by_artist(db, artist: str) -> int` — Delete all by artist

**Transaction Handling:**
- Auto-commit on success
- Auto-rollback on error

---

### etl/queries.py

**Purpose:** Centralized DB query interface (read-only)

**Functions:**
- `search_cds_by_title(db, title: str) -> List[CD]` — Partial match
- `search_cds_by_artist(db, artist: str) -> List[CD]` — Partial match
- `get_cd_by_id(db, cd_id: int) -> CD` — Get by ID
- `get_all_cds(db) -> List[CD]` — Get all
- `filter_cds(db, artist, title, year, genre, limit) -> List[CD]` — Multi-filter
- `count_cds(db) -> int` — Total count

**Returns:** SQLAlchemy CD model instances

---

## Usage Examples

### 1. CLI Import with Enrichment

```bash
# Validate only
python scripts/main.py import data/albums.xlsx --validate-only

# Import and enrich via Discogs
python scripts/main.py import data/albums.xlsx --enrich --db

# Import without enrichment
python scripts/main.py import data/albums.xlsx --db
```

### 2. Programmatic ETL

```python
from etl.importer import import_excel
from etl.normalizer import normalize_record, validate_records
from etl.api_fetcher import fetch_discogs_batch
from etl.merge import merge_records
from app.db.manager import insert_cds_batch
from app.db.database import SessionLocal

# Step 1: Import
raw_records = import_excel("data/albums.xlsx")

# Step 2: Normalize
normalized = [normalize_record(r) for r in raw_records]

# Step 3: Validate
valid_records, invalid = validate_records(normalized)

# Step 4: Enrich
enriched = fetch_discogs_batch(valid_records)
merged = merge_records(valid_records, enriched)

# Step 5: Insert to DB
db = SessionLocal()
inserted = insert_cds_batch(db, merged)
print(f"Inserted {inserted} records")
```

### 3. Streamlit Usage

```python
from etl.queries import search_cds_by_artist, get_all_cds
from app.db.database import SessionLocal

db = SessionLocal()
results = search_cds_by_artist(db, "Pink Floyd")
for cd in results:
    print(f"{cd.artist} - {cd.title}")
```

### 4. CLI Search

```bash
python scripts/main.py search --artist "Pink Floyd"
python scripts/main.py search --title "Dark Side"
```

---

## Error Handling

### Import Errors
- File not found → `FileNotFoundError`
- Missing required columns → `ValueError`
- Invalid data types → `ValueError`

### Validation Errors
- Logged as warnings, invalid records excluded from processing
- Output: invalid records with error reasons

### API Errors
- Discogs timeout/rate limit → Logged, returns original record unmodified
- No match found → Uses first result or returns original

### DB Errors
- Duplicate key → Skipped with warning
- Rollback on commit failure

All errors are logged to console; see `logging.basicConfig()` in `scripts/main.py` for config.

---

## Future Extensibility

1. **New API Sources** — Add `etl/musicbrainz_fetcher.py`, `etl/spotify_fetcher.py`
2. **Data Validation Rules** — Add Pydantic validators to `etl/normalizer.py`
3. **Batch Scheduling** — Wire ETL to Celery or APScheduler
4. **Incremental Import** — Track import state, skip duplicates
5. **Data Export** — Add `etl/exporter.py` (CSV, JSON, Parquet)

---

## Quick Reference

| Task | How To |
|------|-------|
| Import Excel | `from etl.importer import import_excel` |
| Validate data | `from etl.normalizer import validate_records` |
| Search Discogs | `from etl.api_fetcher import search_discogs` |
| Enrich records | `from etl.api_fetcher import fetch_discogs_batch` |
| Merge data | `from etl.merge import merge_records` |
| Insert to DB | `from app.db.manager import insert_cds_batch` |
| Query DB | `from etl.queries import search_cds_by_artist` |
| CLI workflow | `python scripts/main.py import data.xlsx --enrich --db` |

