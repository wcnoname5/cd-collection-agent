"""
ETL Merge - Combine original and API-enriched data

Usage:
    from etl.merge import merge_records
    
    original = [{"artist": "Pink Floyd", "title": "The Wall"}]
    enriched = [{"artist": "Pink Floyd", "title": "The Wall", "genre": "Rock"}]
    
    merged = merge_records(original, enriched)
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def merge_records(
    original: List[Dict[str, Any]],
    enriched: List[Dict[str, Any]],
    source_priority: str = "enriched"
) -> List[Dict[str, Any]]:
    """
    Merge original records with API-enriched records.
    
    Args:
        original: List of original imported records
        enriched: List of enriched records from API
        source_priority: "enriched" or "original" (which source wins on conflicts)
    
    Returns:
        List of merged records
    
    Note:
        Matching is done by position (original[i] + enriched[i]).
        Ensure lists are aligned before calling.
    """
    if len(original) != len(enriched):
        logger.warning(
            f"Original ({len(original)}) and enriched ({len(enriched)}) "
            f"have different lengths; will merge only matching indices"
        )
    
    merged = []
    
    for i in range(min(len(original), len(enriched))):
        orig_record = original[i]
        enrich_record = enriched[i]
        
        # Start with original
        merged_record = orig_record.copy()
        
        # Layer in enriched data
        for key, value in enrich_record.items():
            if value is None or value == "":
                # Skip empty enriched values
                continue
            
            if source_priority == "enriched":
                # Enriched data wins if present
                merged_record[key] = value
            elif source_priority == "original":
                # Original wins if present
                if key not in merged_record or merged_record[key] is None:
                    merged_record[key] = value
        
        merged.append(merged_record)
    
    logger.info(f"Merged {len(merged)} records (priority: {source_priority})")
    return merged


def merge_record_pair(
    original: Dict[str, Any],
    enriched: Dict[str, Any],
    source_priority: str = "enriched"
) -> Dict[str, Any]:
    """
    Merge a single original record with its enriched version.
    
    Args:
        original: Original record
        enriched: Enriched record
        source_priority: "enriched" or "original"
    
    Returns:
        Merged record
    """
    merged = original.copy()
    
    for key, value in enriched.items():
        if value is None or value == "":
            continue
        
        if source_priority == "enriched":
            merged[key] = value
        elif source_priority == "original":
            if key not in merged or merged[key] is None:
                merged[key] = value
    
    return merged
