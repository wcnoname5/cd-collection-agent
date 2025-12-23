"""
ETL Importer - Read Excel/CSV files and parse CD data

Usage:
    from etl.importer import import_excel
    rows = import_excel("data/albums.xlsx")
    
    from etl.importer import import_csv
    rows = import_csv("data/albums.csv")
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def import_excel(file_path: str) -> List[Dict[str, Any]]:
    """
    Import CD records from an Excel file.
    
    Args:
        file_path: Path to Excel file (.xlsx, .xls)
    
    Returns:
        List of dictionaries with keys: artist, title, year, genre, style, etc.
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required columns (artist, title) are missing
    """
    try:
        import pandas as pd
    except ImportError:
        logger.error("pandas required for Excel import. Install: pip install pandas openpyxl")
        raise

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info(f"Reading Excel file: {file_path}")
    df = pd.read_excel(path)
    
    # Normalize column names: lowercase, strip whitespace
    df.columns = [col.lower().strip() for col in df.columns]
    
    # Check required columns
    required_cols = {"artist", "title"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}. Found: {list(df.columns)}")
    
    # Convert rows to list of dicts
    records = []
    for idx, row in df.iterrows():
        record = {k: v for k, v in row.to_dict().items() if pd.notna(v)}
        records.append(record)
    
    logger.info(f"Imported {len(records)} records from Excel")
    return records


def import_csv(file_path: str, delimiter: str = ",") -> List[Dict[str, Any]]:
    """
    Import CD records from a CSV file.
    
    Args:
        file_path: Path to CSV file
        delimiter: CSV delimiter (default: comma)
    
    Returns:
        List of dictionaries
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required columns (artist, title) are missing
    """
    try:
        import pandas as pd
    except ImportError:
        logger.error("pandas required for CSV import. Install: pip install pandas")
        raise

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info(f"Reading CSV file: {file_path}")
    df = pd.read_csv(path, delimiter=delimiter)
    
    # Normalize column names
    df.columns = [col.lower().strip() for col in df.columns]
    
    # Check required columns
    required_cols = {"artist", "title"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}. Found: {list(df.columns)}")
    
    # Convert rows to list of dicts
    records = []
    for idx, row in df.iterrows():
        record = {k: v for k, v in row.to_dict().items() if pd.notna(v)}
        records.append(record)
    
    logger.info(f"Imported {len(records)} records from CSV")
    return records
