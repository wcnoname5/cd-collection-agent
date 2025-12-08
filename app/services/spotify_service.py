'''
Spotify Service Module and APIs 
Handles Spotify OAuth2 authentication and fetching user's recent listening history.
'''
# app/services/spotify_service.py
import requests
import hashlib
import base64
from app.utils.spotify_oauth import load_tokens, save_tokens
 

class SpotifyService:
    AUTH_URL = "https://accounts.spotify.com/authorize"
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    # endpoints
    RECENT_URL = "https://api.spotify.com/v1/me/player/recently-played"

    def __init__(self, client_id, redirect_uri, token_path):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.token_path = token_path

    @staticmethod
    def generate_code_challenge(code_verifier):
        """Generate S256 code challenge from code verifier"""
        code_sha = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(code_sha).decode('utf-8')
        return code_challenge.rstrip('=')

    def build_auth_url(self, code_verifier):
        code_challenge = self.generate_code_challenge(code_verifier)
        return (
            f"{self.AUTH_URL}"
            "?response_type=code"
            f"&client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            "&scope=user-read-recently-played"
            "&code_challenge_method=S256"
            f"&code_challenge={code_challenge}"
        )

    def exchange_code_for_tokens(self, code, code_verifier):
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
        }
        response = requests.post(self.TOKEN_URL, data=data)
        tokens = response.json()
        
        # Check if response contains an error
        if "error" in tokens:
            raise ValueError(f"Spotify error: {tokens.get('error_description', tokens.get('error'))}")
        
        if "access_token" not in tokens:
            raise ValueError("No access token in response. Invalid credentials or code.")
        
        save_tokens(self.token_path, tokens)
        return tokens

    def refresh_access_token(self):
        tokens = load_tokens(self.token_path)
        if "refresh_token" not in tokens:
            return None

        data = {
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": self.client_id,
        }
        new_tokens = requests.post(self.TOKEN_URL, data=data).json()
        tokens.update(new_tokens)
        save_tokens(self.token_path, tokens)
        return tokens

    def get_recent_history(self, limit=50):
        tokens = load_tokens(self.token_path)
        
        if not tokens or "access_token" not in tokens:
            raise ValueError("No valid Spotify tokens found. Please authenticate first.")
        
        access = tokens.get("access_token")

        headers = {"Authorization": f"Bearer {access}"}
        params = {"limit": limit}

        r = requests.get(self.RECENT_URL, headers=headers, params=params)

        if r.status_code == 401:
            tokens = self.refresh_access_token()
            if not tokens or "access_token" not in tokens:
                raise ValueError("Failed to refresh Spotify tokens.")
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            r = requests.get(self.RECENT_URL, headers=headers, params=params)

        if r.status_code != 200:
            raise ValueError(f"Spotify API error: {r.status_code} - {r.text}")

        return r.json()
