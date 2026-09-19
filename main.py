import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from routers.sports import router as sports_router, update_sports_data_periodically
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # აპლიკაციის სტარტზე ფონური ამოცანის გაშვება, რომელიც მონაცემებს ქაჩავს
    bg_task = asyncio.create_task(update_sports_data_periodically())
    yield
    bg_task.cancel()

app = FastAPI(
    title="MatchMind AI - Sports Intelligence API",
    description="Professional sports analytics, predictive modeling, and live data intelligence platform.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS კონფიგურაცია
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# სტატიკური ფაილების მიბმა
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return {"status": "operational", "service": "MatchMind AI API"}

@app.get("/api/system/status")
async def system_status():
    return {
        "status": "operational", 
        "service": "MatchMind AI",
        "cpu": "Normal", 
        "memory": "Optimal", 
        "database": "Connected"
    }

# სპორტული როუტერის მიერთება
app.include_router(sports_router, prefix="/api/sports", tags=["Sports Intelligence"])
