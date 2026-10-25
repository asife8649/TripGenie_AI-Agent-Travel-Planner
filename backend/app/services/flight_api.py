# backend/app/services/flight_api.py

import os
from typing import Optional

import requests
from dotenv import load_dotenv

from .airport_codes import AIRPORT_CODES


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

FLIGHT_API_KEY = os.getenv("FLIGHT_API_KEY")
IGNAV_API_KEY = os.getenv("IGNAV_API_KEY")


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://api.flightapi.io"


# ============================================================
# AIRPORT CODE RESOLVER
# ============================================================

def get_airport_code(location: str) -> Optional[str]:
    """
    Convert city/location name into IATA airport code.

    Example:
        Kolkata   -> CCU
        Darjeeling -> IXB
    """

    if not location:
        return None

    location_clean = (
        location
        .strip()
        .lower()
    )

    # Direct dictionary lookup
    code = AIRPORT_CODES.get(
        location_clean
    )

    if code:
        return code

    # Try removing spaces
    normalized = (
        location_clean
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )

    for city, airport_code in AIRPORT_CODES.items():

        city_normalized = (
            city.lower()
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
        )

        if city_normalized == normalized:
            return airport_code

    return None


# ============================================================
# VALIDATE CONFIGURATION
# ============================================================

def validate_configuration():
    # FlightAPI is optional because Ignav is the automatic fallback.
    if not FLIGHT_API_KEY and not IGNAV_API_KEY:
        print("Warning: neither FLIGHT_API_KEY nor IGNAV_API_KEY is configured.")


# ============================================================
# SAFE ERROR PRINTER
# ============================================================

def print_flight_error(
    response,
    url: str,
):
    """
    Print FlightAPI error safely.

    API key is hidden from output.
    """

    safe_url = url

    if FLIGHT_API_KEY:
        safe_url = safe_url.replace(
            FLIGHT_API_KEY,
            "***"
        )

    print("\n")
    print("========================================")
    print("FLIGHTAPI ERROR")
    print("========================================")

    print(
        "STATUS:",
        response.status_code
    )

    print(
        "URL:",
        safe_url
    )

    print(
        "RESPONSE:",
        response.text
    )

    print("========================================")
    print("\n")


# ============================================================
# PARSE FLIGHT PRICE
# ============================================================

def _extract_price(
    itinerary: dict,
):
    """
    Try to extract the first available
    price from FlightAPI itinerary.
    """

    if not isinstance(
        itinerary,
        dict
    ):
        return None

    # Common direct price locations
    possible_values = [
        itinerary.get("price"),
        itinerary.get("totalPrice"),
        itinerary.get("amount"),
    ]

    for value in possible_values:

        if value is None:
            continue

        try:
            return float(value)

        except (
            TypeError,
            ValueError
        ):
            continue

    # Check pricing options
    pricing_options = itinerary.get(
        "pricingOptions"
    )

    if isinstance(
        pricing_options,
        list
    ):

        for option in pricing_options:

            if not isinstance(
                option,
                dict
            ):
                continue

            for key in [
                "price",
                "totalPrice",
                "amount",
            ]:

                value = option.get(key)

                if value is None:
                    continue

                try:
                    return float(value)

                except (
                    TypeError,
                    ValueError
                ):
                    continue

    return None



def _first(d, *keys):
    for k in keys:
        v = d.get(k) if isinstance(d, dict) else None
        if v not in (None, ""):
            return v
    return None


