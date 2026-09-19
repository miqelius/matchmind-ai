import asyncio
import os
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter
from engines.predictor import predictor

router = APIRouter(tags=["Sports"])

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "mmaapi.p.rapidapi.com")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")

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

LEAGUE_IDS = [39, 140, 135, 78]

async def fetch_football(client):
    upcoming_list = []
    finished_list = []
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    
    for league_id in LEAGUE_IDS:
        try:
            url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season=2026&next=3"
            r = await client.get(url, headers=headers, timeout=8.0)
            if r.status_code == 200:
                data = r.json().get("response", [])
                for match in data:
                    teams = match.get("teams", {})
                    fixture = match.get("fixture", {})
                    league_info = match.get("league", {})
                    
                    home = teams.get("home", {}).get("name", "Team A")
                    away = teams.get("away", {}).get("name", "Team B")
                    
                    pred = predictor.predict_match(home_form=2.5, away_form=1.8, h2h=1.1)
                    
                    date_raw = fixture.get("date", "")
                    date_str = date_raw.split("T")[0] if "T" in date_raw else "TBD"
                    time_str = date_raw.split("T")[1][:5] if "T" in date_raw else "00:00"

                    upcoming_list.append({
                        "home": home,
                        "away": away,
                        "league": league_info.get("name", "Top League"),
                        "date": date_str,
                        "time": time_str,
                        "status": "upcoming",
                        "home_prob": pred["home_prob"],
                        "away_prob": pred["away_prob"],
                        "home_odd": pred["home_odd"],
                        "away_odd": pred["away_odd"],
                        "score": "vs"
                    })
        except Exception:
            pass

    return {"live": [], "upcoming": upcoming_list, "finished": finished_list}

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

async def fetch_f1(client):
    try:
        r = await client.get("https://api.openf1.org/v1/sessions?year=2026", timeout=8.0)
        if r.status_code != 200 or not r.json():
            return []
        latest = r.json()[-1]
        sk = latest.get("session_key")
        r2 = await client.get(f"https://api.openf1.org/v1/position?session_key={sk}", timeout=8.0)
        pos = r2.json() if r2.status_code == 200 else []
        r3 = await client.get(f"https://api.openf1.org/v1/drivers?session_key={sk}", timeout=8.0)
        drivers = {d["driver_number"]: d for d in (r3.json() if r3.status_code == 200 else [])}

        return [{
            "pos": p.get("position"),
            "driver": drivers.get(p.get("driver_number"), {}).get("full_name", "?"),
            "team": drivers.get(p.get("driver_number"), {}).get("team_name", "?"),
            "session": latest.get("session_name"),
            "circuit": latest.get("circuit_short_name")
        } for p in pos[:10]]
    except Exception:
        return []

async def update_sports_data_periodically():
    LIVE_CACHE["meta"]["worker_running"] = True
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}) as client:
        while True:
            try:
                LIVE_CACHE["football"] = await fetch_football(client)
                LIVE_CACHE["ufc"] = await fetch_ufc(client)
                LIVE_CACHE["f1"] = await fetch_f1(client)
                LIVE_CACHE["meta"]["last_update"] = datetime.now(timezone.utc).isoformat()
                LIVE_CACHE["meta"]["update_count"] += 1
            except Exception as e:
                LIVE_CACHE["meta"]["last_error"] = str(e)
            await asyncio.sleep(60)

@router.get("/live")
def get_live_sports():
    return {"status": "success", "data": LIVE_CACHE}
