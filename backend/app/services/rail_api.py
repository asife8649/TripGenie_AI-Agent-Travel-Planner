"""Optional Indian Railways data provider (RapidAPI 'IRCTC1'-style endpoints).

There is NO free official IRCTC fare/schedule API. If you subscribe to a
RapidAPI listing, put the key in backend/.env:

    RAIL_API_KEY=your_rapidapi_key
    RAIL_API_HOST=irctc1.p.rapidapi.com     # change if you use another listing

If the key is missing, or the provider fails, TripGenie falls back to Google
Routes (stations + times when Google has the schedule) and to a clearly labelled
distance-based fare estimate. Field names differ between listings, so parsing
below is deliberately tolerant; test it once with your own key.
"""
import os
import re
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

from .fare_estimator import format_minutes
from .station_codes import get_station

load_dotenv()

RAIL_API_KEY = os.getenv("RAIL_API_KEY")
RAIL_API_HOST = os.getenv("RAIL_API_HOST", "irctc1.p.rapidapi.com")
TIMEOUT = 25


def is_configured() -> bool:
    return bool(RAIL_API_KEY)


def _get(path: str, params: dict):
    response = requests.get(
        f"https://{RAIL_API_HOST}{path}",
        params=params,
        headers={"X-RapidAPI-Key": RAIL_API_KEY, "X-RapidAPI-Host": RAIL_API_HOST},
        timeout=TIMEOUT,
    )
    if response.status_code >= 400:
        print(f"RAIL API {path} -> {response.status_code}: {response.text[:300]}")
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _pick(item: dict, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None


def resolve_station(city: str):
    """Return (code, name) from the local table, else ask the provider."""
    local = get_station(city)
    if local:
        return local
    if not is_configured():
        return None
    data = _get("/api/v1/searchStation", {"query": city})
    rows = (data or {}).get("data") if isinstance(data, dict) else None
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        code = _pick(rows[0], "code", "station_code")
        name = _pick(rows[0], "name", "station_name") or city
        if code:
            return str(code), str(name)
    return None


def _parse_duration_minutes(value):
    if value is None:
        return None
    text = str(value).strip()
    match = re.match(r"^(\d{1,3}):(\d{2})$", text)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    match = re.match(r"^(?:(\d+)\s*h\w*)?\s*(?:(\d+)\s*m\w*)?$", text, re.I)
    if match and (match.group(1) or match.group(2)):
        return int(match.group(1) or 0) * 60 + int(match.group(2) or 0)
    if text.isdigit():
        return int(text)
    return None


def _combine(date_text: str, time_text):
    if not time_text:
        return None
    match = re.match(r"^(\d{1,2}):(\d{2})", str(time_text))
    if not match:
        return None
    try:
        base = datetime.fromisoformat(str(date_text)[:10])
    except ValueError:
        return None
    return base.replace(hour=int(match.group(1)), minute=int(match.group(2)))


def get_fares(train_no, from_code, to_code):
    data = _get("/api/v2/getFare", {
        "trainNo": train_no, "fromStationCode": from_code, "toStationCode": to_code,
    })
    payload = (data or {}).get("data") if isinstance(data, dict) else None
    general = (payload or {}).get("general") if isinstance(payload, dict) else None
    fares = []
    for row in general or []:
        if not isinstance(row, dict):
            continue
        cls = _pick(row, "classType", "class", "class_type")
        try:
            fare = float(_pick(row, "fare", "total_fare", "amount"))
        except (TypeError, ValueError):
            continue
        if cls and fare > 0:
            fares.append({"class": str(cls), "fare": fare})
    return fares


def search_trains(source_city, destination_city, date_value, travelers, limit=5, fare_lookups=5):
    """Return normalised train journeys with live schedule and (when available) fares."""
    if not is_configured():
        return []
    src = resolve_station(source_city)
    dst = resolve_station(destination_city)
    if not src or not dst:
        print(f"Rail API: station code not found for {source_city} / {destination_city}")
        return []

    data = _get("/api/v3/trainBetweenStations", {
        "fromStationCode": src[0], "toStationCode": dst[0], "dateOfJourney": str(date_value)[:10],
    })
    rows = (data or {}).get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []

    journeys = []
    for index, row in enumerate(rows[:limit]):
        if not isinstance(row, dict):
            continue
        number = _pick(row, "train_number", "train_no", "trainNumber")
        name = _pick(row, "train_name", "trainName")
        dep_text = _pick(row, "from_std", "departure_time", "from_time", "dep_time")
        arr_text = _pick(row, "to_sta", "arrival_time", "to_time", "arr_time")
        duration = _parse_duration_minutes(_pick(row, "duration", "travel_time"))
        departure = _combine(date_value, dep_text)
        arrival = departure + timedelta(minutes=duration) if departure and duration else _combine(date_value, arr_text)
        classes = _pick(row, "class_type", "classes", "available_classes") or []
        if isinstance(classes, str):
            classes = [c.strip() for c in classes.split(",") if c.strip()]

        fares = []
        if number and index < fare_lookups:
            fares = get_fares(number, src[0], dst[0])

        cheapest = min((f["fare"] for f in fares), default=None)
        journeys.append({
            "transport_type": "train",
            "vehicle_types": ["TRAIN"],
            "from_name": _pick(row, "from_station_name") or src[1],
            "to_name": _pick(row, "to_station_name") or dst[1],
            "from_code": src[0],
            "to_code": dst[0],
            "departure_time": departure.strftime("%Y-%m-%dT%H:%M:%S") if departure else None,
            "arrival_time": arrival.strftime("%Y-%m-%dT%H:%M:%S") if arrival else None,
            "duration_minutes": duration,
            "travel_time": format_minutes(duration),
            "operator": name,
            "vehicle_number": str(number) if number else None,
            "available_classes": [str(c) for c in classes] if isinstance(classes, list) else [],
            "class_fares": fares,
            "price_per_person": cheapest,
            "currency": "INR" if cheapest is not None else None,
            "fare_available": cheapest is not None,
            "price_type": "live" if cheapest is not None else "unavailable",
            "price_source": f"Indian Railways data via {RAIL_API_HOST}",
            "provider": "Indian Railways API",
        })
    return journeys
