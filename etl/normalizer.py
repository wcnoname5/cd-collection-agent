"""
ETL Normalizer - Validate and standardize CD record data

Usage:
    from etl.normalizer import normalize_record, validate_record
    
    record = {"artist": "  Pink Floyd  ", "title": "THE WALL"}
    normalized = normalize_record(record)
    # -> {"artist": "pink floyd", "title": "the wall", ...}
    
    is_valid = validate_record(normalized)
"""

from typing import Dict, Any, Tuple, List
import logging
import re

logger = logging.getLogger(__name__)


def normalize_string(s: str) -> str:
    """
    Normalize a string: lowercase, strip whitespace, collapse spaces, remove extra punctuation.
    
    Args:
        s: Input string
    
    Returns:
        Normalized string
    """
    if not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = re.sub(r'\s+', ' ', s)  # collapse multiple spaces
    return s


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a CD record: lowercase strings, trim whitespace, standardize fields.
    
    Args:
        record: Dictionary with keys like artist, title, year, genre, style, etc.
    
    Returns:
        Normalized dictionary
    """
    normalized = {}
    
    # String fields to normalize
    string_fields = ["artist", "title", "genre", "style", "labels", "formats"]
    for field in string_fields:
        if field in record and record[field]:
            normalized[field] = normalize_string(str(record[field]))
    
    # Numeric fields
    if "year" in record and record["year"]:
        try:
            normalized["year"] = int(record["year"])
        except (ValueError, TypeError):
            logger.warning(f"Invalid year value: {record.get('year')}, skipping")
    
    # Pass through other fields as-is
    for key, value in record.items():
        if key not in normalized and key not in string_fields + ["year"]:
            normalized[key] = value
    
    return normalized


def validate_record(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a normalized CD record.
    
    Required fields:
    - artist (non-empty string)
    - title (non-empty string)
    
    Optional fields:
    - year (positive integer, ideally 1900-2099)
    - genre, style, labels, formats (strings)
    
    Args:
        record: Normalized dictionary
    
    Returns:
        Tuple of (is_valid: bool, errors: List[str])
    """
    errors = []
    
    # Check required fields
    if not record.get("artist"):
        errors.append("artist is required and cannot be empty")
    
    if not record.get("title"):
        errors.append("title is required and cannot be empty")
    
    # Validate year if present
    if "year" in record:
        year = record["year"]
        if not isinstance(year, int):
            errors.append(f"year must be an integer, got {type(year)}")
        elif year < 1900 or year > 2099:
            errors.append(f"year should be between 1900 and 2099, got {year}")
    
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_records(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Validate a list of records and return valid/invalid splits.
    
    Args:
        records: List of normalized dictionaries
    
    Returns:
        Tuple of (valid_records, invalid_records_with_errors)
    """
    valid = []
    invalid = []
    
    for record in records:
        is_valid, errors = validate_record(record)
        if is_valid:
            valid.append(record)
        else:
            invalid.append({"record": record, "errors": errors})
            logger.warning(f"Invalid record: {record.get('artist', '?')} - {record.get('title', '?')}: {errors}")
    
    logger.info(f"Validation: {len(valid)} valid, {len(invalid)} invalid")
    return valid, invalid
