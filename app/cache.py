"""
Dead-simple file cache.

Each source (weather, stocking, ...) gets one JSON file under data/.
A cached file stores {"fetched_at": <unix ts>, "data": <payload>}.

`get_or_refresh` is the only function the rest of the app needs:
  - if the cached copy is younger than `ttl_seconds`, return it
  - otherwise call `fetch_fn()` to get fresh data, save it, return it
  - if the fetch fails, fall back to the stale cache (better than nothing),
    or to `default` if there is no cache at all

This is what keeps us from hammering the upstream APIs: the page can be
refreshed as often as you like, but we only actually call out to Open-Meteo
or CDFW when the cache for that source has expired.
"""

import json
import os
import time

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _path(name):
    return os.path.join(DATA_DIR, f"{name}.json")


def load(name):
    """Return {"fetched_at": ts, "data": ...} or None if missing/unreadable."""
    try:
        with open(_path(name), "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save(name, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_path(name), "w") as f:
        json.dump({"fetched_at": time.time(), "data": data}, f, indent=2)


def age_seconds(name):
    """How old the cached copy is, in seconds, or None if there is none."""
    cached = load(name)
    if not cached:
        return None
    return time.time() - cached.get("fetched_at", 0)


def get_or_refresh(name, ttl_seconds, fetch_fn, default=None):
    cached = load(name)
    if cached and (time.time() - cached.get("fetched_at", 0)) < ttl_seconds:
        return cached["data"]

    try:
        fresh = fetch_fn()
        save(name, fresh)
        return fresh
    except Exception as exc:  # network error, parse error, etc.
        print(f"[cache] refresh of '{name}' failed: {exc}")
        if cached:
            return cached["data"]  # serve stale rather than nothing
        return default
