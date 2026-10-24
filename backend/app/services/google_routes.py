import os
import re
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

from .fare_estimator import format_minutes

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
IST = timezone(timedelta(hours=5, minutes=30))

BUS_TYPES = {"BUS", "INTERCITY_BUS", "TROLLEYBUS", "SHARE_TAXI"}
TRAIN_TYPES = {
    "TRAIN", "COMMUTER_TRAIN", "LONG_DISTANCE_TRAIN", "HIGH_SPEED_TRAIN",
    "HEAVY_RAIL", "RAIL", "SUBWAY", "METRO_RAIL", "TRAM", "LIGHT_RAIL",
}


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def _duration_seconds(value):
    try:
        return float(str(value).rstrip("s"))
    except (TypeError, ValueError):
        return None


def _duration_to_text(value):
    seconds = _duration_seconds(value)
    if seconds is None:
        return None
    return format_minutes(round(seconds / 60))


def _to_ist_iso(value):
    """Google returns UTC timestamps; show Indian local time (no tz suffix)."""
    if not value:
        return None
    text = re.sub(r"\.\d+", "", str(value)).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(IST)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _money_value(money):
    if not isinstance(money, dict):
        return None, None
    units = money.get("units")
    nanos = money.get("nanos", 0)
    currency = money.get("currencyCode")
    try:
        if units is None:
            return None, currency
        return float(units) + (float(nanos or 0) / 1_000_000_000), currency
    except (TypeError, ValueError):
        return None, currency


def _classify_transport(vehicle_types):
    types = {str(x).upper() for x in vehicle_types}
    has_bus = bool(types & BUS_TYPES)
    has_train = bool(types & TRAIN_TYPES)
    if has_bus and has_train:
        return "mixed_public_transit"
    if has_train:
        return "train"
    if has_bus:
        return "bus"
    return "public_transit"


def _parse_segments(route):
    segments = []
    for leg in route.get("legs", []) or []:
        for step in leg.get("steps", []) or []:
            details = step.get("transitDetails")
            if not details:
                continue
            stops = details.get("stopDetails") or {}
            line = details.get("transitLine") or {}
            vehicle = line.get("vehicle") or {}
            agencies = line.get("agencies") or []
            agency = agencies[0].get("name") if agencies and isinstance(agencies[0], dict) else None
            vehicle_name = (vehicle.get("name") or {}).get("text") if isinstance(vehicle.get("name"), dict) else None
            segments.append({
                "from_name": (stops.get("departureStop") or {}).get("name"),
                "to_name": (stops.get("arrivalStop") or {}).get("name"),
                "departure_time": _to_ist_iso(stops.get("departureTime")),
                "arrival_time": _to_ist_iso(stops.get("arrivalTime")),
                "line_name": line.get("name"),
                "line_short": line.get("nameShort"),
                "vehicle_type": str(vehicle.get("type") or "").upper() or None,
                "vehicle_name": vehicle_name,
                "operator": agency,
                "headsign": details.get("headsign"),
                "stop_count": details.get("stopCount"),
            })
    return segments


def _extract_vehicle_types(route):
    values = []
    for seg in _parse_segments(route):
        vt = seg.get("vehicle_type")
        if vt and vt not in values:
            values.append(vt)
    return values


def _headers(field_mask):
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": field_mask,
    }


