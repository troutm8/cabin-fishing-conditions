"""
Regression tests for the CDFW stocking scraper.

The fixture (tests/fixtures/cdfw_sample.html) is unmodified markup captured
from the live schedule page on 2026-06-09, trimmed to six representative rows.
The full capture that day parsed to 2,115 records with zero unparseable dates,
and every cdfw_match needle in config/waters.json matched only its own water
in the correct county. If CDFW changes the page layout, these tests are the
canary.
"""

import json
import os

from app.main import match_stocking
from app.sources.stocking import _clean_water, _parse_table, _parse_week

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "cdfw_sample.html")
CONFIG = os.path.join(os.path.dirname(__file__), "..", "config", "waters.json")


def load_fixture_records():
    with open(FIXTURE) as f:
        return _parse_table(f.read())


def test_parse_week_takes_start_of_range():
    assert _parse_week("6/15/2025-6/21/2025") == "2025-06-15"
    assert _parse_week("  6/15/2025-6/21/2025  ") == "2025-06-15"
    assert _parse_week("") == ""
    assert _parse_week("not a date") == ""


def test_clean_water_strips_map_link_noise():
    assert _clean_water("Pinecrest Lake\n View Water Body in Map") == "Pinecrest Lake"
    assert _clean_water("  Mosquito   Lake, Lower ") == "Mosquito Lake, Lower"


def test_parse_table_on_captured_live_markup():
    records = load_fixture_records()
    assert len(records) == 6
    assert {
        "county": "Tuolumne",
        "water": "Pinecrest Lake",
        "date": "2025-06-22",
        "species": "Trout",
    } in records
    # Multi-county rows keep the full county string.
    melones = next(r for r in records if r["water"] == "New Melones Reservoir")
    assert melones["county"] == "Calaveras, Tuolumne"
    # Every date normalizes to YYYY-MM-DD.
    assert all(len(r["date"]) == 10 and r["date"][4] == "-" for r in records)


def test_match_stocking_finds_last_plant():
    records = load_fixture_records()
    water = {"cdfw_match": ["Pinecrest"]}
    result = match_stocking(water, records)
    assert result == {
        "last": {"date": "2025-06-22", "species": "Trout"},
        "next": None,
    }


def test_match_stocking_future_plant_goes_to_next():
    # The Carson River row in the fixture is week-of 2026-06-14; relative to
    # the 2026-06-09 capture date that is an upcoming plant. Guard the
    # assertion so the test stays meaningful if run after that week passes.
    from datetime import date

    records = load_fixture_records()
    result = match_stocking({"cdfw_match": ["Carson River East"]}, records)
    if date.today().isoformat() < "2026-06-14":
        assert result["next"] == {"date": "2026-06-14", "species": "Trout"}
        assert result["last"] is None
    else:
        assert result["last"] == {"date": "2026-06-14", "species": "Trout"}


def test_match_stocking_no_match_returns_none():
    records = load_fixture_records()
    assert match_stocking({"cdfw_match": ["Beardsley"]}, records) is None


def test_config_needles_do_not_cross_match():
    """No water's needles may match a fixture row that belongs to a
    different water (e.g. 'Union Res' must not match 'Clear Creek')."""
    with open(CONFIG) as f:
        waters = json.load(f)["waters"]
    records = load_fixture_records()
    expected = {
        "pinecrest_lake": {"Pinecrest Lake"},
        "sf_stanislaus": {"Stanislaus River South Fork"},
        "new_melones": {"New Melones Reservoir"},
    }
    for w in waters:
        needles = [n.lower() for n in w["cdfw_match"]]
        hit = {r["water"] for r in records
               if any(n in r["water"].lower() for n in needles)}
        assert hit == expected.get(w["id"], set()), (
            f"{w['id']} matched unexpected waters: {hit}"
        )
