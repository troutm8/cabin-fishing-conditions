"""
Cabin fishing conditions - FastAPI backend.

Serves two things:
  GET /                -> the dashboard page (static/index.html)
  GET /api/conditions  -> combined JSON the page renders

The combined endpoint pulls three sources through the cache layer
(weather + stocking + crowd reports), matches stocking records to waters,
and groups everything by water type. Refreshing the page is cheap because the
cache only calls upstream when a source's TTL has expired.

Run it with:  uvicorn app.main:app --reload
Then open:    http://127.0.0.1:8000
"""

import json
import os
from datetime import date, datetime

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import cache
from app.sources import crowd, stocking, weather

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "waters.json")

# How long each source's cache stays fresh, in seconds.
WEATHER_TTL = 3 * 60 * 60      # 3 hours
STOCKING_TTL = 24 * 60 * 60    # 1 day
CROWD_TTL = 6 * 60 * 60        # 6 hours

# Display order, labels, and icons for the water-type groups.
GROUPS = [
    {"type": "trout_lake_108", "label": "Highway 108 trout lakes", "icon": "ti-fish"},
    {"type": "valley_reservoir", "label": "Valley reservoirs", "icon": "ti-droplet"},
    {"type": "alpine_lake", "label": "Alpine lakes", "icon": "ti-mountain"},
    {"type": "river", "label": "Rivers", "icon": "ti-ripple"},
]


def load_waters():
    with open(CONFIG_PATH) as f:
        return json.load(f)["waters"]


def match_stocking(water, plants):
    """
    Find stocking records that belong to this water (by cdfw_match substrings)
    and summarize them into a most-recent ("last") and next-upcoming ("next").
    """
    needles = [n.lower() for n in water.get("cdfw_match", [])]
    matches = [
        p for p in plants
        if any(n in p["water"].lower() for n in needles)
    ]
    if not matches:
        return None

    today = date.today().isoformat()
    dated = [p for p in matches if len(p["date"]) == 10 and p["date"][4] == "-"]
    past = sorted([p for p in dated if p["date"] <= today], key=lambda p: p["date"])
    future = sorted([p for p in dated if p["date"] > today], key=lambda p: p["date"])

    result = {"last": None, "next": None}
    if past:
        result["last"] = {"date": past[-1]["date"], "species": past[-1]["species"]}
    if future:
        result["next"] = {"date": future[0]["date"], "species": future[0]["species"]}
    # If nothing had a parseable date, at least surface that a plant is listed.
    if not past and not future and matches:
        result["last"] = {"date": matches[0]["date"] or "scheduled",
                          "species": matches[0]["species"]}
    return result


def build_conditions():
    waters = load_waters()

    weather_by_id = cache.get_or_refresh(
        "weather", WEATHER_TTL, lambda: weather.fetch_all(waters), default={}
    )
    plants = cache.get_or_refresh(
        "stocking", STOCKING_TTL, lambda: stocking.fetch_recent_plants(), default=[]
    )
    crowd_by_id = cache.get_or_refresh(
        "crowd", CROWD_TTL, lambda: crowd.fetch_all(waters), default={}
    )

    groups = []
    for group in GROUPS:
        members = [w for w in waters if w["type"] == group["type"]]
        if not members:
            continue
        members.sort(key=lambda w: w["drive_minutes"])
        groups.append({
            "type": group["type"],
            "label": group["label"],
            "icon": group["icon"],
            "waters": [{
                "id": w["id"],
                "name": w["name"],
                "lat": w["lat"],
                "lon": w["lon"],
                "drive_minutes": w["drive_minutes"],
                "notes": w["notes"],
                "weather": weather_by_id.get(w["id"]),
                "stocking": match_stocking(w, plants),
                "crowd": crowd_by_id.get(w["id"]),
            } for w in members],
        })

    weather_age = cache.age_seconds("weather")
    return {
        "updated": datetime.now().isoformat(timespec="minutes"),
        "weather_age_minutes": round(weather_age / 60) if weather_age is not None else None,
        "groups": groups,
    }


app = FastAPI(title="Cabin fishing conditions")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/conditions")
def conditions():
    return build_conditions()
