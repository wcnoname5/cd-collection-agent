from tools.discogs_API_functions import format_cd_info, search_album, get_release_info, pick_best_match
from tools.gsheets_API_functions import (
    init_gsheets_client, open_or_create_sheet, get_or_create_worksheet, append_cd_metadata, is_duplicate, search_collection
) 

def check_collection_for_cd(query: str) -> bool:
    """
    Check if a CD is already in the Google Sheets collection.
    """
    client = init_gsheets_client()
    sh = open_or_create_sheet(client, "My CD Collection")
    ws = get_or_create_worksheet(sh, "CDs")

    # Search the collection directly
    results = search_collection(ws, query)
    if results:
        print(f"Found {len(results)} matching CDs in collection:")
        for result in results:
            print(format_cd_info(result))
        return True
    else:
        print("CD not found in collection.")
        return False
