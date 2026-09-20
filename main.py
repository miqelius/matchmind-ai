import asyncio
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers.sports import router as sports_router, update_sports_data_periodically

load_dotenv()

app = FastAPI(title="MatchMind AI Hub", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sports_router, prefix="/api/sports")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_sports_data_periodically())

@app.get("/")
def read_root():
    return FileResponse("index.html")
