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


def init_gsheets_client(key_path="gcp_credentials.json"):
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


def is_duplicate(ws, cd_infor: dict) -> bool:
    '''
    Check if the CD info already exists in the worksheet.
    '''
    discogs_id = str(cd_infor.get("discogs_id"))
    title = cd_infor.get("title", "").lower()
    artist = cd_infor.get("artist", "").lower()
    # Into a list of dicts, each dict represents a row
    existing = ws.get_all_records()

    for row in existing:
        # check Discogs ID first (most reliable)
        if str(row.get("discogs_id")) == discogs_id:
            return True

        # fallback check
        if row.get("title", "").lower() == title and row.get("artist", "").lower() == artist:
            return True

    return False


def append_cd_metadata(ws, cd_info: dict):
    """
    Appends CD metadata to worksheet. cd_info should contain keys like 
    title, artist, year, country, genre, style, etc.
    """
    # Define expected headers to maintain consistent column order
    expected_headers = ["title", "artist", "year", "country", "genre", "style", "tracklist", "labels", "formats", "images", "discogs_id"]
    
    # Create row with values in the correct order, converting all values to strings
    row = [str(cd_info.get(k, "")) for k in expected_headers]
    
    # Only append if we have valid data
    if any(cell.strip() for cell in row):
        ws.append_row(row)


# ==========
#  Searching specific collections in Google Sheets
# =========

def search_collection(ws, query: str) -> list:
    """
    Search cd info in current collection (a worksheet) by query string.
    """
    # Get all records from the worksheet
    records = ws.get_all_records()
    
    query_lower = query.lower()
    matches = []
    
    for record in records:
        # Search in title, artist, genre, style fields
        searchable_fields = [
            record.get("title", ""),
            record.get("artist", ""),
            record.get("genre", ""),
            record.get("style", "")
        ]
        
        # Check if query matches any of the searchable fields
        if any(query_lower in str(field).lower() for field in searchable_fields):
            matches.append(record)
    
    return matches
