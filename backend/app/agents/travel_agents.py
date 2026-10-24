import math
import re
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from ..services.google_places import search_tourist_places
from ..services.google_routes import get_transit_options, get_driving_distance_km
from ..services.flight_api import search_round_trip_flights
from ..services.airport_codes import get_airport_note
from ..services.fare_estimator import (
    estimate_bus_fares,
    estimate_duration_minutes,
    estimate_train_fares,
    format_minutes,
)
from ..services import rail_api
from ..services.hotel_service import (
    DEFAULT_ROOM_NIGHT_INR,
    booking_search_url,
    nights_between,
    rooms_needed,
    search_hotels,
)


DESTINATION_ALIASES = {
    "murshdabd": "Murshidabad",
    "murshidabd": "Murshidabad",
    "murshidabad": "Murshidabad",
    "murshidabad city": "Murshidabad",
    "mursidabad": "Murshidabad",
    "murshedabad": "Murshidabad",
    "calcutta": "Kolkata",
    "kolkata": "Kolkata",
}


def normalize_destination(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    key = " ".join(text.lower().split())
    return DESTINATION_ALIASES.get(key, text.title())


def _numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _transit_departure_time(date_value, hour=9):
    """Convert a date-only value into a future RFC3339 local time for Google Routes."""
    if not date_value:
        return None
    value = str(date_value)[:10]
    try:
        dt = datetime.fromisoformat(value).replace(hour=hour, minute=0, second=0)
        return dt.isoformat(timespec="seconds") + "+05:30"  # India is UTC+05:30
    except ValueError:
        return None


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")


# ----------------------------------------------------------------------
# Transport item builders (one common shape for the UI + PDF)
# ----------------------------------------------------------------------
def _transit_item(option, mode, direction, travelers):
    """Build a train/bus card from a Google Routes option."""
    distance = option.get("distance_km")
    price = option.get("price_per_person")
    class_fares = []
    if _numeric(price):
        price_type = "live"
        price_source = "Google Routes transit fare"
    else:
        class_fares = estimate_train_fares(distance) if mode == "train" else estimate_bus_fares(distance)
        price = min((f["fare"] for f in class_fares), default=None)
        price_type = "estimate" if price is not None else "unavailable"
        price_source = "Distance-based estimate (no live fare available)" if price is not None else None

    return {
        "mode": mode,
        "transport_type": option.get("transport_type") or mode,
        "direction": direction,
        "trip_type": "round_trip",
        "from_name": option.get("from_name"),
        "to_name": option.get("to_name"),
        "departure_time": option.get("departure_time"),
        "arrival_time": option.get("arrival_time"),
        "duration_minutes": option.get("duration_minutes"),
        "travel_time": option.get("travel_time"),
        "changes": option.get("changes"),
        "operator": option.get("operator"),
        "segments": option.get("segments") or [],
        "distance_km": distance,
        "price_per_person": float(price) if _numeric(price) else None,
        "total_price": float(price) * travelers if _numeric(price) else None,
        "currency": option.get("currency") or ("INR" if price is not None else None),
        "class_fares": class_fares,
        "fare_available": price_type == "live",
        "price_type": price_type,
        "price_status": price_type,
        "price_source": price_source,
        "provider": "Google Routes",
        "vehicle_types": option.get("vehicle_types", []),
    }


def _rail_item(journey, direction, travelers, distance_km=None):
    price = journey.get("price_per_person")
    journey = dict(journey)
    journey.update({
        "mode": "train",
        "direction": direction,
        "trip_type": "round_trip",
        "total_price": float(price) * travelers if _numeric(price) else None,
        "price_status": journey.get("price_type", "unavailable"),
        "segments": [],
        "changes": 0,
        "distance_km": distance_km,
    })
    # Provider gave a schedule but no fare: show a labelled class-wise estimate.
    if not _numeric(price) and distance_km:
        fares = estimate_train_fares(distance_km)
        cheapest = min((f["fare"] for f in fares), default=None)
        journey.update({
            "class_fares": fares,
            "price_per_person": cheapest,
            "total_price": cheapest * travelers if cheapest is not None else None,
            "currency": "INR",
            "price_type": "estimate",
            "price_status": "estimate",
            "price_source": "Distance-based estimate (live fare not returned)",
        })
    return journey


def _estimate_only_item(mode, direction, source, destination, travelers):
    """No schedule found anywhere: distance-based estimate, no clock times."""
    distance = get_driving_distance_km(source, destination)
    if not distance:
        return None
    fares = estimate_train_fares(distance) if mode == "train" else estimate_bus_fares(distance)
    price = min((f["fare"] for f in fares), default=None)
    minutes = estimate_duration_minutes(distance, mode)
    return {
        "mode": mode,
        "transport_type": mode,
        "direction": direction,
        "trip_type": "round_trip",
        "from_name": source,
        "to_name": destination,
        "departure_time": None,
        "arrival_time": None,
        "duration_minutes": minutes,
        "travel_time": f"≈ {format_minutes(minutes)}" if minutes else None,
        "changes": None,
        "operator": None,
        "segments": [],
        "distance_km": distance,
        "price_per_person": price,
        "total_price": price * travelers if price is not None else None,
        "currency": "INR",
        "class_fares": fares,
        "fare_available": False,
        "price_type": "estimate",
        "price_status": "estimate",
        "price_source": "Distance-based estimate — timetable not available",
        "provider": "TripGenie estimate",
        "schedule_unavailable": True,
        "vehicle_types": [],
    }


class TransportAgent:

    def __init__(self):
        self.notes = []

    def _transit_for_direction(self, mode, src, dst, travelers, date_value, direction):
        items = []

        # 1) Real train timetable + fares (optional paid provider)
        if mode == "train" and rail_api.is_configured() and date_value:
            try:
                journeys = rail_api.search_trains(src, dst, date_value, travelers)
                distance = None
                if any(j.get("price_per_person") is None for j in journeys):
                    distance = get_driving_distance_km(src, dst)
                for journey in journeys:
                    items.append(_rail_item(journey, direction, travelers, distance))
            except Exception as error:
                print("Rail API failed:", error)

        # 2) Google Routes: stations + clock times (when Google has the schedule)
        if not items:
            try:
                result = get_transit_options(
                    source=src, destination=dst, travelers=travelers, allowed_mode=mode,
                    departure_time=_transit_departure_time(date_value, hour=9), limit=3,
                )
                print(f"{mode.title()} {direction} Google result:", result.get("available"), result.get("message", ""))
                for option in result.get("options", []):
                    items.append(_transit_item(option, mode, direction, travelers))
            except Exception as error:
                print(f"{mode.title()} {direction} search failed:", error)

        # 3) Last resort: labelled estimate
        if not items:
            fallback = _estimate_only_item(mode, direction, src, dst, travelers)
            if fallback:
                items.append(fallback)
            else:
                self.notes.append(f"No {mode} {direction} information could be found for {src} → {dst}.")
        return items

    def search(self, source, destination, travelers, transport_option,
               departure_date=None, return_date=None):
        print("\n[1] Transport Agent")
        self.notes = []
        source = normalize_destination(source)
        destination = normalize_destination(destination)
        option = (transport_option or "both").lower().strip()
        results = []

        # ---------------- FLIGHTS ----------------
        if option in {"flight", "all"}:
            if departure_date and return_date:
                try:
                    flights = search_round_trip_flights(
                        source=source, destination=destination,
                        departure_date=str(departure_date), return_date=str(return_date),
                        travelers=travelers,
                    )
                    flights = [f for f in (flights or []) if isinstance(f, dict)]
                    note = get_airport_note(destination)
                    for f in flights:
                        if note:
                            f["airport_note"] = note
                    results.extend(flights)
                    if not flights:
                        self.notes.append(
                            "No flight fares returned. Check FLIGHT_API_KEY / IGNAV_API_KEY, "
                            "that both cities have an airport, and that the dates are in the future."
                        )
                except Exception as error:
                    print("Flight search failed:", error)
                    self.notes.append("Flight search failed. See backend logs.")
            else:
                self.notes.append("Flight search skipped: departure and return dates are required.")

        # ---------------- TRAIN / BUS ----------------
        if option in {"train", "bus", "both", "all"}:
            modes = ["train", "bus"] if option in {"both", "all"} else [option]
            for mode in modes:
                results.extend(self._transit_for_direction(mode, source, destination, travelers, departure_date, "outbound"))
                if return_date:
                    results.extend(self._transit_for_direction(mode, destination, source, travelers, return_date, "return"))

        return [item for item in results if isinstance(item, dict)]


# ----------------------------------------------------------------------
# Hotels
# ----------------------------------------------------------------------
class HotelAgent:
    """Real hotel names via SerpApi/Google Places; prices are labelled live/range/estimate."""

    ESTIMATED_ROOM_NIGHT_INR = DEFAULT_ROOM_NIGHT_INR

    def search(self, destination, departure_date, return_date, travelers, days=1):
        print("\n[2] Hotel Agent")
        check_in = departure_date
        check_out = return_date
        if departure_date and not return_date:
            try:
                start = datetime.fromisoformat(str(departure_date)[:10])
                check_out = (start + timedelta(days=max(0, int(days) - 1))).date().isoformat()
            except ValueError:
                check_out = None

        hotels = search_hotels(destination, check_in, check_out, travelers, limit=6)

        # Dates missing: derive nights from the "days" field instead.
        if not (check_in and check_out):
            fallback_nights = max(0, int(days) - 1)
            for h in hotels:
                per_room = h.get("price_per_room_night")
                h["nights"] = fallback_nights
                if _numeric(per_room) and fallback_nights:
                    h["total_price"] = round(per_room * h["rooms"] * fallback_nights, 2)
        return hotels


class PlacesAgent:

    def search(self, destination):
        print("\n[3] Places Agent")
        destination = normalize_destination(destination)
        try:
            places = search_tourist_places(destination=destination, limit=8)
            if not isinstance(places, list):
                return []
            cleaned = []
            for place in places:
                if not isinstance(place, dict):
                    continue
                if place.get("estimated_cost") == 0:
                    place["estimated_cost"] = None
                cleaned.append(place)
            return cleaned
        except Exception as error:
            print("Places search failed:", error)
            return []


def self_hotel_estimate(nights, rooms):
    return max(0, int(nights)) * max(1, int(rooms)) * DEFAULT_ROOM_NIGHT_INR


# ----------------------------------------------------------------------
# Budget
# ----------------------------------------------------------------------
class BudgetAgent:

    @staticmethod
    def _best_complete_transport(transport_options):
        """Cheapest complete transport choice (not the sum of alternatives).

        Returns (total_cost | None, is_estimate). Flights are priced as one
        round-trip fare. Train/bus use cheapest outbound + cheapest return of
        the same mode. Only explicitly 'unverified' provider quotes are skipped;
        labelled estimates are included and flagged.
        """
        options = [i for i in (transport_options or []) if isinstance(i, dict)]
        candidates = []  # (cost, is_estimate)

        directional = [i for i in options if i.get("direction") in {"outbound", "return"}]
        for item in options:
            if item in directional:
                continue
            status = str(item.get("price_status") or "").lower()
            if status in {"unverified", "unknown", "indicative"}:
                continue
            price = item.get("total_price")
            if _numeric(price):
                candidates.append((float(price), status == "estimate"))

        if directional:
            return_required = any(i.get("direction") == "return" for i in directional)
            by_mode = {}
            for item in directional:
                mode = str(item.get("transport_type") or "public_transit")
                price = item.get("total_price")
                if _numeric(price):
                    by_mode.setdefault(mode, {}).setdefault(item["direction"], []).append(
                        (float(price), str(item.get("price_status")) == "estimate")
                    )
            for legs in by_mode.values():
                out_prices = legs.get("outbound", [])
                ret_prices = legs.get("return", [])
                if not out_prices or (return_required and not ret_prices):
                    continue
                best_out = min(out_prices)
                total, est = best_out
                if return_required:
                    best_ret = min(ret_prices)
                    total += best_ret[0]
                    est = est or best_ret[1]
                candidates.append((total, est))

        if not candidates:
            return None, False
        return min(candidates)

    @staticmethod
    def _pick_budget_hotel(hotels):
        priced = [h for h in (hotels or []) if isinstance(h, dict) and _numeric(h.get("price_per_room_night"))]
        if not priced:
            return None
        decent = [h for h in priced if h.get("rating") is None or float(h["rating"]) >= 3.5] or priced
        return min(decent, key=lambda h: h["price_per_room_night"])

    def calculate(self, transport_options, hotels, places, budget_per_person, travelers, days):
        print("\n[4] Budget Agent")
        total_transport, transport_is_estimate = self._best_complete_transport(transport_options)
        transport_known = total_transport is not None

        hotel = self._pick_budget_hotel(hotels)
        rooms = int(hotel.get("rooms")) if hotel and hotel.get("rooms") else rooms_needed(travelers)
        nights = int(hotel.get("nights") or 0) if hotel else max(0, int(days) - 1)
        per_room_night = float(hotel["price_per_room_night"]) if hotel else DEFAULT_ROOM_NIGHT_INR
        hotel_total = per_room_night * rooms * nights
        hotel_price_type = hotel.get("price_type", "estimate") if hotel else "estimate"

        food_estimate = 800.0 * max(1, travelers) * max(1, days)
        local_transport_estimate = 500.0 * max(1, travelers) * max(1, days)
        total_budget = float(budget_per_person) * travelers
        estimated_total = (total_transport or 0.0) + hotel_total + food_estimate + local_transport_estimate

        notes = []
        if hotel:
            label = {
                "live": "live nightly rate",
                "google_range": "Google price range (indicative)",
            }.get(hotel_price_type, "estimate")
            notes.append(f"Hotel budget uses the cheapest well-rated option ({hotel.get('hotel_name')}) — {label}.")
        else:
            notes.append("Hotel price is a planning allowance, not live availability.")
        if transport_known and transport_is_estimate:
            notes.append("Transport total includes a distance-based fare estimate; confirm the real fare before travel.")
        if not transport_known:
            notes.append("No usable transport fare was found; total excludes transport cost.")
        notes += [
            "Food allowance: ₹800 per person per day.",
            "Local transport allowance: ₹500 per person per day.",
            "Attraction entry fees and shopping are not included.",
        ]

        return {
            "total_transport": round(total_transport, 2) if transport_known else None,
            "transport_is_estimate": bool(transport_known and transport_is_estimate),
            "total_hotel": round(hotel_total, 2),
            "hotel_is_estimate": hotel_price_type != "live",
            "hotel_price_type": hotel_price_type,
            "hotel_name": hotel.get("hotel_name") if hotel else None,
            "hotel_per_night_estimate": round(per_room_night * rooms, 2),
            "hotel_per_room_night": round(per_room_night, 2),
            "hotel_nights": nights,
            "hotel_rooms": rooms,
            "food_estimate": round(food_estimate, 2),
            "local_transport_estimate": round(local_transport_estimate, 2),
            "total_places": None,
            "total_estimated_cost": round(estimated_total, 2),
            "remaining_budget": round(total_budget - estimated_total, 2),
            "budget_is_estimate": True,
            "missing_transport_price": not transport_known,
            "budget_notes": notes,
        }


# ----------------------------------------------------------------------
# Itinerary
# ----------------------------------------------------------------------
class ItineraryAgent:

    def create(self, destination, places, days, departure_date=None):
        print("\n[5] Itinerary Agent")
        destination = normalize_destination(destination)
        valid = [p for p in (places or []) if isinstance(p, dict) and p.get("place_name")]

        try:
            start = datetime.fromisoformat(str(departure_date)[:10]).date() if departure_date else None
        except ValueError:
            start = None

        itinerary = []
        for day_number in range(1, days + 1):
            if valid:
                first = valid[((day_number - 1) * 2) % len(valid)]
                second = valid[((day_number - 1) * 2 + 1) % len(valid)]
                activities = [f"Morning: visit {first['place_name']}"]
                if second["place_name"] != first["place_name"]:
                    activities.append(f"Afternoon: visit {second['place_name']}")
                else:
                    activities.append("Afternoon: explore nearby streets and markets")
                activities.append("Evening: local food and rest")
            else:
                activities = [
                    f"Morning: explore {destination}",
                    "Afternoon: visit local attractions",
                    "Evening: local food and rest",
                ]
            if day_number == 1:
                activities.insert(0, "Arrive, check in to your hotel and freshen up")
            if day_number == days and days > 1:
                activities.append("Check out and start your return journey")

            itinerary.append({
                "day_number": day_number,
                "date": (start + timedelta(days=day_number - 1)).isoformat() if start else None,
                "title": f"Day {day_number} — Explore {destination}",
                "activities": activities,
                "estimated_cost": None,
            })
        return itinerary


# ----------------------------------------------------------------------
# Coordinator
# ----------------------------------------------------------------------
class TravelCoordinator:

    def __init__(self):
        self.transport_agent = TransportAgent()
        self.hotel_agent = HotelAgent()
        self.places_agent = PlacesAgent()
        self.budget_agent = BudgetAgent()
        self.itinerary_agent = ItineraryAgent()

    def create_plan(self, source, destination, budget_per_person, travelers, days,
                    transport_option="both", departure_date=None, return_date=None):
        print("\n" + "=" * 60)
        print("TRIPGENIE TRAVEL PLAN")
        print("=" * 60)

        source = normalize_destination(source)
        destination = normalize_destination(destination)

        transport_options = self.transport_agent.search(
            source=source, destination=destination, travelers=travelers,
            transport_option=transport_option,
            departure_date=departure_date, return_date=return_date,
        )
        hotels = self.hotel_agent.search(
            destination=destination, departure_date=departure_date,
            return_date=return_date, travelers=travelers, days=days,
        )
        places = self.places_agent.search(destination)
        budget = self.budget_agent.calculate(
            transport_options=transport_options, hotels=hotels, places=places,
            budget_per_person=budget_per_person, travelers=travelers, days=days,
        )
        itinerary = self.itinerary_agent.create(
            destination=destination, places=places, days=days, departure_date=departure_date,
        )

        dep = str(departure_date)[:10] if departure_date else None
        ret = str(return_date)[:10] if return_date else None
        flight_link = (
            "https://www.google.com/travel/flights?q="
            + quote_plus(f"Flights from {source} to {destination} on {dep}" + (f" through {ret}" if ret else ""))
        ) if dep else "https://www.google.com/travel/flights"

        hotel_link = (
            booking_search_url(destination, dep, ret or dep, travelers) if dep
            else f"https://www.booking.com/searchresults.html?ss={quote_plus(destination)}"
        )

        return {
            "source": source,
            "destination": destination,
            "budget_per_person": budget_per_person,
            "total_budget": float(budget_per_person) * travelers,
            "travelers": travelers,
            "days": days,
            "departure_date": departure_date,
            "return_date": return_date,
            "transport_options": transport_options,
            "transport_notes": self.transport_agent.notes,
            "hotels": hotels,
            "places": places,
            "total_estimated_cost": budget["total_estimated_cost"],
            "remaining_budget": budget["remaining_budget"],
            "budget_breakdown": {
                "transport": budget["total_transport"],
                "transport_is_estimate": budget["transport_is_estimate"],
                "hotel": budget["total_hotel"],
                "hotel_name": budget["hotel_name"],
                "hotel_price_type": budget["hotel_price_type"],
                "hotel_per_night_estimate": budget["hotel_per_night_estimate"],
                "hotel_per_room_night": budget["hotel_per_room_night"],
                "hotel_nights": budget["hotel_nights"],
                "hotel_rooms": budget["hotel_rooms"],
                "food_estimate": budget["food_estimate"],
                "local_transport_estimate": budget["local_transport_estimate"],
                "budget_is_estimate": budget["budget_is_estimate"],
                "missing_transport_price": budget["missing_transport_price"],
                "notes": budget["budget_notes"],
            },
            "transport_search_links": {
                "flight": flight_link,
                "train": "https://www.irctc.co.in/nget/train-search",
                "bus": f"https://www.redbus.in/bus-tickets/{_slug(source)}-to-{_slug(destination)}",
                "hotel": hotel_link,
            },
            "itinerary": itinerary,
        }
