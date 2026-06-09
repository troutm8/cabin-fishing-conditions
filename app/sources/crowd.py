"""
Crowd reports - NorCal Fish Reports (https://www.norcalfishreports.com).

Part of the fishreports.com network. Most of our waters have a dedicated page
(e.g. /lakes/22/don-pedro-reservoir.php) with a "Latest Fish Reports" table:
Date | Report (linked title + teaser) | Author. The authors are exactly the
"crowd" we want - local shops and agencies like Ebbetts Pass Sporting Goods
and the Don Pedro Recreation Agency. robots.txt allows crawling (checked
2026-06-09).

Each water that has a page carries its path in waters.json as "ncfr_path".
Waters without a path, or whose page lists no reports, get
{"status": "none"}. Quiet waters can go years between reports, so the date is
part of the payload and the UI decides how to present staleness.

Returned shape, keyed by water id:
  {"lake_don_pedro": {"status": "report", "date": "2026-06-01",
                      "title": "Fishing days at Don Pedro just hit different",
                      "author": "Don Pedro Recreation Agency",
                      "url": "https://www.norcalfishreports.com/fish_reports/..."},
   "lyons_reservoir": {"status": "none"}, ...}
"""

from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.norcalfishreports.com"

HEADERS = {"User-Agent": "cabin-fishing-conditions/0.1 (personal dashboard)"}


def _parse_date(raw):
    """'6-1-2026' -> '2026-06-01'; '' for anything unparseable."""
    try:
        return datetime.strptime((raw or "").strip(), "%m-%d-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _parse_reports(html):
    """
    Pull rows out of the "Latest Fish Reports" table on a water page.
    The page also has a fish-plants table with the same styling, so locate
    the section by its heading rather than taking the first table.
    """
    soup = BeautifulSoup(html, "html.parser")

    heading = soup.find(
        lambda tag: tag.name == "h3" and "latest fish reports" in tag.get_text(strip=True).lower()
    )
    if heading is None:
        return []
    table = heading.find_next("table")
    if table is None:
        return []

    reports = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        link = cells[1].find("a")
        if link is None:  # header row has no link
            continue
        reports.append({
            "date": _parse_date(cells[0].get_text(strip=True)),
            "title": link.get_text(strip=True),
            "author": cells[2].get_text(strip=True),
            "url": urljoin(BASE_URL, link.get("href", "")),
        })
    return reports


def fetch_one(path):
    """Latest report from one water page, or None if the page lists none."""
    resp = requests.get(urljoin(BASE_URL, path), headers=HEADERS, timeout=20)
    resp.raise_for_status()
    reports = _parse_reports(resp.text)
    if not reports:
        return None
    # Rows are listed newest-first; sort anyway in case that ever changes.
    reports.sort(key=lambda r: r["date"], reverse=True)
    return reports[0]


def fetch_all(waters):
    """Fetch the latest report for every water. One failure doesn't sink the rest."""
    out = {}
    for water in waters:
        path = water.get("ncfr_path")
        if not path:
            out[water["id"]] = {"status": "none"}
            continue
        try:
            report = fetch_one(path)
        except Exception as exc:
            print(f"[crowd] {water['id']} failed: {exc}")
            report = None
        if report is None:
            out[water["id"]] = {"status": "none"}
        else:
            out[water["id"]] = {"status": "report", **report}
    return out
