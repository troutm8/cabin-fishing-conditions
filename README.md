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

- **CDFW stocking scraper** (`app/sources/stocking.py`) — verified against the
  live page on 2026-06-09. The single-GET query
  (`Params.PlantTimeFrame=1`) returned the full schedule (~2,100 rows), every
  row parsed with a valid date, and every `cdfw_match` needle in
  `waters.json` matched only its own water in the correct county. Six waters
  (Beardsley, Donnells, Phoenix Lake, New Hogan, Spicer, Utica) showed
  "No recent stocking data" because CDFW genuinely hadn't stocked them in the
  past year — not a scraper bug. Regression tests against captured live
  markup live in `tests/`; if CDFW changes the page layout they'll catch it.
- **Coordinates and drive times** in `waters.json` are approximate starting
  points.
- **Crowd reports** are a stub by design for v1.

## Tests

```bash
pip install pytest
python -m pytest tests/
```

The stocking tests run against `tests/fixtures/cdfw_sample.html`, real markup
captured from the CDFW schedule page, so they pass offline.

## Roadmap ideas (later)

- Wire a real crowd-reports source (local shop page or forum feed).
- Add live water conditions (USGS streamflow/temp, reservoir levels).
- Host it on a real server instead of running locally.
