# cabin-fishing-conditions

A small personal dashboard that shows fishing conditions for the spots within a
2-hour drive of Koda's Place (the cabin near Twain Harte, CA).

It's a read-only page: one card per water, grouped by water type, showing
**weather** (top priority), **stocking** (CDFW fish plants), and a
**crowd-reports** placeholder for now. A thin FastAPI backend pulls and caches
the data so the page stays fast and the upstream APIs don't get throttled.

## What it shows

- **Weather** - current temp, conditions, wind, and today's high/low
  (via [Open-Meteo](https://open-meteo.com), free, no API key).
- **Stocking** - most recent and next CDFW trout/catfish plant for each water
  (scraped from the CDFW Fish Planting Schedule).
- **Crowd reports** - placeholder slot for v1; wire a real source in later.

Spots are grouped into Highway 108 trout lakes, valley reservoirs, alpine
lakes, and rivers, and sorted by drive time within each group.

## Quick start

```bash
# from the repo root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000

## Project layout

```
config/waters.json      The master list of spots (edit this to add/remove waters)
app/main.py             FastAPI app: serves the page + /api/conditions
app/cache.py            File cache with per-source TTL
app/sources/weather.py  Open-Meteo weather
app/sources/stocking.py CDFW plant-schedule scraper
app/sources/crowd.py    Crowd-reports placeholder
static/                 The dashboard page (index.html, styles.css, app.js)
data/                   Cache files written at runtime (git-ignored)
```

## Adding or changing spots

Edit `config/waters.json`. Each entry needs a `lat`/`lon` (for weather), a
`county` (for the stocking lookup), a `type` (which group it falls under), an
approximate `drive_minutes`, and `cdfw_match` - a list of substrings used to
match the water against names in the CDFW schedule. Coordinates and drive times
in the starter file are approximate; adjust them to taste.

## Caching

The cache decouples page refreshes from upstream calls. Defaults (in
`app/main.py`): weather refreshes every 3 hours, stocking once a day. Delete a
file in `data/` to force that source to refetch on the next load.

## Things to verify / known rough edges

- **CDFW stocking scraper** (`app/sources/stocking.py`) is the piece most likely
  to need tuning. The schedule is an ASP.NET page, not a clean API, so the
  query parameters and county filter are marked with `TODO` and should be
  confirmed against the live page. Until that's dialed in, cards simply show
  "No recent stocking data" rather than erroring.
- **Coordinates and drive times** in `waters.json` are approximate starting
  points.
- **Crowd reports** are a stub by design for v1.

## Roadmap ideas (later)

- Wire a real crowd-reports source (local shop page or forum feed).
- Add live water conditions (USGS streamflow/temp, reservoir levels).
- Host it on a real server instead of running locally.
