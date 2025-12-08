"""
CD Collection Agent - Streamlit Application
A modern UI for managing your CD collection with Discogs integration
usage:
    streamlit run streamlit_app.py  
"""
import streamlit as st
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, Base, engine
from app.services import cd_service
from app import schemas
from app.utils.discogs import search_album, get_release_info
from app.agents.workflow import workflow
import json

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


# Main title
st.title("💿 CD Collection Agent")
st.markdown("---")

# Create tabs for different sections
tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Add CD", "🔍 Search", "🌐 Discogs Search", "📋 View All", "Chat"]) 

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
                    db = get_db()
                    cd_data = schemas.CDCreate(
                        title=title,
                        artist=artist,
                        year=year if year else None,
                        genre=genre if genre else None,
                        style=style if style else None
                    )
                    new_cd = cd_service.create_cd(db, cd_data)
                    st.success(f"✅ Successfully added '{new_cd.title}' by {new_cd.artist} (ID: {new_cd.id})")
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
                cds = cd_service.search_cds_by_title(db, search_value)
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
                cds = cd_service.search_cds_by_artist(db, search_value)
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
                # Prepare search parameters
                search_params = {"query": discogs_query, "limit": 10}
                
                # Add optional filters only if they're set
                if filter_format and filter_format != "Any":
                    search_params["release_format"] = filter_format
                if filter_country:
                    search_params["country"] = filter_country
                if filter_year != -1:  # -1 is the sentinel value for "not set"
                    search_params["year"] = filter_year
                
                results = search_album(**search_params)
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
                # Create columns: image, info, button
                col_img, col_info, col_btn = st.columns([1, 3, 1])

                with col_img:
                    # Display album cover image if available
                    images = result.get('images', [])
                    if images and len(images) > 0:
                        # Get the first image (usually the cover)
                        image_url = images[0].get("uri") if isinstance(images, list) else images.get("uri")
                        st.image(image_url, width=100)
                    else:
                        # Placeholder if no image available
                        st.write("🎵")

                with col_info:
                    url = result.get('url', '')
                    title_text = f"**{result.get('artist', 'Unknown')} - {result.get('title', 'Unknown')}**"
                    if url:
                        st.markdown(f"{title_text} | [View on Discogs]({url})")
                    else:
                        st.markdown(title_text)
                    details = f"{result.get('year', 'N/A')} | {result.get('country', 'N/A')}"
                    formats = result.get('formats', [])
                    if formats:
                        details += f" | {', '.join(formats) if isinstance(formats, list) else formats}"
                    st.caption(details)

                with col_btn:
                    # Use unique key for each button
                    if st.button("Add to Collection", key=f"add_discogs_{idx}"):
                        try:
                            # Get detailed release info
                            release_id = result.get('id')
                            with st.spinner("Fetching details..."):
                                release_info = get_release_info(release_id)

                            # Prepare CD data
                            cd_data = schemas.CDCreate(
                                title=release_info.get('title'),
                                artist=release_info.get('artist'),
                                year=release_info.get('year'),
                                genre=release_info.get('genres'),
                                style=release_info.get('styles'),
                                tracklist=release_info.get('tracklist'),
                                labels=release_info.get('labels'),
                                formats=release_info.get('formats'),
                                images=release_info.get('images'),
                                discogs_id=str(release_info.get('discogs_id'))
                            )

                            # Add to database
                            db = get_db()
                            new_cd = cd_service.create_cd(db, cd_data)
                            db.close()

                            st.success(f"✅ Added '{new_cd.title}' to collection!")
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
        all_cds = cd_service.get_all_cds(db)
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
                    
                    # Show additional details if available
                    if cd.tracklist:
                        st.write("**Tracklist:**")
                        st.json(cd.tracklist)
                    if cd.formats:
                        st.write("**Formats:**")
                        st.json(cd.formats)
        else:
            st.warning("No CDs in collection yet. Add some CDs to get started!")
    except Exception as e:
        st.error(f"Error loading CDs: {str(e)}")

#===== TAB 5: Chat with LLM =====
with tab5:
    st.title("Talk to the CD Collection Agent!")

    user_input = st.text_input("Enter your message:")

    if st.button("Send"):
        if user_input.strip():
            result = workflow.invoke({"user_input": user_input})
            st.markdown("### Agent Response:")
            st.write(result["model_output"])
# Footer
st.markdown("---")
st.caption("💿 CD Collection Agent - Built with Streamlit")
