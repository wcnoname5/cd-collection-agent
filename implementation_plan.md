# Implementation Plan - Discogs Integration

I will implement keyword searching via the Discogs API on the main page.

## User Review Required

> [!IMPORTANT]
> I will be adding a new section to the main page for searching Discogs. When a user selects a result, it will be added to the local database.

- **UI Changes**: A new "Search Discogs" card will be added to the main dashboard.
- **Backend Changes**: A new API endpoint `/cds/search` (or similar) will be created to proxy requests to Discogs.

## Proposed Changes

### Backend

#### [NEW] `app/routers/discogs.py`
- Create a new router for Discogs related operations.
- Implement `GET /discogs/search` endpoint.
    - Accepts `query` parameter.
    - Uses `app.utils.discogs.album_lookup_agent` or `search_album` to fetch results.
    - Returns a list of candidates.

#### `app/main.py`
- Include the new `discogs` router.
- Update the HTML template to include the search UI.

### Frontend (in `app/main.py` HTML)

- Add a new "Search Discogs" card.
- Add an input field for the search query.
- Add a "Search" button.
- Add a results area to display the search results.
- Add "Add to Collection" buttons next to each result.

## Verification Plan

### Automated Tests
- I will run `pytest` to ensure no regressions.
- I may add a simple test for the new endpoint if possible (mocking Discogs).

### Manual Verification
- Start the server with `uv run uvicorn app.main:app --reload`.
- Open the browser to `http://127.0.0.1:8000`.
- Enter a search term (e.g., "The Dark Side of the Moon").
- Verify results appear.
- Click "Add" on a result and verify it appears in the "List All CDs" section.
