from tools.discogs_API_functions import format_cd_info, search_album, get_release_info, pick_best_match
from tools.gsheets_API_functions import (
    init_gsheets_client, open_or_create_sheet, get_or_create_worksheet, append_cd_metadata, is_duplicate, search_collection
) 


def choose_release(releases):
    '''
    Let the user choose a release from the search results.
    '''
    print("\nSearch results:")
    for i, r in enumerate(releases):
        print(f"{i+1}. {r['artist']}({r['year']}) - {r['title']} (Format: {', '.join(r['formats']) if 'formats' in r else ''})")

    while True:
        choice = input("Pick the correct release (1–{}), or 0 to cancel: ".format(len(releases)))
        if choice.isdigit():
            choice = int(choice)
            if 0 <= choice <= len(releases):
                return None if choice == 0 else releases[choice - 1]
        print("Invalid input.")


def add_cd_to_sheets(query: str, auto_confirm: bool = False):
    """
    Searches Discogs for an album and adds the first or selected match to a Google Sheets collection.
    This function performs a complete workflow: searches Discogs for albums matching the query,
    allows user selection (or auto-selects if specified), checks for duplicates in the existing
    collection, and appends the album metadata to a Google Sheets worksheet.
    Args:
        query (str): The search query for the album (e.g., artist name, album title, or both).
        auto_confirm (bool, optional): If True, automatically selects the best match without 
                                     user interaction. If False, prompts user to choose from 
                                     search results. Defaults to False.
    Returns:
        None: This function doesn't return a value but prints status messages and may prompt 
              for user input during execution.   
    """

    # Step 1: Search & select release
    search_results = search_album(query, limit=5)
    if search_results is None:
        print("No results found on Discogs.")
        return
    
    # Sort options by relevance
    candidates = pick_best_match(query, search_results)
    if auto_confirm and candidates:
        user_pick = candidates[0]
        print(f"Auto-selected: {format_cd_info(user_pick)}")
    else:
        user_pick = choose_release(candidates)
        if user_pick is None:
            print("Cancelled.")
            return

    # Step 2: Write chosen album to Google Sheets
    selected_metadata = get_release_info(user_pick['id'])
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
    # Check for duplicates
    cd_info = format_cd_info(selected_metadata)

    if is_duplicate(ws, selected_metadata):
        choice = input(f"'{cd_info}' is already in the collection. Add anyway? (y/N): ")
        if choice.lower() not in ['y', 'yes']:
            print("Skipped duplicate CD.")
            return
    append_cd_metadata(ws, selected_metadata)
    print(f"Added: 'cd_info'")


# ==========
#  Service: Searching collections in Google Sheets
# ==========

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


def select_service():
    """
    Let the user select which service to use: Discogs or Google Sheets.
    """
    print("Select service:")
    print("1. Add Collection To Google Sheets")
    print("2. Check Collections in Google Sheets")
    while True:
        choice = input("Enter 1 or 2: ")
        if choice in ['1', '2']:
            return int(choice)
        print("Invalid input.")

def main():
    service_choice = select_service()
    if service_choice == 1:
        query = input("Enter album name to search on Discogs: ")
        add_cd_to_sheets(query=query)
    elif service_choice == 2:
        query = input("Enter album name to check in Google Sheets: ")
        check_collection_for_cd(query=query)    

if __name__ == "__main__":
    # Example usage
    main()