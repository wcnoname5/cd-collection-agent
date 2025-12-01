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
DISCOGS_TOKEN = os.getenv("DISCOGS_TOKEN")
USER_AGENT = "CDCollectionAgent/1.0"

# Initialize Discogs client
d = discogs_client.Client(USER_AGENT, user_token=DISCOGS_TOKEN)


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


# ----------------------------
# Top-level wrapper agent
# ----------------------------
def album_lookup_agent(query: str, limit: int = 5, require_cd: bool = True, auto_confirm: bool = False) -> Optional[Dict[str, Any]]:
    """
    High-level wrapper:
    1) search Discogs
    2) pick best matches (sorted)
    3) present top candidate(s) and optionally ask user to confirm or pick another
    4) fetch detailed info for chosen release and return structured dict
    - auto_confirm: if True, takes top candidate without interactive prompt (good for scripts)
    - require_cd: prefer CD formats
    Returns detailed release info dict or None if user cancels.
    """
    if not query or not query.strip():
        raise ValueError("Empty query")

    # 1) search
    candidates = search_album(query, limit=limit)
    if not candidates:
        print("No candidates found on Discogs.")
        return None

    # 2) rank
    ranked = pick_best_match(query, candidates, require_cd=require_cd)

    # 3) show top N (3) to user
    top_n = ranked[:3]
    if auto_confirm:
        chosen = top_n[0]
    else:
        print("\nTop matches:")
        for i, item in enumerate(top_n, start=1):
            print(f"{i}. {item.get('artist')} — {item.get('title')} ({item.get('year')}) | formats: {item.get('formats')} | score: {item.get('score'):.3f}")
        print("0. None of the above / Cancel")

        while True:
            try:
                pick = input("Pick the correct match number (default 1): ").strip()
                if pick == "":
                    pick_index = 1
                else:
                    pick_index = int(pick)
                if pick_index == 0:
                    print("Cancelled by user.")
                    return None
                if 1 <= pick_index <= len(top_n):
                    chosen = top_n[pick_index - 1]
                    break
                else:
                    print("Invalid choice. Enter 0..{len(top_n)}.")
            except ValueError:
                print("Please enter a number.")

    # 4) fetch detailed info
    release_id = chosen.get("id") or chosen.get("discogs_id") or chosen.get("release_id")
    if not release_id:
        # sometimes _raw_obj has .id
        raw = chosen.get("_raw_obj")
        if raw:
            release_id = getattr(raw, "id", None)

    if not release_id:
        print("Could not determine release id for chosen candidate.")
        return None

    # optional small delay to behave nicely with API
    time.sleep(0.2)
    try:
        detailed = get_release_info(int(release_id))
    except Exception as e:
        print(f"Error fetching release details: {e}")
        return None

    # final clean/normalize output for Sheets
    out = {
        "title": detailed.get("title"),
        "artist": detailed.get("artist"),
        "year": detailed.get("year"),
        "labels": "; ".join(detailed.get("labels") or []),
        "formats": "; ".join(detailed.get("formats") or []),
        "country": detailed.get("country"),
        "genres": ", ".join(detailed.get("genres") or []) if detailed.get("genres") else None,
        "styles": ", ".join(detailed.get("styles") or []) if detailed.get("styles") else None,
        "tracklist": " | ".join(detailed.get("tracklist") or []),
        "images": "; ".join(detailed.get("images") or []),
        "discogs_id": detailed.get("discogs_id"),
        "uri": detailed.get("uri"),
    }

    return out


# ----------------------------
# Example CLI usage
# ----------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Discogs album lookup agent (CD-focused).")
    parser.add_argument("query", help="Album query, e.g. 'OK Computer' or 'Radiohead - OK Computer 1997'")
    parser.add_argument("--no-cd", action="store_true", help="Do not require CD format (don't penalize non-CD)")
    parser.add_argument("--auto", action="store_true", help="Auto-confirm top match (non-interactive)")
    parser.add_argument("--limit", type=int, default=8, help="Number of search candidates to fetch")

    args = parser.parse_args()

    # ensure token is set
    if DISCOGS_USER_TOKEN == "YOUR_DISCOGS_PERSONAL_ACCESS_TOKEN":
        print("Please set DISCOGS_USER_TOKEN in this file before running.")
        raise SystemExit(1)

    result = album_lookup_agent(args.query, limit=args.limit, require_cd=not args.no_cd, auto_confirm=args.auto)
    if result:
        print("\nFinal metadata (structured):")
        for k, v in result.items():
            print(f"{k}: {v}")
    else:
        print("No metadata returned.")
