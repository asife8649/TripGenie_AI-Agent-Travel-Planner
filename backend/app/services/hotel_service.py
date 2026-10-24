"""Hotel search.

Priority:
 1. SerpApi Google Hotels  (SERPAPI_KEY)  -> real nightly rates for your dates
 2. Google Places (GOOGLE_MAPS_API_KEY)   -> real hotel names/ratings/photos,
    price from Google's price range if present, otherwise a labelled estimate
 3. Planning allowance only                -> if no key is configured at all

Each hotel carries `price_type` ("live" | "google_range" | "estimate") so the UI
and PDF never present an estimate as a quote.
"""
import math
import os
from datetime import datetime
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

DEFAULT_ROOM_NIGHT_INR = 2500.0
PRICE_LEVEL_ESTIMATE_INR = {
    "PRICE_LEVEL_FREE": 800.0,
    "PRICE_LEVEL_INEXPENSIVE": 1500.0,
    "PRICE_LEVEL_MODERATE": 3000.0,
    "PRICE_LEVEL_EXPENSIVE": 6500.0,
    "PRICE_LEVEL_VERY_EXPENSIVE": 12000.0,
}


def rooms_needed(travelers) -> int:
    return max(1, math.ceil(max(1, int(travelers)) / 2))


def nights_between(check_in, check_out) -> int:
    try:
        start = datetime.fromisoformat(str(check_in)[:10]).date()
        end = datetime.fromisoformat(str(check_out)[:10]).date()
        return max(0, (end - start).days)
    except (TypeError, ValueError):
        return 0


def booking_search_url(destination, check_in, check_out, travelers):
    return (
        "https://www.booking.com/searchresults.html"
        f"?ss={quote_plus(str(destination))}&checkin={str(check_in)[:10]}&checkout={str(check_out)[:10]}"
        f"&group_adults={max(1, int(travelers))}&no_rooms={rooms_needed(travelers)}&selected_currency=INR"
    )


def _finish(hotel: dict, nights: int, rooms: int):
    per_room = hotel.get("price_per_room_night")
    hotel["nights"] = nights
    hotel["rooms"] = rooms
    if isinstance(per_room, (int, float)):
        hotel["price_per_night"] = round(per_room * rooms, 2)
        hotel["total_price"] = round(per_room * rooms * nights, 2) if nights else None
    else:
        hotel["price_per_night"] = None
        hotel["total_price"] = None
    return hotel


# ------------------------------------------------------------------
# 1) SerpApi Google Hotels  (live rates)
# ------------------------------------------------------------------
def _search_serpapi(destination, check_in, check_out, nights, rooms, limit):
    if not SERPAPI_KEY or not check_in or not check_out:
        return []
    try:
        response = requests.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google_hotels",
                "q": f"hotels in {destination}",
                "check_in_date": str(check_in)[:10],
                "check_out_date": str(check_out)[:10],
                "adults": 2,  # per room, so the rate is a per-room nightly rate
                "currency": "INR",
                "gl": "in",
                "hl": "en",
                "api_key": SERPAPI_KEY,
            },
            timeout=45,
        )
        if response.status_code >= 400:
            print("SerpApi hotels error:", response.status_code, response.text[:300])
            return []
        properties = response.json().get("properties") or []
    except (requests.RequestException, ValueError) as error:
        print("SerpApi hotels failed:", error)
        return []

    hotels = []
    for prop in properties:
        if not isinstance(prop, dict):
            continue
        rate = prop.get("rate_per_night") or {}
        price = rate.get("extracted_lowest") if isinstance(rate, dict) else None
        if not isinstance(price, (int, float)) or price <= 0:
            continue
        images = prop.get("images") or []
        image_url = None
        if images and isinstance(images[0], dict):
            image_url = images[0].get("thumbnail") or images[0].get("original_image")
        gps = prop.get("gps_coordinates") or {}
        hotels.append(_finish({
            "hotel_name": prop.get("name") or "Hotel",
            "rating": prop.get("overall_rating"),
            "user_rating_count": prop.get("reviews"),
            "hotel_class": prop.get("hotel_class"),
            "address": prop.get("description") or None,
            "google_maps_url": (
                f"https://www.google.com/maps/search/?api=1&query={gps.get('latitude')},{gps.get('longitude')}"
                if gps.get("latitude") else None
            ),
            "booking_url": prop.get("link"),
            "image_url": image_url,
            "photo_names": [],
            "price_per_room_night": float(price),
            "price_type": "live",
            "price_source": "Google Hotels via SerpApi",
        }, nights, rooms))
        if len(hotels) >= limit:
            break
    return hotels


