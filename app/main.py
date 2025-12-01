from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from .db.database import Base, engine
from .routers import cd

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(cd.router)

@app.get("/", response_class=HTMLResponse)
def read_root():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>CD Collection Agent</title>
            <style>
                body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .container { display: flex; flex-direction: column; gap: 20px; }
                .card { border: 1px solid #ccc; padding: 20px; border-radius: 8px; }
                button { padding: 10px 20px; cursor: pointer; }
                input { padding: 8px; margin-right: 10px; }
                #results { background: #f0f0f0; padding: 10px; border-radius: 4px; white-space: pre-wrap; }
            </style>
        </head>
        <body>
            <h1>CD Collection Agent</h1>
            <div class="container">
                
                <div class="card">
                    <h2>Add New CD</h2>
                    <input type="text" id="title" placeholder="Title">
                    <input type="text" id="artist" placeholder="Artist">
                    <input type="number" id="year" placeholder="Year">
                    <button onclick="addCD()">Add CD</button>
                </div>

                <div class="card">
                    <h2>Get CD by ID</h2>
                    <input type="number" id="cdId" placeholder="CD ID">
                    <button onclick="getCD()">Get CD</button>
                </div>

                <div class="card">
                    <h2>List All CDs</h2>
                    <button onclick="listCDs()">List All CDs</button>
                </div>

                <div id="results">Results will appear here...</div>
            </div>

            <script>
                async function addCD() {
                    const title = document.getElementById('title').value;
                    const artist = document.getElementById('artist').value;
                    const year = document.getElementById('year').value;
                    
                    const response = await fetch('/cds/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title, artist, year: parseInt(year) })
                    });
                    const data = await response.json();
                    document.getElementById('results').textContent = JSON.stringify(data, null, 2);
                }

                async function getCD() {
                    const id = document.getElementById('cdId').value;
                    const response = await fetch(`/cds/${id}`);
                    const data = await response.json();
                    document.getElementById('results').textContent = JSON.stringify(data, null, 2);
                }

                async function listCDs() {
                    const response = await fetch('/cds/');
                    const data = await response.json();
                    document.getElementById('results').textContent = JSON.stringify(data, null, 2);
                }
            </script>
        </body>
    </html>
    """
