"""
Stocking source - CDFW Fish Planting Schedule.

CDFW publishes a hatchery-maintained schedule at:
  https://nrm.dfg.ca.gov/FishPlants/PublicPlantSearch

The default page is a single GET that returns ~2000 rows (every CA plant for
roughly the last year + the next two weeks) inside one HTML <table>. We fetch
it once, parse the table, and let main.py do per-water matching against each
water's cdfw_match substrings.

Headers on the live page: "Week of Plant" | "Water Name" | "Counties" | "Species"
Dates are weekly ranges like "6/8/2025-6/14/2025"; we keep the start of the
range and normalize to YYYY-MM-DD.

Verified against the live page on 2026-06-09: the GET below returned ~2,100
rows in a single table, all dates parsed, and the headers matched the names
_parse_table looks for. Regression tests with captured markup: tests/.

Returned records:
  {"county": "Tuolumne", "water": "Pinecrest Lake",
   "date": "2025-06-08", "species": "Trout"}
"""

import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://nrm.dfg.ca.gov/fishplants/publicplantsearch"

# PlantTimeFrame: 1 = All (past year + 2 wks future) -- what we want.
#                 2 = Current-Future only (~2 weeks).
#                 3 = Past Plants only.
PARAMS = {"Params.PlantTimeFrame": "1"}

HEADERS = {"User-Agent": "cabin-fishing-conditions/0.1 (personal dashboard)"}

# The water-name cell wraps a "View Water Body in Map" link whose text
# gets concatenated to the name when we read with get_text(); strip it.
LINK_NOISE = "View Water Body in Map"


def _find_col(headers, *needles):
    """Return the index of the first header cell containing any needle."""
    for i, h in enumerate(headers):
        text = h.lower()
        if any(n in text for n in needles):
            return i
    return None


def _parse_week(raw):
    """Take the start of a 'M/D/YYYY-M/D/YYYY' range and return YYYY-MM-DD."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    head = raw.split("-", 1)[0].strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(head, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _clean_water(text):
    return re.sub(r"\s+", " ", (text or "").replace(LINK_NOISE, "")).strip()


def _parse_table(html):
    soup = BeautifulSoup(html, "html.parser")
    records = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
        date_i = _find_col(header_cells, "week of plant", "date")
        water_i = _find_col(header_cells, "water")
        county_i = _find_col(header_cells, "count")  # matches "Counties"
        species_i = _find_col(header_cells, "species", "fish")

        if water_i is None or date_i is None:
            continue

        for row in rows[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) <= max(water_i, date_i):
                continue
            records.append({
                "county": cells[county_i] if county_i is not None and len(cells) > county_i else "",
                "water": _clean_water(cells[water_i]),
                "date": _parse_week(cells[date_i]),
                "species": cells[species_i] if species_i is not None and len(cells) > species_i else "",
            })

    return records


def fetch_recent_plants():
    """Fetch the full state-wide schedule in one request. Returns [] on failure."""
    try:
        resp = requests.get(SEARCH_URL, params=PARAMS, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return _parse_table(resp.text)
    except Exception as exc:
        print(f"[stocking] fetch failed: {exc}")
        return []