def _parse_flightapi_lookup(data, travelers):
    """Parser for FlightAPI responses that use id lookups:
    itineraries[].pricing_options[].price.amount + legs[] / segments[] / carriers[] / places[].
    Field names are read tolerantly (snake_case and camelCase).
    FlightAPI quotes the whole party, so the amount is treated as the TOTAL.
    """
    if not isinstance(data, dict):
        return []
    itineraries = data.get("itineraries")
    if not isinstance(itineraries, list) or not itineraries:
        return []

    def by_id(key):
        return {str(x.get("id")): x for x in (data.get(key) or []) if isinstance(x, dict) and x.get("id") is not None}

    legs, segments, carriers, places = by_id("legs"), by_id("segments"), by_id("carriers"), by_id("places")

    def place_code(pid):
        p = places.get(str(pid)) or {}
        return _first(p, "display_code", "displayCode", "iata", "code", "name")

    def carrier_name(cid):
        c = carriers.get(str(cid)) or {}
        return _first(c, "name", "display_code", "displayCode")

    def build_leg(leg_id, direction):
        leg = legs.get(str(leg_id))
        if not leg:
            return None
        seg_ids = _first(leg, "segment_ids", "segmentIds") or []
        segs = [segments.get(str(i)) for i in seg_ids if segments.get(str(i))]
        numbers, layovers = [], []
        for sg in segs:
            code = ""
            cid = _first(sg, "marketing_carrier_id", "marketingCarrierId")
            c = carriers.get(str(cid)) or {}
            code = _first(c, "display_code", "displayCode", "iata") or ""
            num = _first(sg, "marketing_flight_number", "marketingFlightNumber", "flight_number") or ""
            if code or num:
                numbers.append(f"{code}{num}")
        for sg in segs[:-1]:
            code = place_code(_first(sg, "destination_place_id", "destinationPlaceId", "arrival_place_id"))
            if code:
                layovers.append(code)
        cids = _first(leg, "marketing_carrier_ids", "marketingCarrierIds") or []
        airline = carrier_name(cids[0]) if cids else None
        minutes = _first(leg, "duration")
        return {
            "direction": direction,
            "from_code": place_code(_first(leg, "origin_place_id", "originPlaceId", "departure_place_id")),
            "to_code": place_code(_first(leg, "destination_place_id", "destinationPlaceId", "arrival_place_id")),
            "departure_time": _first(leg, "departure", "departure_time"),
            "arrival_time": _first(leg, "arrival", "arrival_time"),
            "airline": airline,
            "flight_numbers": numbers,
            "stops": _first(leg, "stop_count", "stopCount") if _first(leg, "stop_count", "stopCount") is not None else max(0, len(segs) - 1),
            "layover_airports": layovers,
            "duration_minutes": minutes,
            "duration_text": _fmt_minutes_flight(minutes),
        }

    results = []
    for it in itineraries:
        if not isinstance(it, dict):
            continue
        options = _first(it, "pricing_options", "pricingOptions") or []
        amounts = []
        for opt in options:
            price = opt.get("price") if isinstance(opt, dict) else None
            amount = _first(price, "amount") if isinstance(price, dict) else (price if isinstance(price, (int, float)) else None)
            try:
                if amount is not None and float(amount) > 0:
                    amounts.append(float(amount))
            except (TypeError, ValueError):
                pass
        if not amounts:
            continue
        total = min(amounts)
        leg_ids = _first(it, "leg_ids", "legIds") or []
        parsed_legs = [
            leg for leg in (
                build_leg(leg_ids[0], "outbound") if len(leg_ids) > 0 else None,
                build_leg(leg_ids[1], "return") if len(leg_ids) > 1 else None,
            ) if leg
        ]
        results.append({
            "mode": "flight",
            "transport_type": "flight",
            "price_per_person": round(total / max(1, travelers), 2),
            "total_price": total,
            "currency": "INR",
            "travel_time": None,
            "source_airport": parsed_legs[0]["from_code"] if parsed_legs else None,
            "destination_airport": parsed_legs[0]["to_code"] if parsed_legs else None,
            "fare_available": True,
            "provider": "FlightAPI",
            "price_status": "indicative",
            "price_type": "indicative",
            "trip_type": "round_trip",
            "legs": parsed_legs,
        })
    results.sort(key=lambda r: r["total_price"])
    return results[:5]


# ============================================================
# PARSE FLIGHT RESPONSE
# ============================================================

def _parse_flight_response(
    data: dict,
    travelers: int,
):
    """
    Convert FlightAPI response into
    TripGenie transport structure.
    """

    if not isinstance(
        data,
        dict
    ):
        return []

    try:
        modern = _parse_flightapi_lookup(data, travelers)
    except Exception as error:
        print("FlightAPI lookup parser failed:", error)
        modern = []
    if modern:
        return modern
    print("FlightAPI: unfamiliar response shape, top-level keys =", list(data.keys())[:12])

    itineraries = data.get(
        "itineraries",
        []
    )

    if not isinstance(
        itineraries,
        list
    ):
        return []

    results = []

    for itinerary in itineraries:

        if not isinstance(
            itinerary,
            dict
        ):
            continue

        price_per_person = (
            _extract_price(
                itinerary
            )
        )

        if price_per_person is None:
            continue

        total_price = (
            price_per_person
            * travelers
        )

        results.append(
            {
                "transport_type": "flight",

                "price_per_person":
                    price_per_person,

                "total_price":
                    total_price,

                "currency": "INR",

                "travel_time":
                    itinerary.get(
                        "duration"
                    ),

                "source_airport":
                    itinerary.get(
                        "departureAirport"
                    ),

                "destination_airport":
                    itinerary.get(
                        "arrivalAirport"
                    ),

                "fare_available": True,
                "provider": "FlightAPI",
                "price_status": "unverified",
                "trip_type": "round_trip",
            }
        )

    results.sort(
        key=lambda item:
        item.get(
            "price_per_person",
            float("inf")
        )
    )

    return results[:5]


