import os
import gspread
from dotenv import load_dotenv # Don't forget to install this: pip install python-dotenv
from google.oauth2.service_account import Credentials

# Load environment variables from .env file
load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def init_gsheets_client(key_path="gcp_service_account.json"):
    '''
    Initialize and return a Google spread sheet client using service account credentials.
    '''
    creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client

def open_or_create_sheet(client, sheet_name):
    '''
    Opens an existing sheet or creates a new one in the specified Google Drive folder.
    If the sheet does not exist, it will attempt to open by GOOGLE_SHEET_ID environment variable.
    '''
    try:
        sh = client.open(sheet_name)
    except gspread.SpreadsheetNotFound:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if sheet_id:
            sh = client.open_by_key(sheet_id)
            return sh
        else:
            # Fallback to the old method or raise an error
            raise ValueError("GOOGLE_SHEET_ID not found in `.env` file.")
    return sh

def get_or_create_worksheet(sheet, worksheet_name, headers=None):
    # Add worksheet if it doesn't exist
    try:
        ws = sheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
        if headers:
            ws.append_row(headers)
    return ws


def append_cd_metadata(ws, cd_info: dict):
    """
    cd_info must be something like:
    {
        "title": "...",
        "artist": "...",
        "year": "...",
        "country": "...",
        "genre": "...",
        "style": "...",
        "tracklist": "...",
        "labels": "...",
        "formats": "...",
        "images": "...",
        "discogs_id": "..."
    }
    """
    # Define expected headers to maintain consistent column order
    expected_headers = ["title", "artist", "year", "country", "genre", "style", "tracklist", "labels", "formats", "images", "discogs_id"]
    
    # Create row with values in the correct order, converting all values to strings
    row = [str(cd_info.get(k, "")) for k in expected_headers]
    
    # Only append if we have valid data
    if any(cell.strip() for cell in row):
        ws.append_row(row)

