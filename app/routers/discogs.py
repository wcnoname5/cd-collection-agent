from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from ..utils.discogs import search_album, get_release_info

router = APIRouter(prefix="/discogs", tags=["Discogs"])

@router.get("/search")
async def search_discogs(query: str = Query(..., min_length=1)) -> List[Dict[str, Any]]:
    """
    Search Discogs for albums matching the query.
    Returns a list of candidate releases.
    """
    try:
        results = search_album(query, limit=10)
        if not results:
            return []
        
        # Return simplified results for the frontend
        simplified_results = []
        for r in results:
            simplified_results.append({
                "id": r.get("id"),
                "title": r.get("title"),
                "artist": r.get("artist"),
                "year": r.get("year"),
                "label": r.get("label"),
                "country": r.get("country"),
                "formats": r.get("formats", [])
            })
        
        return simplified_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching Discogs: {str(e)}")

@router.get("/release/{release_id}")
async def get_release(release_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific release.
    """
    try:
        release_info = get_release_info(release_id)
        return release_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching release: {str(e)}")