# ============================================================
# IGNAV FALLBACK
# ============================================================


def _fmt_minutes_flight(value):
    try:
        mins = int(value)
    except (TypeError, ValueError):
        return None
    if mins <= 0:
        return None
    hrs, rem = divmod(mins, 60)
    return f"{hrs} hr {rem} min" if hrs and rem else (f"{hrs} hr" if hrs else f"{rem} min")


def _ignav_leg(leg, direction):
    """Turn an Ignav outbound/inbound leg into a display-ready dict with clock times."""
    if not isinstance(leg, dict):
        return None
    segments = [s for s in (leg.get("segments") or []) if isinstance(s, dict)]
    if not segments:
        return None
    first, last = segments[0], segments[-1]
    numbers = []
    for seg in segments:
        code = seg.get("marketing_carrier_code") or ""
        number = seg.get("flight_number") or ""
        if code or number:
            numbers.append(f"{code}{number}".strip())
    layovers = [s.get("arrival_airport") for s in segments[:-1] if s.get("arrival_airport")]
    return {
        "direction": direction,
        "from_code": first.get("departure_airport"),
        "to_code": last.get("arrival_airport"),
        "departure_time": first.get("departure_time_local"),
        "arrival_time": last.get("arrival_time_local"),
        "airline": first.get("operating_carrier_name") or leg.get("carrier"),
        "flight_numbers": numbers,
        "stops": max(0, len(segments) - 1),
        "layover_airports": layovers,
        "duration_minutes": leg.get("duration_minutes"),
        "duration_text": _fmt_minutes_flight(leg.get("duration_minutes")),
        "aircraft": first.get("aircraft"),
    }


def _parse_ignav_response(data: dict, travelers: int):
    """Convert Ignav round-trip results into TripGenie transport items."""
    if not isinstance(data, dict):
        return []

    itineraries = data.get("itineraries", [])
    if not isinstance(itineraries, list):
        return []

    results = []

    for itinerary in itineraries:
        if not isinstance(itinerary, dict):
            continue

        price = itinerary.get("price")
        if not isinstance(price, dict):
            continue

        try:
            amount = float(price.get("amount"))
        except (TypeError, ValueError):
            continue

        currency = str(price.get("currency") or "").upper()
        if amount <= 0 or currency != "INR":
            # TripGenie's budget engine is INR based. Never pretend another
            # currency is INR and never create an estimated conversion here.
            print("Ignav result skipped: non-INR currency:", currency)
            continue

        outbound = itinerary.get("outbound") or {}
        segments = outbound.get("segments") or []

        source_airport = None
        destination_airport = None
        if isinstance(segments, list) and segments:
            first = segments[0] if isinstance(segments[0], dict) else {}
            last = segments[-1] if isinstance(segments[-1], dict) else {}
            source_airport = first.get("departure_airport")
            destination_airport = last.get("arrival_airport")

        outbound_duration = outbound.get("duration_minutes")
        inbound = itinerary.get("inbound") or {}
        inbound_duration = inbound.get("duration_minutes")
        duration_parts = []
        try:
            if outbound_duration is not None and int(outbound_duration) > 0:
                duration_parts.append(f"Outbound {int(outbound_duration)} min")
        except (TypeError, ValueError):
            pass
        try:
            if inbound_duration is not None and int(inbound_duration) > 0:
                duration_parts.append(f"Return {int(inbound_duration)} min")
        except (TypeError, ValueError):
            pass
        def fmt_minutes(value):
            try:
                mins = int(value)
            except (TypeError, ValueError):
                return None
            hrs, rem = divmod(mins, 60)
            return f"{hrs} hr {rem} min" if hrs and rem else (f"{hrs} hr" if hrs else f"{rem} min")

        pretty_parts = []
        if outbound_duration is not None and str(outbound_duration).isdigit():
            pretty_parts.append(f"Outbound: {fmt_minutes(outbound_duration)}")
        if inbound_duration is not None and str(inbound_duration).isdigit():
            pretty_parts.append(f"Return: {fmt_minutes(inbound_duration)}")
        travel_time = " · ".join(pretty_parts) if pretty_parts else None

        # Ignav's `price.amount` is the itinerary-level price for the search,
        # not a per-person amount. Do not multiply it by the passenger count.
        # Derive a per-person display value only for convenience.
        price_status = str(price.get("status") or "unknown").lower()
        results.append({
            "transport_type": "flight",
            "price_per_person": round(amount / max(1, travelers), 2),
            "total_price": amount,
            "currency": currency,
            "travel_time": travel_time,
            "source_airport": source_airport,
            "destination_airport": destination_airport,
            "fare_available": price_status == "verified",
            "trip_type": "round_trip",
            "provider": "Ignav",
            "airline": outbound.get("carrier"),
            "ignav_id": itinerary.get("ignav_id"),
            "price_status": price_status,
            "price_type": "live" if price_status == "verified" else "indicative",
            "legs": [
                leg for leg in (
                    _ignav_leg(outbound, "outbound"),
                    _ignav_leg(inbound, "return"),
                ) if leg
            ],
        })

    results.sort(key=lambda item: item.get("total_price", float("inf")))
    # Keep the UI focused on the ten cheapest results rather than rendering
    # every itinerary returned by the provider.
    return results[:5]


