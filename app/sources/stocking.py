"""
Stocking source - CDFW Fish Planting Schedule.

CDFW publishes a live, hatchery-maintained planting schedule here:
  https://nrm.dfg.ca.gov/FishPlants/PublicPlantSearch

It's an ASP.NET page rather than a clean JSON API, so we scrape the results
table. This module fetches recent plants for the counties we care about and
returns a flat list of records; matching them to specific waters happens in
main.py against each water's `cdfw_match` strings.

IMPORTANT - this is the piece most likely to need tuning once it runs against
the live site from your Mac. The exact query parameters and table markup can
change. The parser below reads columns by their header text (Date / Water /
County / Species) so it survives column reordering, but if CDFW returns nothing
or changes the page, `fetch_recent_plants` just returns [] and the dashboard
shows "no recent stocking data" rather than crashing. Verify the URL and the
`PARAMS` below against the live page and adjust as needed.

Returns records shaped like:
  {"county": "Tuolumne", "water": "Pinecrest Lake",
   "date": "2026-05-20", "species": "Rainbow Trout"}
"""

from datetime import datetime

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://nrm.dfg.ca.gov/FishPlants/PublicPlantSearch"

# Time frame for the search. On the live page this maps to a dropdown.
# TODO: confirm the value that means "recent / next few weeks" on the live form.
PARAMS = {"Params.PlantTimeFrame": "2"}

HEADERS = {"User-Agent": "cabin-fishing-conditions/0.1 (personal dashboard)"}


def _find_col(headers, *needles):
    """Return the index of the first header cell containing any needle."""
    for i, h in enumerate(headers):
        text = h.lower()
        if any(n in text for n in needles):
            return i
    return None


def _parse_date(raw):
    """Normalize a CDFW date string to YYYY-MM-DD; keep raw if it won't parse."""
    raw = (raw or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def _parse_table(html):
    soup = BeautifulSoup(html, "html.parser")
    records = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
        date_i = _find_col(header_cells, "date")
        water_i = _find_col(header_cells, "water")
        county_i = _find_col(header_cells, "county")
        species_i = _find_col(header_cells, "species", "fish")

        # Only treat this as a plant table if it has at least a water column.
        if water_i is None:
            continue

        for row in rows[1:]:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) <= water_i:
                continue
            records.append({
                "county": cells[county_i] if county_i is not None and len(cells) > county_i else "",
                "water": cells[water_i],
                "date": _parse_date(cells[date_i]) if date_i is not None and len(cells) > date_i else "",
                "species": cells[species_i] if species_i is not None and len(cells) > species_i else "",
            })

    return records


def fetch_recent_plants(counties):
    """Fetch recent plant records for the given counties. Returns [] on failure."""
    all_records = []
    for county in sorted(set(counties)):
        params = dict(PARAMS)
        # TODO: confirm the county filter param name/format on the live form.
        params["RegionCountyMappings"] = county
        try:
            resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            all_records.extend(_parse_table(resp.text))
        except Exception as exc:
            print(f"[stocking] county '{county}' failed: {exc}")
    return all_records
