# app/utils/spotify_oauth.py
import json
from pathlib import Path

def load_tokens(path):
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text())

def save_tokens(path, tokens):
    p = Path(path)
    p.write_text(json.dumps(tokens, indent=2))
