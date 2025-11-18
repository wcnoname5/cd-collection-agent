import uuid
from tools.discogs_API_functions import format_cd_info, search_album, pick_best_match, get_release_info
from tools.gsheets_API_functions import (
    init_gsheets_client, open_or_create_sheet, get_or_create_worksheet, append_cd_metadata, is_duplicate, search_collection
) 

# state storage for long-running calls
PENDING_ADDITIONS = {}


def add_cd_to_sheets_long_running(query: str, auto_confirm: bool = False):
    """
    Long-running version of add_cd_to_sheets.
    Step 1: Search Discogs and ask the user to pick a release.
    """
    # Create a ticket for storing state
    ticket = str(uuid.uuid4())

    # Step 1 — search Discogs
    search_results = search_album(query, limit=5)
    if not search_results:
        return {
            "status": "no_results",
            "message": "No results found on Discogs."
        }

    # Candidate selection
    candidates = pick_best_match(query, search_results)

    # Auto-select fast path
    if auto_confirm and candidates:
        chosen = candidates[0]

        # Store only what is needed for next step
        PENDING_ADDITIONS[ticket] = {
            "step": "await_duplicate_check",
            "selected_release": chosen
        }

        return {
            "status": "need_user_confirmation",
            "ticket": ticket,
            "message": f"Auto-selected: {format_cd_info(chosen)}\n\nAdd this CD to your collection?",
            "options": ["yes", "no"]
        }

    # Otherwise ask user to choose from candidates
    display_list = [
        {
            "id": c["id"],
            "summary": format_cd_info(c)
        }
        for c in candidates
    ]

    # store state for step 2 (waiting for user to select release)
    PENDING_ADDITIONS[ticket] = {
        "step": "await_user_pick",
        "candidates": candidates
    }

    return {
        "status": "awaiting_user_choice",
        "ticket": ticket,
        "message": "Select the correct CD from the list.",
        "choices": display_list
    }

def resume_add_cd_to_sheets(ticket: str, user_input: dict):
    """
    Continue the add-CD process based on user's response.
    """
    if ticket not in PENDING_ADDITIONS:
        return {"status": "error", "message": "Unknown ticket."}

    state = PENDING_ADDITIONS[ticket]
    step = state["step"]

    # -------------------------
    # Step 2: User picked a release
    # -------------------------
    if step == "await_user_pick":
        release_id = user_input.get("release_id")
        if release_id is None:
            return {"status": "error", "message": "No release selected."}

        chosen = next(
            (c for c in state["candidates"] if c["id"] == release_id),
            None
        )
        if chosen is None:
            return {"status": "error", "message": "Invalid release ID."}

        # Now we go to duplicate-check step
        PENDING_ADDITIONS[ticket] = {
            "step": "await_duplicate_check",
            "selected_release": chosen
        }

        return {
            "status": "need_user_confirmation",
            "ticket": ticket,
            "message": f"You selected: {format_cd_info(chosen)}\n\nAdd to collection?",
            "options": ["yes", "no"]
        }

    # -------------------------
    # Step 3: User confirmed adding
    # -------------------------
    if step == "await_duplicate_check":
        confirm = user_input.get("confirm", "").lower()
        if confirm not in ["yes", "y"]:
            del PENDING_ADDITIONS[ticket]
            return {"status": "cancelled", "message": "Cancelled by user."}

        selected = state["selected_release"]

        # Fetch full metadata
        selected_metadata = get_release_info(selected["id"])

        # Open Sheets
        client = init_gsheets_client()
        sheet = open_or_create_sheet(client, "My CD Collection")
        ws = get_or_create_worksheet(
            sheet,
            "CDs",
            headers=[
                "title", "artist", "year", "country", "genre",
                "style", "tracklist", "labels", "formats",
                "images", "discogs_id",
            ]
        )

        cd_info = format_cd_info(selected_metadata)

        # Duplicate check
        if is_duplicate(ws, selected_metadata):
            del PENDING_ADDITIONS[ticket]
            return {
                "status": "duplicate",
                "message": f"'{cd_info}' is already in the collection."
            }

        # Add to sheet
        append_cd_metadata(ws, selected_metadata)

        del PENDING_ADDITIONS[ticket]
        return {
            "status": "completed",
            "message": f"Added: {cd_info}"
        }

    return {"status": "error", "message": "Invalid state."}


