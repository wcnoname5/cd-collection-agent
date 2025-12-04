from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from .db.database import Base, engine
from .routers import cd, discogs
import os

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(cd.router)
app.include_router(discogs.router)

@app.get("/")
def read_root():
    """Serve the main UI HTML file"""
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "UI.html")
    return FileResponse(ui_path)
