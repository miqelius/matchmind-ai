import asyncio
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter
from engines.predictor import predictor

router = APIRouter(tags=["Sports"])

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

TOP_LEAGUES = [
    {"id": "4328", "name": "Premier League"},
    {"id": "4335", "name": "La Liga"},
    {"id": "4332", "name": "Serie A"},
    {"id": "4331", "name": "Bundesliga"},
]

async def fetch_football(client):
    upcoming_list = []
    finished_list = []
    for league in TOP_LEAGUES:
        try:
            url_next = f"https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id={league['id']}"
            r_next = await client.get(url_next, timeout=8.0)
            if r_next.status_code == 200:
                events = (r_next.json() or {}).get("events") or []
                for e in events[:3]:
                    home = e.get("strHomeTeam") or "Team A"
                    away = e.get("strAwayTeam") or "Team B"
                    
                    pred = predictor.predict_match(home_form=2.5, away_form=1.8, h2h=1.1)
                    
                    upcoming_list.append({
                        "home": home,
                        "away": away,
                        "league": league["name"],
                        "date": e.get("dateEvent", "TBD"),
                        "time": e.get("strTime", "00:00"),
                        "status": "upcoming",
                        "home_prob": pred["home_prob"],
                        "away_prob": pred["away_prob"],
                        "home_odd": pred["home_odd"],
                        "away_odd": pred["away_odd"],
                        "score": "vs"
                    })

            url_past = f"https://www.thesportsdb.com/api/v1/json/3/eventspastleague.php?id={league['id']}"
            r_past = await client.get(url_past, timeout=8.0)
            if r_past.status_code == 200:
                past_events = (r_past.json() or {}).get("events") or []
                for e in past_events[:3]:
                    home = e.get("strHomeTeam") or "Team A"
                    away = e.get("strAwayTeam") or "Team B"
                    home_score = e.get("intHomeScore") if e.get("intHomeScore") is not None else "0"
                    away_score = e.get("intAwayScore") if e.get("intAwayScore") is not None else "0"
                    finished_list.append({
                        "home": home,
                        "away": away,
                        "league": league["name"],
                        "date": e.get("dateEvent", "TBD"),
                        "time": e.get("strTime", "00:00"),
                        "status": "finished",
                        "home_prob": 50,
                        "away_prob": 50,
                        "home_odd": 1.90,
                        "away_odd": 1.90,
                        "score": f"{home_score} : {away_score}"
                    })
        except Exception:
            pass
    return {"live": [], "upcoming": upcoming_list, "finished": finished_list}

async def fetch_ufc(client):
    try:
        r = await client.get("https://ufcapi.aristotle.me/api/events?limit=5", timeout=10.0)
        if r.status_code != 200:
            raise Exception("UFC API error")
        events = r.json()
        upcoming, finished = [], []

        for ev in events:
            event_name = ev.get("name", "UFC Event")
            date = ev.get("date", "TBD")
            is_finished = ev.get("status") == "finished"

            for fight in ev.get("fights", [])[:4]:
                fa = fight.get("fighter_a", {}).get("name", "Fighter 1")
                fb = fight.get("fighter_b", {}).get("name", "Fighter 2")
                
                pred = predictor.predict_match(home_form=2.2, away_form=2.0, h2h=1.0)
                
                item = {
                    "event": event_name,
                    "fighter_a": fa,
                    "fighter_b": fb,
                    "date": date,
                    "time": "22:00",
                    "status": "finished" if is_finished else "upcoming",
                    "home_prob": pred["home_prob"],
                    "away_prob": pred["away_prob"],
                    "home_odd": pred["home_odd"],
                    "away_odd": pred["away_odd"],
                    "score": fight.get("result", "VS") if is_finished else "VS"
                }
                if is_finished:
                    finished.append(item)
                else:
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
