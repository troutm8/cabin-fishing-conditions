"""
Weather source - Open-Meteo (https://open-meteo.com).

Why Open-Meteo: it's free, needs no API key, and returns current conditions
plus today's high/low in a single GET per location. One less credential to manage.

`fetch_all(waters)` returns a dict keyed by water id:
  { "pinecrest_lake": {"temp": 56, "condition": "Partly cloudy",
                        "icon": "ti-cloud", "wind": "5 mph NW",
                        "high": 62, "low": 38}, ... }
"""

import requests

BASE_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes -> (human label, Tabler icon name).
# Reference: https://open-meteo.com/en/docs (Weather variable documentation)
WMO_CODES = {
    0: ("Clear", "ti-sun"),
    1: ("Mainly clear", "ti-sun"),
    2: ("Partly cloudy", "ti-cloud"),
    3: ("Overcast", "ti-cloud"),
    45: ("Fog", "ti-fog"),
    48: ("Freezing fog", "ti-fog"),
    51: ("Light drizzle", "ti-cloud-rain"),
    53: ("Drizzle", "ti-cloud-rain"),
    55: ("Heavy drizzle", "ti-cloud-rain"),
    56: ("Freezing drizzle", "ti-cloud-rain"),
    57: ("Freezing drizzle", "ti-cloud-rain"),
    61: ("Light rain", "ti-cloud-rain"),
    63: ("Rain", "ti-cloud-rain"),
    65: ("Heavy rain", "ti-cloud-rain"),
    66: ("Freezing rain", "ti-cloud-rain"),
    67: ("Freezing rain", "ti-cloud-rain"),
    71: ("Light snow", "ti-snowflake"),
    73: ("Snow", "ti-snowflake"),
    75: ("Heavy snow", "ti-snowflake"),
    77: ("Snow grains", "ti-snowflake"),
    80: ("Rain showers", "ti-cloud-rain"),
    81: ("Rain showers", "ti-cloud-rain"),
    82: ("Heavy showers", "ti-cloud-rain"),
    85: ("Snow showers", "ti-snowflake"),
    86: ("Snow showers", "ti-snowflake"),
    95: ("Thunderstorm", "ti-bolt"),
    96: ("Thunderstorm", "ti-bolt"),
    99: ("Thunderstorm", "ti-bolt"),
}

COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _compass(degrees):
    """Turn a wind bearing in degrees into an 8-point compass label."""
    return COMPASS[round(degrees / 45) % 8]


def fetch_one(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,wind_speed_10m,wind_direction_10m",
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "America/Los_Angeles",
        "forecast_days": 1,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    payload = resp.json()

    current = payload["current"]
    daily = payload["daily"]
    label, icon = WMO_CODES.get(current["weather_code"], ("Unknown", "ti-cloud"))

    return {
        "temp": round(current["temperature_2m"]),
        "condition": label,
        "icon": icon,
        "wind": f"{round(current['wind_speed_10m'])} mph {_compass(current['wind_direction_10m'])}",
        "high": round(daily["temperature_2m_max"][0]),
        "low": round(daily["temperature_2m_min"][0]),
    }


def fetch_all(waters):
    """Fetch weather for every water. One failure doesn't sink the rest."""
    out = {}
    for water in waters:
        try:
            out[water["id"]] = fetch_one(water["lat"], water["lon"])
        except Exception as exc:
            print(f"[weather] {water['id']} failed: {exc}")
            out[water["id"]] = None
    return out
