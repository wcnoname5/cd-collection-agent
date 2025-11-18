# discogs_agent.py
import os
import re
import time
from dotenv import load_dotenv
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

import discogs_client

# ----------------------------
# Config: replace with your token
# ----------------------------
load_dotenv()
DISCOGS_USER_TOKEN = os.getenv("DISCOGS_USER_TOKEN")
USER_AGENT = "CDCollectionAgent/1.0"

# Initialize Discogs client
d = discogs_client.Client(USER_AGENT, user_token=DISCOGS_USER_TOKEN)


# ----------------------------
# Helpers: clean / normalize
# ----------------------------
def normalize(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[^\w\s]', '', s)  # strip punctuation
    return s


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def format_cd_info(cd_info: dict) -> str:
    '''
    Format CD information into a readable string.
    '''
    title = cd_info.get("title", "Unknown Title")
    artist = cd_info.get("artist", "Unknown Artist")
    year = cd_info.get("year", "Unknown Year")
    formats = cd_info.get("formats", [])
    format_str = ', '.join(formats) if formats else "Unknown Format"
    return f"'{artist} ({year}) - {title} (Format: {format_str})'"


# ----------------------------
# Low-level Discogs functions
# ----------------------------
def search_album(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search Discogs for releases matching `query`.
    Returns a list of candidate dicts (limited).
    """
    results = d.search(query, type='release')  # search releases (not masters)
    candidates = []
    for i, release in enumerate(results):
        if i >= limit:
            break
        try:
            artist_names = ", ".join(a.name for a in getattr(release, "artists", [])) if getattr(release, "artists", None) else ""
            labels = ", ".join(l.name for l in getattr(release, "labels", [])) if getattr(release, "labels", None) else ""
            formats = []
            # release.formats sometimes returns list of dicts or objects
            for f in getattr(release, "formats", []) or []:
                if isinstance(f, dict):
                    formats.append(f.get("name", ""))
                elif isinstance(f, (list, tuple)):
                    formats.extend([x.get("name", "") if isinstance(x, dict) else str(x) for x in f])
                else:
                    try:
                        formats.append(f.name)
                    except Exception:
                        formats.append(str(f))

            candidates.append({
                "title": getattr(release, "title", None),
                "artist": artist_names,
                "year": getattr(release, "year", None),
                "label": labels,
                "country": getattr(release, "country", None),
                "id": getattr(release, "id", None),
                "formats": formats,
                # keep raw object lightly for later details if needed
                "_raw_obj": release,
            })
        except Exception:
            # skip problematic entries
            continue
    return candidates


def get_release_info(release_id: int) -> Dict[str, Any]:
    """
    Fetch detailed release info for a specific release id.
    Returns normalized dict ready to write to Sheets/DB.
    """
    release = d.release(release_id)

    # artists
    artists = ", ".join(a.name for a in getattr(release, "artists", [])) if getattr(release, "artists", None) else ""
    labels = [l.name for l in getattr(release, "labels", [])] if getattr(release, "labels", None) else []
    formats = []
    # release.formats sometimes returns list of dicts or objects
    for f in getattr(release, "formats", []) or []:
        if isinstance(f, dict):
            formats.append(f.get("name", ""))
        else:
            try:
                formats.append(f.name)
            except Exception:
                formats.append(str(f))

    tracklist = []
    for t in getattr(release, "tracklist", []) or []:
        # tracklist items can be objects or dicts
        try:
            tracklist.append(getattr(t, "title", t.get("title") if isinstance(t, dict) else str(t)))
        except Exception:
            continue

    # images: sometimes available in release.data['images']
    images = []
    try:
        for im in (release.data.get("images") or []):
            url = im.get("uri") or im.get("uri150") or im.get("resource_url")
            if url:
                images.append(url)
    except Exception:
        pass

    info = {
        "title": getattr(release, "title", None),
        "artist": artists,
        "year": getattr(release, "year", None),
        "labels": labels,
        "formats": formats,
        "tracklist": tracklist,
        "country": getattr(release, "country", None),
        "genre": getattr(release, "genres", None),
        "style": getattr(release, "styles", None),
        "images": images,
        "discogs_id": getattr(release, "id", None),
    }
    return info


# ----------------------------
# Scoring & ranking
# ----------------------------
def score_candidate(query: str, candidate: Dict[str, Any]) -> float:
    """
    Heuristic scoring:
    - title similarity (weight 0.45)
    - artist similarity (0.25)
    - year proximity exact (0.15)
    - CD format bonus (0.15)
    Scores 0..1
    """
    q_norm = normalize(query)
    title_norm = normalize(candidate.get("title") or "")
    artist_norm = normalize(candidate.get("artist") or "")

    title_sim = similarity(q_norm, title_norm)
    # also check if query contains artist-like pattern "artist - title"
    artist_sim = 0.0
    # try splitting "artist - title" style
    if "-" in query:
        parts = query.split("-", 1)
        if len(parts) == 2:
            artist_piece = normalize(parts[0])
            title_piece = normalize(parts[1])
            artist_sim = similarity(artist_piece, artist_norm) * 0.9 + similarity(title_piece, title_norm) * 0.1
    else:
        artist_sim = similarity(q_norm, artist_norm) * 0.2  # lesser weight if artist not provided in query

    # year score: 1 if year matches or if candidate has no year (neutral)
    year_score = 0.0
    try:
        q_years = re.findall(r'\b(19|20)\d{2}\b', query)
        if q_years:
            qy = int(q_years[0])
            cy = candidate.get("year")
            if cy:
                year_score = 1.0 if abs(int(cy) - qy) == 0 else max(0.0, 1.0 - min(10, abs(int(cy) - qy)) / 10.0)
    except Exception:
        year_score = 0.0

    # CD format bonus
    formats = [normalize(f) for f in (candidate.get("formats") or [])]
    cd_bonus = 0.0
    # look for tokens like "cd", "cd, album", "compact disc"
    for f in formats:
        if "cd" in f or "compact disc" in f:
            cd_bonus = 1.0
            break

    # Weighted combination
    score = (
        0.45 * title_sim +
        0.25 * artist_sim +
        0.15 * year_score +
        0.15 * cd_bonus
    )
    return score


def pick_best_match(query: str, candidates: List[Dict[str, Any]], require_cd: bool = False) -> List[Dict[str, Any]]:
    """
    Score and sort candidates. Returns sorted list (highest first).
    If require_cd is True, penalize non-CD formats heavily.
    """
    scored = []
    for c in candidates:
        s = score_candidate(query, c)
        if require_cd:
            formats = " ".join(c.get("formats") or [])
            if "cd" not in normalize(formats) and "compact disc" not in normalize(formats):
                s *= 0.5  # penalize non-CD
        scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": sc, **cand} for sc, cand in scored]