# ------------------------------------------------------------------
# 2) Google Places  (real names, estimated or range price)
# ------------------------------------------------------------------
def _range_midpoint(price_range):
    if not isinstance(price_range, dict):
        return None
    try:
        start = price_range.get("startPrice") or {}
        end = price_range.get("endPrice") or {}
        if start.get("currencyCode") not in (None, "INR"):
            return None
        low = float(start.get("units")) if start.get("units") is not None else None
        high = float(end.get("units")) if end.get("units") is not None else None
    except (TypeError, ValueError):
        return None
    values = [v for v in (low, high) if v is not None and v >= 300]
    return sum(values) / len(values) if values else None


def _search_places(destination, nights, rooms, limit):
    if not GOOGLE_MAPS_API_KEY:
        return []
    try:
        response = requests.post(
            "https://places.googleapis.com/v1/places:searchText",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": (
                    "places.displayName,places.formattedAddress,places.rating,"
                    "places.userRatingCount,places.googleMapsUri,places.photos.name,"
                    "places.priceLevel,places.priceRange,places.websiteUri"
                ),
            },
            json={
                "textQuery": f"hotels in {destination}",
                "includedType": "lodging",
                "pageSize": max(limit, 8),
                "languageCode": "en",
            },
            timeout=20,
        )
        if response.status_code >= 400:
            print("Places hotels error:", response.status_code, response.text[:300])
            return []
        places = response.json().get("places") or []
    except (requests.RequestException, ValueError) as error:
        print("Places hotels failed:", error)
        return []

    hotels = []
    for place in places:
        name = (place.get("displayName") or {}).get("text")
        if not name:
            continue
        midpoint = _range_midpoint(place.get("priceRange"))
        level = place.get("priceLevel")
        if midpoint:
            per_room, price_type, source = midpoint, "google_range", "Google Maps price range (indicative)"
        else:
            per_room = PRICE_LEVEL_ESTIMATE_INR.get(level, DEFAULT_ROOM_NIGHT_INR)
            price_type = "estimate"
            source = "Estimated from Google price level" if level in PRICE_LEVEL_ESTIMATE_INR else "Planning estimate (no price data)"
        photos = [p.get("name") for p in (place.get("photos") or [])[:3] if isinstance(p, dict) and p.get("name")]
        hotels.append(_finish({
            "hotel_name": name,
            "rating": place.get("rating"),
            "user_rating_count": place.get("userRatingCount"),
            "address": place.get("formattedAddress"),
            "google_maps_url": place.get("googleMapsUri"),
            "booking_url": place.get("websiteUri"),
            "image_url": None,
            "photo_names": photos,
            "price_per_room_night": float(round(per_room, 2)),
            "price_type": price_type,
            "price_source": source,
        }, nights, rooms))
        if len(hotels) >= limit:
            break
    return hotels


# ------------------------------------------------------------------
# public entry point
# ------------------------------------------------------------------
def search_hotels(destination, check_in, check_out, travelers, limit=6):
    nights = nights_between(check_in, check_out)
    rooms = rooms_needed(travelers)

    hotels = _search_serpapi(destination, check_in, check_out, nights, rooms, limit)
    if hotels:
        return hotels
    hotels = _search_places(destination, nights, rooms, limit)
    if hotels:
        return hotels

    return [_finish({
        "hotel_name": "Typical budget hotel (planning estimate)",
        "rating": None,
        "user_rating_count": None,
        "address": None,
        "google_maps_url": None,
        "booking_url": None,
        "image_url": None,
        "photo_names": [],
        "price_per_room_night": DEFAULT_ROOM_NIGHT_INR,
        "price_type": "estimate",
        "price_source": "Planning allowance — no hotel provider configured",
    }, nights, rooms)]