# ------------------------------------------------------------------
# transit options (train / bus) with stations and clock times
# ------------------------------------------------------------------
def get_transit_options(
    source: str,
    destination: str,
    travelers: int = 1,
    allowed_mode: str | None = None,
    departure_time: str | None = None,
    limit: int = 3,
):
    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY is not set in .env")

    mode = (allowed_mode or "").lower().strip()
    body = {
        "origin": {"address": source},
        "destination": {"address": destination},
        "travelMode": "TRANSIT",
        "computeAlternativeRoutes": True,
        "languageCode": "en",
    }
    if mode == "bus":
        body["transitPreferences"] = {"allowedTravelModes": ["BUS"]}
    elif mode == "train":
        body["transitPreferences"] = {"allowedTravelModes": ["RAIL"]}
    if departure_time:
        body["departureTime"] = departure_time

    response = requests.post(
        ROUTES_URL,
        headers=_headers(
            "routes.duration,routes.distanceMeters,"
            "routes.legs.steps.transitDetails,"
            "routes.travelAdvisory.transitFare"
        ),
        json=body,
        timeout=30,
    )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        return {"available": False, "options": [],
                "message": f"Google Routes API error {response.status_code}", "detail": detail}

    routes = response.json().get("routes") or []
    if not routes:
        return {"available": False, "options": [], "message": "No public transit route was found."}

    options = []
    for route in routes:
        segments = _parse_segments(route)
        vehicles = _extract_vehicle_types(route)
        classified = _classify_transport(vehicles)
        if mode == "bus" and classified not in {"bus", "mixed_public_transit"}:
            continue
        if mode == "train" and classified not in {"train", "mixed_public_transit"}:
            continue
        if not segments:
            continue

        fare_value, fare_currency = _money_value(
            (route.get("travelAdvisory") or {}).get("transitFare")
        )
        distance_m = route.get("distanceMeters")
        distance_km = round(float(distance_m) / 1000, 1) if isinstance(distance_m, (int, float)) else None
        seconds = _duration_seconds(route.get("duration"))
        minutes = int(round(seconds / 60)) if seconds is not None else None

        first, last = segments[0], segments[-1]
        options.append({
            "transport_type": classified,
            "vehicle_types": vehicles,
            "segments": segments,
            "from_name": first.get("from_name"),
            "to_name": last.get("to_name"),
            "departure_time": first.get("departure_time"),
            "arrival_time": last.get("arrival_time"),
            "duration_minutes": minutes,
            "travel_time": format_minutes(minutes),
            "changes": max(0, len(segments) - 1),
            "operator": first.get("line_name") or first.get("operator"),
            "price_per_person": fare_value,
            "currency": fare_currency,
            "fare_available": fare_value is not None,
            "distance_km": distance_km,
        })
        if len(options) >= limit:
            break

    if not options:
        return {"available": False, "options": [],
                "message": f"No {mode or 'transit'} route was found by Google Routes."}
    return {"available": True, "options": options}


def get_driving_distance_km(source: str, destination: str):
    """Road distance, used only to estimate fare/duration when no schedule exists."""
    if not GOOGLE_MAPS_API_KEY:
        return None
    body = {
        "origin": {"address": source},
        "destination": {"address": destination},
        "travelMode": "DRIVE",
        "languageCode": "en",
    }
    try:
        response = requests.post(
            ROUTES_URL,
            headers=_headers("routes.distanceMeters,routes.duration"),
            json=body,
            timeout=20,
        )
        if response.status_code >= 400:
            return None
        routes = response.json().get("routes") or []
        meters = routes[0].get("distanceMeters") if routes else None
        return round(float(meters) / 1000, 1) if meters else None
    except (requests.RequestException, ValueError, TypeError):
        return None


# ------------------------------------------------------------------
# backward-compatible single-route wrapper
# ------------------------------------------------------------------
def get_transit_route(source, destination, travelers=1, allowed_mode=None, departure_time=None):
    result = get_transit_options(source, destination, travelers, allowed_mode, departure_time, limit=1)
    if not result.get("available"):
        return result
    first = result["options"][0]
    price = first.get("price_per_person")
    return {
        "available": True,
        "transport_type": first["transport_type"],
        "price_per_person": price,
        "total_price": price * max(1, travelers) if price is not None else None,
        "currency": first.get("currency"),
        "fare_available": first.get("fare_available"),
        "travel_time": first.get("travel_time"),
        "distance_km": first.get("distance_km"),
        "vehicle_types": first.get("vehicle_types", []),
    }


def calculate_public_transit_route(source, destination, travelers=1, mode=None, departure_time=None):
    return get_transit_route(source, destination, travelers, mode, departure_time)
