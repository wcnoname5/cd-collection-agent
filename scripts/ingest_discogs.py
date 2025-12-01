# TODO: Implement Discogs API 

from discogs_tool import search_album, get_release_info
from gsheets_tool import (
    init_gsheets_client, open_or_create_sheet, get_or_create_worksheet, append_cd_metadata
) 

def add_cd_to_sheets(query):
    """
    Search Discogs for the album and write the first match into Google Sheets.
    Very simple pipeline.
    """

    # Step 1: Search
    release = search_album(query, limit=5)
    if release is None:
        print("No results found on Discogs.")
        return

    # Step 2: Convert to metadata dict
    # Currently we just takes the first result metadata.
    # TODO: handle multiple results and enable user to select best release
    metadata = get_release_info(release[0]['id'])
    # Step 3: Write to Google Sheets
    client = init_gsheets_client()
    sheet = open_or_create_sheet(client, "My CD Collection")
    ws = get_or_create_worksheet(
        sheet,
        "CDs",
        headers=[
            "title",
            "artist",
            "year",
            "country",
            "genre",
            "style",
            "tracklist",
            "labels",
            "formats",
            "images",
            "discogs_id",
        ]
    )

    append_cd_metadata(ws, metadata)
    print(f"Added: {metadata.get('title')} - {metadata.get('artist')}")

if __name__ == "__main__":
    # Example usage
    add_cd_to_sheets("The Dark Side of the Moon")