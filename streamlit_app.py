"""
CD Collection Agent - Streamlit Application
A modern UI for managing your CD collection with Discogs integration
usage:
    streamlit run streamlit_app.py  
"""
import streamlit as st
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, Base, engine
from app import schemas
from app.services.spotify_service import SpotifyService

# ETL imports
from etl.importer import import_excel
from etl.normalizer import normalize_record, validate_records
from etl.api_fetcher import search_discogs, fetch_discogs_batch
from etl.merge import merge_records
from etl.queries import (
    search_cds_by_title,
    search_cds_by_artist,
    get_cd_by_id,
    get_all_cds,
    filter_cds,
)
from app.db.manager import insert_cds_batch

import json
import os
import uuid
import secrets
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TOKEN_PATH = "data/spotify_tokens.json"

# Initialize database
Base.metadata.create_all(bind=engine)

# Page configuration
st.set_page_config(
    page_title="CD Collection Agent",
    page_icon="💿",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .cd-card {
        background-color: #f0f0f0;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # Streamlit will handle session lifecycle


def format_cd_display(cd):
    """Format CD object for display"""
    return {
        "ID": cd.id,
        "Title": cd.title,
        "Artist": cd.artist,
        "Year": cd.year,
        "Genre": cd.genre,
        "Style": cd.style,
        "Discogs ID": cd.discogs_id
    }


def parse_spotify_items(data):
    """Parse Spotify recently played items into a DataFrame"""
    items = data.get('items', [])
    records = []
    for item in items:
        track = item.get('track', {})
        record = {
            'Artist': ', '.join([a.get('name', 'Unknown') for a in track.get('artists', [])]),
            'Track': track.get('name', 'Unknown'),
            'Duration': f"{int(track.get('duration_ms', 0) / 60000)}:{int((track.get('duration_ms', 0) / 1000) % 60):02d}",
            'Played At': item.get('played_at', 'Unknown'),
            'Album': track.get('album', {}).get('name', 'Unknown'),
            'Track Number': track.get('track_number', 0),
            'Album Year': track.get('album', {}).get('release_date', 'Unknown')[:4]
        }
        records.append(record)
    return pd.DataFrame(records)


# Main title
st.title("💿 CD Collection Agent")
st.markdown("---")

# Create tabs for different sections
tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Add CD", "🔍 Search", "🌐 Discogs Search", "📋 View All", "🎵 Spotify"]) 

# ===== TAB 1: Add New CD =====
with tab1:
    st.header("Add New CD")
    
    with st.form("add_cd_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Title*", placeholder="Enter CD title")
            artist = st.text_input("Artist*", placeholder="Enter artist name")
            year = st.number_input("Year", min_value=1900, max_value=2100, value=2024, step=1)
        
        with col2:
            genre = st.text_input("Genre", placeholder="e.g., Rock, Jazz, Classical")
            style = st.text_input("Style", placeholder="e.g., Alternative Rock, Bebop")
        
        submit_button = st.form_submit_button("Add CD to Collection")
        
        if submit_button:
            if not title or not artist:
                st.error("Please provide both Title and Artist")
            else:
                try:
                    # Normalize and create CD record
                    cd_data = schemas.CDCreate(
                        title=title,
                        artist=artist,
                        year=year if year else None,
                        genre=genre if genre else None,
                        style=style if style else None
                    )
                    
                    # Insert to DB
                    db = get_db()
                    inserted = insert_cds_batch(db, [cd_data.dict()])
                    
                    if inserted > 0:
                        st.success(f"✅ Successfully added '{title}' by {artist}")
                    else:
                        st.error("Failed to add CD to collection")
                    
                    db.close()
                except Exception as e:
                    st.error(f"Error adding CD: {str(e)}")

# ===== TAB 2: Search CD =====
with tab2:
    st.header("Search CD Collection")
    
    search_type = st.selectbox("Search by:", ["ID", "Title", "Artist"])
    
    if search_type == "ID":
        search_value = st.number_input("Enter CD ID", min_value=1, step=1)
        search_button = st.button("Search by ID")
        
        if search_button:
            try:
                db = get_db()
                cd = cd_service.get_cd_by_id(db, int(search_value))
                db.close()
                
                if cd:
                    st.success("Found CD:")
                    st.json(format_cd_display(cd))
                else:
                    st.warning("No CD found with that ID")
            except Exception as e:
                st.error(f"Error searching: {str(e)}")
    
    elif search_type == "Title":
        search_value = st.text_input("Enter title (partial match supported)")
        search_button = st.button("Search by Title")
        
        if search_button and search_value:
            try:
                db = get_db()
                cds = search_cds_by_title(db, search_value)
                db.close()
                
                if cds:
                    st.success(f"Found {len(cds)} CD(s):")
                    for cd in cds:
                        with st.expander(f"{cd.title} - {cd.artist} ({cd.year})"):
                            st.json(format_cd_display(cd))
                else:
                    st.warning("No CDs found matching that title")
            except Exception as e:
                st.error(f"Error searching: {str(e)}")
    
    else:  # Artist
        search_value = st.text_input("Enter artist name (partial match supported)")
        search_button = st.button("Search by Artist")
        
        if search_button and search_value:
            try:
                db = get_db()
                cds = search_cds_by_artist(db, search_value)
                db.close()
                
                if cds:
                    st.success(f"Found {len(cds)} CD(s):")
                    for cd in cds:
                        with st.expander(f"{cd.title} - {cd.artist} ({cd.year})"):
                            st.json(format_cd_display(cd))
                else:
                    st.warning("No CDs found by that artist")
            except Exception as e:
                st.error(f"Error searching: {str(e)}")

# ===== TAB 3: Discogs Search =====
with tab3:
    st.header("Search Discogs Database")
    st.markdown("Search for albums on Discogs and add them to your collection")

    with st.expander("🔍 Advanced Search Filters", expanded=False):
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            filter_format = st.selectbox(
                "Format",
                options=["Any", "CD", "Vinyl", "Cassette", "DVD", "Blu-ray", "Other"],
                index=0,
                help="Select the format type to filter results"
            )
        with col_filter2:
            filter_country = st.text_input("Country", placeholder="e.g., US, UK, Japan", help="Filter by country of release")
        with col_filter3:
            filter_year = st.number_input(
                "Year (or -1 for any)", 
                min_value=-1, 
                max_value=2100, 
                value=-1, 
                step=1, 
                help="Enter specific year or -1 for any year"
            )

    # Initialize session state for search results if not exists
    if 'discogs_results' not in st.session_state:
        st.session_state.discogs_results = None

    discogs_query = st.text_input("Search for album or artist", placeholder="e.g., Pink Floyd The Wall")
    discogs_search_button = st.button("Search Discogs")

    # Perform search and save to session state
    if discogs_search_button and discogs_query:
        with st.spinner("Searching Discogs..."):
            try:
                # Parse query
                parts = discogs_query.split(" ", 1)
                artist = parts[0]
                title = parts[1] if len(parts) > 1 else ""
                
                # Use ETL API fetcher
                results = search_discogs(artist, title, limit=10)
                st.session_state.discogs_results = results
                
                if not results:
                    st.info("No results found on Discogs")
            except Exception as e:
                st.error(f"Error searching Discogs: {str(e)}")
                st.session_state.discogs_results = None

    # Display results from session state
    if st.session_state.discogs_results:
        results = st.session_state.discogs_results
        st.success(f"Found {len(results)} result(s)")

        for idx, result in enumerate(results):
            with st.container():
                # Create columns: info, button
                col_info, col_btn = st.columns([3, 1])

                with col_info:
                    title_text = f"**{result.get('artist', 'Unknown')} - {result.get('title', 'Unknown')}**"
                    st.markdown(title_text)
                    
                    details = f"{result.get('year', 'N/A')} | {result.get('country', 'N/A')}"
                    formats = result.get('formats', [])
                    if formats:
                        details += f" | {', '.join(formats) if isinstance(formats, list) else formats}"
                    st.caption(details)
                    
                    # Show genres/styles
                    genres = result.get('genres', [])
                    styles = result.get('styles', [])
                    if genres or styles:
                        genre_text = f"📚 {', '.join(genres + styles)}" if genres or styles else ""
                        st.caption(genre_text)

                with col_btn:
                    # Use unique key for each button
                    if st.button("Add to Collection", key=f"add_discogs_{idx}"):
                        try:
                            # Prepare CD data from Discogs result
                            cd_data = schemas.CDCreate(
                                title=result.get('title'),
                                artist=result.get('artist'),
                                year=result.get('year'),
                                genre=" / ".join(result.get('genres', [])) if result.get('genres') else None,
                                style=" / ".join(result.get('styles', [])) if result.get('styles') else None,
                                formats=" / ".join(result.get('formats', [])) if result.get('formats') else None,
                                discogs_id=str(result.get('id'))
                            )

                            # Add to database
                            db = get_db()
                            inserted = insert_cds_batch(db, [cd_data.dict()])
                            db.close()

                            if inserted > 0:
                                st.success(f"✅ Added '{result.get('title')}' to collection!")
                            else:
                                st.error("Failed to add CD")
                        except Exception as e:
                            st.error(f"Error adding from Discogs: {str(e)}")

                st.markdown("---")

# ===== TAB 4: View All CDs =====
with tab4:
    st.header("All CDs in Collection")
    
    if st.button("Refresh List"):
        st.rerun()
    
    try:
        db = get_db()
        all_cds = get_all_cds(db)
        db.close()
        
        if all_cds:
            st.info(f"Total CDs in collection: {len(all_cds)}")
            
            # Display in a table-like format
            for cd in all_cds:
                with st.expander(f"🎵 {cd.title} - {cd.artist} ({cd.year if cd.year else 'N/A'})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**ID:** {cd.id}")
                        st.write(f"**Title:** {cd.title}")
                        st.write(f"**Artist:** {cd.artist}")
                        st.write(f"**Year:** {cd.year if cd.year else 'N/A'}")
                    
                    with col2:
                        st.write(f"**Genre:** {cd.genre if cd.genre else 'N/A'}")
                        st.write(f"**Style:** {cd.style if cd.style else 'N/A'}")
                        if cd.discogs_id:
                            st.write(f"**Discogs ID:** {cd.discogs_id}")
        else:
            st.warning("No CDs in collection yet. Add some CDs to get started!")
    except Exception as e:
        st.error(f"Error loading CDs: {str(e)}")

# ===== TAB 6: Spotify =====
with tab5:
    st.header("🎵 Spotify Integration")
    
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    redirect = os.getenv("SPOTIFY_REDIRECT_URI")

    if not client_id or not redirect:
        st.warning("Spotify credentials not configured.")
        st.info("""
        Please set these environment variables:
        - SPOTIFY_CLIENT_ID
        - SPOTIFY_REDIRECT_URI (should be: http://127.0.0.1:8501/ or http://localhost:8501/)
        
        **Important:** The SPOTIFY_REDIRECT_URI in your Spotify app settings MUST match exactly what you set here.
        Go to https://developer.spotify.com/dashboard and update your app's redirect URI.
        """)
    else:
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        service = SpotifyService(client_id, redirect, TOKEN_PATH)
        
        verifier_file = "data/.code_verifier"

        # Display current redirect URI for debugging
        with st.expander("🔧 Debug Info"):
            st.code(f"Redirect URI: {redirect}", language="text")
            st.code(f"Current URL: {st.query_params}", language="text")

        # Generate code verifier once and store it persistently
        if not os.path.exists(verifier_file):
            # PKCE requires code verifier to be between 43 and 128 characters
            # secrets.token_urlsafe(64) generates a string of approx 85 chars
            code_verifier = secrets.token_urlsafe(64)
            with open(verifier_file, "w") as f:
                f.write(code_verifier)
            st.session_state.code_verifier = code_verifier
        else:
            # Load from file
            with open(verifier_file, "r") as f:
                saved_verifier = f.read().strip()

            # Auto-fix: if the saved verifier is too short, regenerate it
            if len(saved_verifier) < 43:
                code_verifier = secrets.token_urlsafe(64)
                with open(verifier_file, "w") as f:
                    f.write(code_verifier)
                st.session_state.code_verifier = code_verifier
                # Clear any existing query params to avoid processing the old code with new verifier
                st.query_params.clear() 
            else:
                st.session_state.code_verifier = saved_verifier

        auth_url = service.build_auth_url(st.session_state.code_verifier)
        st.markdown(f"[🔐 Login with Spotify]({auth_url})")
        st.caption("Click the link above to authenticate with Spotify")

        code = st.query_params.get("code")
        if code:
            st.info("Processing Spotify callback...")
            try:
                # Ensure we have the correct code verifier
                if not os.path.exists(verifier_file):
                    st.error("❌ Code verifier not found. Please click the login link again.")
                else:
                    with open(verifier_file, "r") as f:
                        code_verifier = f.read().strip()
                    
                    if not code_verifier:
                        st.error("❌ Code verifier is empty. Please click the login link again.")
                    else:
                        st.info(f"Using code verifier of length: {len(code_verifier)}")
                        tokens = service.exchange_code_for_tokens(code, code_verifier)
                        
                        # Check if we got valid tokens
                        if tokens and "access_token" in tokens:
                            st.success("✅ Spotify authenticated successfully!")
                            st.info("You can now load your Spotify history below.")
                            # Clean up the code from URL by clearing query params
                            st.query_params.clear()
                            # Clean up stored verifier
                            try:
                                os.remove(verifier_file)
                            except:
                                pass
                        else:
                            st.error(f"❌ Authentication failed: {tokens}")
                            st.info("Please try logging in again.")
            except Exception as e:
                st.error(f"❌ Authentication failed: {str(e)}")
                st.info("""
                **Troubleshooting:**
                1. Make sure SPOTIFY_REDIRECT_URI matches exactly in your Spotify app settings
                2. Check that your Spotify Client ID and Secret are correct
                3. Try logging in again
                """)

        if st.button("Load recent history"):
            try:
                data = service.get_recent_history(limit=50)
                if not data or 'items' not in data:
                    st.warning("No recent history data available.")
                else:
                    df = parse_spotify_items(data)
                    if len(df) > 0:
                        st.dataframe(df, use_container_width=True)
                        df.to_parquet("data/spotify_history.parquet")
                        st.success(f"✅ Loaded {len(df)} tracks from Spotify history")
                    else:
                        st.info("No tracks found in recent history.")
            except Exception as e:
                st.error(f"Error loading Spotify history: {str(e)}")
                st.info("Make sure you've authenticated and have recent listening history.")


# Footer
st.markdown("---")
st.caption("💿 CD Collection Agent - Built with Streamlit")
