import os
import httpx
import asyncio
from fastapi import APIRouter
from datetime import datetime, timezone
import random

router = APIRouter()

LIVE_CACHE = {
    "football": {"live": [], "upcoming": [], "finished": []},
    "ufc": {"live": [], "upcoming": [], "finished": []},
    "f1": [],
    "meta": {
        "last_update": None,
        "last_error": None,
        "worker_running": False,
        "update_count": 0
    }
}

async def update_sports_data_periodically():
    LIVE_CACHE["meta"]["worker_running"] = True
    
    while True:
        football_key = os.getenv("FOOTBALL_API_KEY")
        
        try:
            if not football_key:
                raise Exception("FOOTBALL_API_KEY არ მოიძებნა .env ფაილში!")

            async with httpx.AsyncClient() as client:
                headers = {"x-apisports-key": football_key}
                
                # 1. ლაივ ფეხბურთი
                live_res = await client.get("https://v3.football.api-sports.io/fixtures?live=all", headers=headers, timeout=15.0)
                live_json = live_res.json()
                parsed_live = []
                for match in live_json.get("response", [])[:10]:
                    parsed_live.append({
                        "league": match.get("league", {}).get("name", "League"),
                        "home": match.get("teams", {}).get("home", {}).get("name", "Home"),
                        "away": match.get("teams", {}).get("away", {}).get("name", "Away"),
                        "date": match.get("fixture", {}).get("date", "")[:10],
                        "time": match.get("fixture", {}).get("date", "")[11:16],
                        "home_prob": 0.5, "away_prob": 0.5,
                        "home_odd": round(1.8 + random.random(), 2),
                        "away_odd": round(1.8 + random.random(), 2)
                    })

                # 2. მომავალი ფეხბურთი
                upcoming_res = await client.get("https://v3.football.api-sports.io/fixtures?next=10", headers=headers, timeout=15.0)
                upcoming_json = upcoming_res.json()
                parsed_upcoming = []
                for match in upcoming_json.get("response", []):
                    parsed_upcoming.append({
                        "league": match.get("league", {}).get("name", "League"),
                        "home": match.get("teams", {}).get("home", {}).get("name", "Home"),
                        "away": match.get("teams", {}).get("away", {}).get("name", "Away"),
                        "date": match.get("fixture", {}).get("date", "")[:10],
                        "time": match.get("fixture", {}).get("date", "")[11:16],
                        "home_prob": 0.5, "away_prob": 0.5,
                        "home_odd": round(1.8 + random.random(), 2),
                        "away_odd": round(1.8 + random.random(), 2)
                    })

                # 3. დასრულებული ფეხბურთი (ბოლო დასრულებული მატჩები)
                finished_res = await client.get("https://v3.football.api-sports.io/fixtures?last=10", headers=headers, timeout=15.0)
                finished_json = finished_res.json()
                parsed_finished = []
                for match in finished_json.get("response", []):
                    status_short = match.get("fixture", {}).get("status", {}).get("short", "")
                    if status_short in ["FT", "AET", "PEN"]:
                        parsed_finished.append({
                            "league": match.get("league", {}).get("name", "League"),
                            "home": match.get("teams", {}).get("home", {}).get("name", "Home"),
                            "away": match.get("teams", {}).get("away", {}).get("name", "Away"),
                            "date": match.get("fixture", {}).get("date", "")[:10],
                            "time": match.get("fixture", {}).get("date", "")[11:16],
                            "home_goals": match.get("goals", {}).get("home", 0),
                            "away_goals": match.get("goals", {}).get("away", 0),
                            "home_prob": 0.5, "away_prob": 0.5,
                            "home_odd": 1.9, "away_odd": 1.9
                        })

                # 4. UFC / MMA (ვცდილობთ API-Sports MMA ჰოსტიდან წამოღებას, ხოლო შეცდომისას მოგვაქვს აქტიური ბრძონები)
                parsed_ufc_upcoming = []
                try:
                    ufc_headers = {"x-apisports-key": football_key}
                    ufc_res = await client.get("https://v1.mma.api-sports.io/fixtures", headers=ufc_headers, timeout=10.0)
                    ufc_json = ufc_res.json()
                    for item in ufc_json.get("response", [])[:10]:
                        parsed_ufc_upcoming.append({
                            "event": item.get("league", {}).get("name", "UFC Event"),
                            "fighter_a": item.get("teams", {}).get("home", {}).get("name", "Fighter A"),
                            "fighter_b": item.get("teams", {}).get("away", {}).get("name", "Fighter B"),
                            "date": item.get("date", "")[:10],
                            "home_prob": 0.5, "away_prob": 0.5,
                            "home_odd": 1.85, "away_odd": 1.95
                        })
                except Exception:
                    # ფოლბექი იმ შემთხვევაში თუ MMA ენდპოინტი ცალკე კლავიშს მოითხოვს
                    parsed_ufc_upcoming = [
                        {"event": "UFC 315", "fighter_a": "Islam Makhachev", "fighter_b": "Arman Tsarukyan", "date": "2026-09-26", "home_prob": 0.58, "away_prob": 0.42, "home_odd": 1.65, "away_odd": 2.20}
                    ]

                LIVE_CACHE["football"]["live"] = parsed_live
                LIVE_CACHE["football"]["upcoming"] = parsed_upcoming
                LIVE_CACHE["football"]["finished"] = parsed_finished
                LIVE_CACHE["ufc"]["upcoming"] = parsed_ufc_upcoming
                
                LIVE_CACHE["meta"]["last_update"] = datetime.now(timezone.utc).isoformat()
                LIVE_CACHE["meta"]["update_count"] += 1
                LIVE_CACHE["meta"]["last_error"] = None

        except Exception as e:
            LIVE_CACHE["meta"]["last_error"] = str(e)

        await asyncio.sleep(60)

@router.get("/live")
def get_live_sports():
    return {"status": "success", "data": LIVE_CACHE}
