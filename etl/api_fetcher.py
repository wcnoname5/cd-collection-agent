"""
ETL API Fetcher - Enrich CD data via Discogs API

Usage:
    from etl.api_fetcher import fetch_discogs_data, search_discogs
    
    enriched = fetch_discogs_data({"artist": "Pink Floyd", "title": "The Wall"})
    results = search_discogs("Pink Floyd", "The Wall")
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# Load env vars
load_dotenv()
DISCOGS_TOKEN = os.getenv("DISCOGS_TOKEN")
USER_AGENT = "CDCollectionAgent/1.0"

# Initialize Discogs client
try:
    import discogs_client
    d = discogs_client.Client(USER_AGENT, user_token=DISCOGS_TOKEN)
except ImportError:
    logger.error("discogs_client not installed. Install: pip install discogs-client")
    d = None


def similarity(a: str, b: str) -> float:
    """
    Calculate string similarity ratio (0.0 to 1.0).
    
    Args:
        a: First string
        b: Second string
    
    Returns:
        Similarity ratio
    """
    if not a or not b:
        return 0.0
    a_norm = a.lower().strip()
    b_norm = b.lower().strip()
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def search_discogs(artist: str, title: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search Discogs for album releases.
    
    Args:
        artist: Artist name
        title: Album title
        limit: Max results to return
    
    Returns:
        List of release info dicts
    
    Note:
        Rate limit: 60 requests per minute (1 request per second recommended)
    """
    if not d:
        logger.error("Discogs client not initialized")
        return []
    
    if not DISCOGS_TOKEN:
        logger.warning("DISCOGS_TOKEN not set; API requests may be rate-limited")
    
    try:
        query = f"{artist} {title}"
        logger.info(f"Searching Discogs: {query}")
        
        results = d.search(query, type='release')
        releases = []
        
        for idx, result in enumerate(results):
            if idx >= limit:
                break
            
            try:
                time.sleep(0.1)  # Be kind to the API
                if results.formats:
                    print(f'{results.formats}')
                release_data = {
                    "id": result.id,
                    "title": result.title,
                    "artist": result.artists[0].name if result.artists else "Unknown",
                    "year": result.year or None,
                    "genres": result.genres or [],
                    "styles": result.styles or [],
                    "country": result.country or "Unknown",
                    "formats": [fmt for fmt in result.formats] if result.formats else [],
                }
                releases.append(release_data)
            except Exception as e:
                logger.warning(f"Error parsing release {idx}: {e}")
                continue
        
        logger.info(f"Found {len(releases)} releases")
        return releases
    
    except Exception as e:
        logger.error(f"Discogs search error: {e}")
        return []


def fetch_discogs_data(record: Dict[str, Any], match_threshold: float = 0.7) -> Dict[str, Any]:
    """
    Enrich a CD record by fetching data from Discogs API.
    
    Prioritizes:
    1. CD format (over vinyl, cassette, etc.)
    2. Earlier/older releases (lower year values)
    3. Title similarity
    
    Args:
        record: Dictionary with artist, title (required), and optional year
        match_threshold: Similarity threshold (0.0-1.0) for matching
    
    Returns:
        Enriched record with genres, styles, cover art, etc.
    """
    if not d:
        logger.warning("Discogs client not initialized; returning original record")
        return record
    
    artist = record.get("artist", "").strip()
    title = record.get("title", "").strip()
    
    if not artist or not title:
        logger.warning(f"Missing artist or title: {record}")
        return record
    
    try:
        # Search Discogs
        releases = search_discogs(artist, title, limit=5)
        
        if not releases:
            logger.warning(f"No Discogs results for {artist} - {title}")
            return record
        
        # Pick best match based on multiple factors
        best_match = releases[0]
        best_score = 0.0
        
        for release in releases:
            release_title = release.get("title", "").lower()
            query_title = f"{artist} {title}".lower()
            
            # Base score: title similarity
            title_score = similarity(query_title, release_title)
            
            # Bonus: CD format (prefer CDs over vinyl, cassette, etc.)
            format_bonus = 0.0
            formats = release.get("formats", [])
            if any("cd" in fmt.lower() for fmt in formats):
                format_bonus = 0.1
            
            # Bonus: Earlier/older releases (normalize year to 0-1, lower year = higher score)
            year_bonus = 0.0
            release_year = release.get("year")
            if release_year and isinstance(release_year, int):
                # Prefer releases from 1900 onwards
                # Normalize to 0-1 range: older = higher score
                # Year 1900 = 1.0, Year 2024 = ~0.05
                year_bonus = max(0, 1.0 - (release_year - 1900) / 150)
                year_bonus *= 0.05  # Cap at 0.05 to not dominate title similarity
            
            # Combined score
            combined_score = title_score + format_bonus + year_bonus
            
            logger.debug(
                f"  Release: {release_title} | "
                f"Title: {title_score:.2f} | Format: {format_bonus:.2f} | Year: {year_bonus:.2f} | "
                f"Total: {combined_score:.2f} | Year: {release_year} | Formats: {formats}"
            )
            
            if combined_score > best_score:
                best_score = combined_score
                best_match = release
        
        if best_score < match_threshold:
            logger.warning(f"No good match found (score {best_score}); using best available")
        
        # Merge enriched data
        enriched = record.copy()
        enriched.update({
            "genre": " / ".join(best_match.get("genres", [])) or enriched.get("genre"),
            "style": " / ".join(best_match.get("styles", [])) or enriched.get("style"),
            "discogs_id": best_match.get("id"),
            "formats": " / ".join(best_match.get("formats", [])) or enriched.get("formats"),
            "country": best_match.get("country") or enriched.get("country"),
        })
        
        logger.info(
            f"Enriched {artist} - {title} with Discogs data "
            f"(match score: {best_score:.2f}, year: {best_match.get('year')}, "
            f"formats: {best_match.get('formats')})"
        )
        return enriched
    
    except Exception as e:
        logger.error(f"Error fetching Discogs data for {artist} - {title}: {e}")
        return record


def fetch_discogs_batch(records: List[Dict[str, Any]], delay: float = 1.0) -> List[Dict[str, Any]]:
    """
    Enrich a batch of records via Discogs API.
    
    Args:
        records: List of dictionaries to enrich
        delay: Delay (seconds) between API calls to respect rate limits
    
    Returns:
        List of enriched records
    
    Note:
        Discogs rate limit: 60 req/min (1 req/sec recommended)
    """
    enriched = []
    
    for idx, record in enumerate(records):
        logger.info(f"Processing {idx + 1}/{len(records)}: {record.get('artist')} - {record.get('title')}")
        enriched_record = fetch_discogs_data(record)
        enriched.append(enriched_record)
        
        if idx < len(records) - 1:
            time.sleep(delay)
    
    return enriched
