import asyncio
import os
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter
from engines.predictor import predictor

router = APIRouter(tags=["Sports"])

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "eaf9d7fefamsh9d8be23de5950a3p12a...")
RAPIDAPI_HOST = "mmaapi.p.rapidapi.com"

LIVE_CACHE = {
    "football": {"live": [], "upcoming": [], "finished": []},
    "ufc": {"live": [], "upcoming": [], "finished": []},
    "f1": [],
    "meta": {
        "last_update": None,
        "last_error": None,
        "worker_running": False,
        "update_count": 0,
    },
}

async def fetch_ufc(client):
    url = f"https://{RAPIDAPI_HOST}/events"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    try:
        r = await client.get(url, headers=headers, timeout=10.0)
        if r.status_code != 200:
            return {"live": [], "upcoming": [], "finished": []}
        
        events = r.json() or []
        upcoming, finished = [], []

        for ev in events[:5]:
            event_name = ev.get("name", "UFC Event")
            date = ev.get("date", "TBD")
            
            pred = predictor.predict_match(home_form=2.2, away_form=2.0, h2h=1.0)
            
            item = {
                "event": event_name,
                "fighter_a": ev.get("fighter_a", "Fighter 1"),
                "fighter_b": ev.get("fighter_b", "Fighter 2"),
                "date": date,
                "time": "22:00",
                "status": "upcoming",
                "home_prob": pred["home_prob"],
                "away_prob": pred["away_prob"],
                "home_odd": pred["home_odd"],
                "away_odd": pred["away_odd"],
                "score": "VS"
            }
            upcoming.append(item)

        return {"live": [], "upcoming": upcoming, "finished": finished}
    except Exception:
        return {"live": [], "upcoming": [], "finished": []}

async def update_sports_data_periodically():
    LIVE_CACHE["meta"]["worker_running"] = True
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}) as client:
        while True:
            try:
                LIVE_CACHE["ufc"] = await fetch_ufc(client)
                LIVE_CACHE["meta"]["last_update"] = datetime.now(timezone.utc).isoformat()
                LIVE_CACHE["meta"]["update_count"] += 1
            except Exception as e:
                LIVE_CACHE["meta"]["last_error"] = str(e)
            await asyncio.sleep(60)

@router.get("/live")
def get_live_sports():
    return {"status": "success", "data": LIVE_CACHE}
