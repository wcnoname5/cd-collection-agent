# CD Collection Agent

A Streamlit-based application for managing your CD collection with Discogs integration, search capabilities, and a modern user interface.

## Features

- 📀 **Add CDs**: Manually add CDs to your collection with detailed metadata
- 🔍 **Search**: Search your collection by ID, title, or artist
- 🌐 **Discogs Integration**: Search Discogs database and add albums directly to your collection
- 📋 **View Collection**: Browse your entire CD collection with detailed information
- 💾 **SQLite Database**: Persistent storage of your collection

## Quick Start

```bash
# Install dependencies
uv sync

# Run the Streamlit application
streamlit run streamlit_app.py
```

The application will open in your browser at `http://localhost:8501`

## Requirements

- Python >= 3.13
- Streamlit
- SQLAlchemy
- Discogs API token (set in `.env` file)

## Project Structure

- `streamlit_app.py` - Main Streamlit application
- `app/db/` - Database models and configuration
- `app/routers/` - Currently archieved, can be build later when flip back into FastAPI
- `app/services/` - Business logic and CRUD operations
- `app/utils/` - Utility functions (Discogs integration, etc.)
- `data/` - SQLite database storage

## Archive Note

Previous FastAPI files have been archived with `.archive` extension for reference.

