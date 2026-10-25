"""Live bus fares + timetable (optional) via an Apify redBus actor.

There is no public redBus API. This uses a community-built Apify actor that reads
public redBus listings (default: maximedupre/redbus, ~US$0.0009 per bus service).
Set in backend/.env:

    APIFY_TOKEN=your_apify_api_token
    APIFY_BUS_ACTOR=maximedupre~redbus        # optional, this is the default

Without a token the app falls back to Google Routes / a labelled estimate.
Third-party scraper: availability and terms can change, so keep the fallback.
"""
import os
import re
from datetime import datetime

import requests
from dotenv import load_dotenv

from .fare_estimator import format_minutes

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
APIFY_BUS_ACTOR = os.getenv("APIFY_BUS_ACTOR", "maximedupre~redbus")
TIMEOUT = 150


def is_configured() -> bool:
    return bool(APIFY_TOKEN)


def _iso(value):
    """'2026-11-05 22:35:00' -> '2026-11-05T22:35:00' (local clock time)."""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})", str(value or ""))
    return f"{m.group(1)}T{m.group(2)}:{m.group(3)}:00" if m else None


def _num(value):
    try:
        n = float(value)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def parse_services(rows, travelers, direction, limit=5):
    """Normalise Apify redBus rows into TripGenie bus journeys (cheapest first)."""
    journeys = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        fare = row.get("fare") or {}
        price = _num(fare.get("amount")) if isinstance(fare, dict) else None
        if price is None:
            continue
        if isinstance(fare, dict) and fare.get("currency") not in (None, "INR"):
            continue
        service = row.get("service") or {}
        schedule = row.get("schedule") or {}
        seats = row.get("seatAvailability") or {}
        ratings = row.get("ratings") or {}
        route = row.get("route") or {}
        boarding = [str(x) for x in (row.get("boardingLocations") or [])][:3]
        dropping = [str(x) for x in (row.get("droppingLocations") or [])][:3]
        minutes = row.get("durationMinutes")
        minutes = int(minutes) if isinstance(minutes, (int, float)) else None
        journeys.append({
            "mode": "bus",
            "transport_type": "bus",
            "direction": direction,
            "trip_type": "round_trip",
            "from_name": (boarding[0] if boarding else None) or route.get("origin"),
            "to_name": (dropping[0] if dropping else None) or route.get("destination"),
            "departure_time": _iso(schedule.get("departureTime")),
            "arrival_time": _iso(schedule.get("arrivalTime")),
            "duration_minutes": minutes,
            "travel_time": format_minutes(minutes),
            "changes": 0,
            "operator": service.get("operator") or service.get("serviceName"),
            "bus_type": service.get("busType"),
            "service_name": service.get("serviceName"),
            "rating": ratings.get("rating") if isinstance(ratings, dict) else None,
            "rating_count": ratings.get("reviewCount") if isinstance(ratings, dict) else None,
            "seats_available": seats.get("count") if isinstance(seats, dict) else None,
            "seat_status": seats.get("status") if isinstance(seats, dict) else None,
            "boarding_points": boarding,
            "dropping_points": dropping,
            "segments": [],
            "price_per_person": price,
            "total_price": price * max(1, travelers),
            "currency": "INR",
            "class_fares": [],
            "fare_available": True,
            "price_type": "live",
            "price_status": "live",
            "price_source": "redBus listing via Apify",
            "provider": "redBus (Apify)",
            "vehicle_types": ["BUS"],
        })
    journeys.sort(key=lambda j: (j["price_per_person"], j.get("departure_time") or ""))
    return journeys[:limit]


def search_buses(source, destination, date_value, travelers, direction="outbound", limit=5):
    if not is_configured() or not date_value:
        return []
    try:
        datetime.fromisoformat(str(date_value)[:10])
    except ValueError:
        return []
    try:
        response = requests.post(
            f"https://api.apify.com/v2/acts/{APIFY_BUS_ACTOR}/run-sync-get-dataset-items",
            headers={"Authorization": f"Bearer {APIFY_TOKEN}", "Content-Type": "application/json"},
            json={
                "market": "in",
                "origin": source,
                "destination": destination,
                "travelDate": str(date_value)[:10],
                "onlyAvailableSeats": False,
            },
            timeout=TIMEOUT,
        )
        if response.status_code >= 400:
            print("Apify bus error:", response.status_code, response.text[:300])
            return []
        rows = response.json()
    except (requests.RequestException, ValueError) as error:
        print("Apify bus failed:", error)
        return []
    if not isinstance(rows, list):
        return []
    return parse_services(rows, travelers, direction, limit)