def _search_ignav_round_trip(
    departure_code: str,
    arrival_code: str,
    departure_date: str,
    return_date: str,
    travelers: int,
):
    if not IGNAV_API_KEY:
        print("Ignav fallback skipped: IGNAV_API_KEY is not configured.")
        return []

    url = "https://ignav.com/api/fares/round-trip"
    headers = {
        "X-Api-Key": IGNAV_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "origin": departure_code,
        "destination": arrival_code,
        "departure_date": str(departure_date),
        "return_date": str(return_date),
        "adults": max(1, int(travelers)),
        "cabin_class": "economy",
        "market": "IN",
        "allow_self_transfer": False,
    }

    print("\n========================================")
    print("IGNAV FLIGHT FALLBACK")
    print("========================================")
    print("ORIGIN:", departure_code)
    print("DESTINATION:", arrival_code)
    print("DEPARTURE DATE:", departure_date)
    print("RETURN DATE:", return_date)
    print("TRAVELERS:", travelers)

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
    except requests.exceptions.Timeout as error:
        print("Ignav timeout:", error)
        return []
    except requests.exceptions.RequestException as error:
        print("Ignav request failed:", error)
        return []

    print("IGNAV STATUS:", response.status_code)

    if response.status_code >= 400:
        print("IGNAV RESPONSE:", response.text[:2000])
        return []

    try:
        data = response.json()
    except ValueError:
        print("Ignav returned invalid JSON.")
        return []

    results = _parse_ignav_response(data, travelers)
    print("Ignav flights found:", len(results))
    return results


# ============================================================
# ROUND TRIP FLIGHT SEARCH
# ============================================================

def search_round_trip_flights(
    source: str,
    destination: str,
    departure_date: str,
    return_date: str,
    travelers: int = 1,
):
    """Search FlightAPI first, then automatically fall back to Ignav."""
    validate_configuration()

    if not departure_date or not return_date or travelers <= 0:
        return []

    departure_code = get_airport_code(source)
    arrival_code = get_airport_code(destination)

    if not departure_code:
        print(f"No airport code found for source: {source}")
        return []
    if not arrival_code:
        print(f"No airport code found for destination: {destination}")
        return []

    print("\n========================================")
    print("FLIGHT SEARCH")
    print("========================================")
    print("SOURCE:", source)
    print("DESTINATION:", destination)
    print("DEPARTURE AIRPORT:", departure_code)
    print("ARRIVAL AIRPORT:", arrival_code)
    print("DEPARTURE DATE:", departure_date)
    print("RETURN DATE:", return_date)
    print("TRAVELERS:", travelers)

    flightapi_results = []

    if FLIGHT_API_KEY:
        url = (
            f"{BASE_URL}/roundtrip/{FLIGHT_API_KEY}/"
            f"{departure_code}/{arrival_code}/{departure_date}/{return_date}/"
            f"{travelers}/0/0/Economy/INR"
        )
        try:
            response = requests.get(url, timeout=60)
            if response.status_code >= 400:
                print_flight_error(response, url)
            else:
                try:
                    flightapi_results = _parse_flight_response(
                        response.json(), travelers
                    )
                except ValueError:
                    print("FlightAPI returned invalid JSON.")
        except requests.exceptions.Timeout as error:
            print("FlightAPI timeout:", error)
        except requests.exceptions.RequestException as error:
            print("FlightAPI request failed:", error)
    else:
        print("FlightAPI skipped: FLIGHT_API_KEY is not configured.")

    print("FlightAPI flights found:", len(flightapi_results))

    if flightapi_results:
        return flightapi_results

    print("FlightAPI unavailable. Trying Ignav fallback...")
    return _search_ignav_round_trip(
        departure_code=departure_code,
        arrival_code=arrival_code,
        departure_date=departure_date,
        return_date=return_date,
        travelers=travelers,
    )


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def search_flights(
    source: str,
    destination: str,
    departure_date: str,
    return_date: str,
    travelers: int = 1,
):
    """
    Backward-compatible wrapper.
    """

    return search_round_trip_flights(
        source=source,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        travelers=travelers,
    )