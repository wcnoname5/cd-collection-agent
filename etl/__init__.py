"""
ETL Package - Extract, Transform, Load pipeline for Discogs CD collection

Modules:
- importer: Read Excel/CSV files
- normalizer: Validate and standardize data
- api_fetcher: Enrich data via Discogs API
- merge: Combine original and enriched data
- queries: Database query interface
"""

from .importer import import_excel, import_csv
from .normalizer import normalize_record, validate_record
from .api_fetcher import fetch_discogs_data, search_discogs
from .merge import merge_records
from .queries import (
    search_cds_by_title,
    search_cds_by_artist,
    get_cd_by_id,
    get_all_cds,
    filter_cds,
)

__all__ = [
    "import_excel",
    "import_csv",
    "normalize_record",
    "validate_record",
    "fetch_discogs_data",
    "search_discogs",
    "merge_records",
    "search_cds_by_title",
    "search_cds_by_artist",
    "get_cd_by_id",
    "get_all_cds",
    "filter_cds",
]
