import os

import requests
from dotenv import load_dotenv


load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


def search_tourist_places(destination: str, limit: int = 8):

    if not GOOGLE_MAPS_API_KEY:
        raise ValueError(
            "GOOGLE_MAPS_API_KEY is not set in .env"
        )

    url = "https://places.googleapis.com/v1/places:searchText"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "places.displayName,"
            "places.formattedAddress,"
            "places.rating,"
            "places.userRatingCount,"
            "places.googleMapsUri,"
            "places.photos.name,"
            "places.location,"
            "places.primaryType"
        )
    }

    payload = {
        "textQuery": f"best tourist attractions in {destination}",
        "pageSize": limit,
        "languageCode": "en"
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    results = []

    for place in data.get("places", []):

        display_name = place.get("displayName", {})
        location = place.get("location", {})

        photo_names = [
            photo.get("name")
            for photo in place.get("photos", [])[:5]
            if isinstance(photo, dict) and photo.get("name")
        ]

        results.append({
            "place_name": display_name.get(
                "text",
                "Unknown place"
            ),

            "description": place.get(
                "primaryType",
                "Tourist attraction"
            ),

            "estimated_cost": 0,

            "rating": place.get(
                "rating",
                0
            ),

            "user_rating_count": place.get(
                "userRatingCount",
                0
            ),

            "address": place.get(
                "formattedAddress",
                ""
            ),

            "latitude": location.get(
                "latitude"
            ),

            "longitude": location.get(
                "longitude"
            ),

            "google_maps_url": place.get(
                "googleMapsUri",
                ""
            ),
            "photo_names": photo_names,
        })

    return results