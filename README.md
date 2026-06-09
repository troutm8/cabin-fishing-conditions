# cabin-fishing-conditions

A small personal dashboard that shows fishing conditions for the spots within a
2-hour drive of Koda's Place (the cabin near Twain Harte, CA).

It's a read-only page: one card per water, grouped by water type, showing
**weather** (top priority), **stocking** (CDFW fish plants), and the
**latest fish report** for the water. A thin FastAPI backend pulls and caches
the data so the page stays fast and the upstream APIs don't get throttled.

## What it shows

- **Weather** - current temp, conditions, wind, and today's high/low
  (via [Open-Meteo](https://open-meteo.com), free, no API key).
- **Stocking** - most recent and next CDFW trout/catfish plant for each water
  (scraped from the CDFW Fish Planting Schedule).
- **Fish reports** - the latest report for each water from
  [NorCal Fish Reports](https://www.norcalfishreports.com), with date, author
  (local shops/agencies like Ebbetts Pass Sporting Goods and the Don Pedro
  Recreation Agency), and a link to the full report.

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
app/sources/crowd.py    NorCal Fish Reports scraper (latest report per water)
static/                 The dashboard page (index.html, styles.css, app.js)
data/                   Cache files written at runtime (git-ignored)
```

## Adding or changing spots

Edit `config/waters.json`. Each entry needs a `lat`/`lon` (for weather), a
`county` (for the stocking lookup), a `type` (which group it falls under), an
approximate `drive_minutes`, and `cdfw_match` - a list of substrings used to
match the water against names in the CDFW schedule. Optionally add
`ncfr_path`, the water's page path on
[norcalfishreports.com](https://www.norcalfishreports.com) (e.g.
`/lakes/22/don-pedro-reservoir.php`, find it via their Spots index) to get
fish reports; waters without one show "No reports for this water".
Coordinates and drive times in the starter file are approximate; adjust them
to taste.

## Caching

The cache decouples page refreshes from upstream calls. Defaults (in
`app/main.py`): weather refreshes every 3 hours, stocking once a day, fish
reports every 6 hours. Delete a file in `data/` to force that source to
refetch on the next load.

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
- **Fish reports** (`app/sources/crowd.py`) come from norcalfishreports.com
  per-water pages (robots.txt allows crawling; verified 2026-06-09). Coverage
  is real but uneven: busy waters (Don Pedro, Lake Alpine, Spicer) get fresh
  reports, quiet ones can go years between reports - the card shows the
  report date (with year when it's old) so stale news reads as stale. Six
  waters have no page on the site at all (Lyons, Beardsley, Donnells,
  Phoenix, Utica, SF Stanislaus) and show "No reports for this water".

## Tests

```bash
pip install pytest
python -m pytest tests/
```

The scraper tests run against fixtures in `tests/fixtures/` - real markup
captured from the CDFW schedule and norcalfishreports.com pages - so they
pass offline.

## Roadmap ideas (later)

- Add live water conditions (USGS streamflow/temp, reservoir levels).
- Host it on a real server instead of running locally.
