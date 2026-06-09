"""
Regression tests for the NorCal Fish Reports crowd source.

The fixture (tests/fixtures/ncfr_sample.html) is unmodified markup captured
from the Don Pedro Reservoir page on 2026-06-09, trimmed to the "Latest Fish
Plants" and "Latest Fish Reports" sections. The plants table is kept on
purpose: it uses the same table styling, so the parser must find the reports
section by its heading. If the site changes layout, these tests are the
canary.
"""

import os

from app.sources.crowd import _parse_date, _parse_reports, fetch_all

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "ncfr_sample.html")


def load_fixture():
    with open(FIXTURE) as f:
        return f.read()


def test_parse_date():
    assert _parse_date("6-1-2026") == "2026-06-01"
    assert _parse_date("12-25-2025") == "2025-12-25"
    assert _parse_date("") == ""
    assert _parse_date("not a date") == ""


def test_parse_reports_on_captured_live_markup():
    reports = _parse_reports(load_fixture())
    assert len(reports) == 5
    newest = reports[0]
    assert newest == {
        "date": "2026-06-01",
        "title": "Fishing days at Don Pedro just hit different",
        "author": "Don Pedro Recreation Agency",
        "url": "https://www.norcalfishreports.com/fish_reports/238499/"
               "fishing-days-at-don-pedro-just-hit-different.php",
    }
    # The fish-plants table must not leak into the results: every record
    # comes from the reports table, with a date and an absolute report URL.
    assert all(r["url"].startswith("https://www.norcalfishreports.com/fish_reports/")
               for r in reports)
    assert all(len(r["date"]) == 10 for r in reports)


def test_parse_reports_without_section_returns_empty():
    assert _parse_reports("<html><body><h3>Nothing here</h3></body></html>") == []


def test_fetch_all_skips_waters_without_a_page():
    # No ncfr_path means no network call and an explicit "none" status.
    out = fetch_all([{"id": "lyons_reservoir"}])
    assert out == {"lyons_reservoir": {"status": "none"}}
