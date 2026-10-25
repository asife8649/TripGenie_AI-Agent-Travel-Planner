
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class TravelPlanRequest(BaseModel):
    source: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    budget_per_person: float = Field(..., gt=0)

    # No artificial maximum.
    travelers: int = Field(default=1, ge=1)

    # No artificial maximum.
    days: int = Field(default=1, ge=1)

    # flight | train | bus | both | all
    transport_option: str = "all"

    departure_date: Optional[date] = None
    return_date: Optional[date] = None


class SaveTripRequest(BaseModel):
    source: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    budget_per_person: float = Field(..., gt=0)
    travelers: int = Field(default=1, ge=1)
    days: int = Field(default=1, ge=1)
    transport_option: str = "all"
    departure_date: Optional[date] = None
    return_date: Optional[date] = None
    total_estimated_cost: Optional[float] = None
    remaining_budget: Optional[float] = None


class TransportOption(BaseModel):
    # flight | train | bus | mixed_public_transit
    transport_type: str

    price_per_person: Optional[float] = None
    total_price: Optional[float] = None
    currency: Optional[str] = None

    travel_time: Optional[str] = None

    source_airport: Optional[str] = None
    destination_airport: Optional[str] = None

    fare_available: bool = False

    # one_way | round_trip
    trip_type: Optional[str] = None

    # outbound | return | None for one-way
    direction: Optional[str] = None

    vehicle_types: List[str] = Field(default_factory=list)

    # v1.1 additions
    mode: Optional[str] = None
    from_name: Optional[str] = None
    to_name: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    operator: Optional[str] = None
    # live | estimate | indicative | unavailable
    price_type: Optional[str] = None
    class_fares: List[dict] = Field(default_factory=list)
    legs: List[dict] = Field(default_factory=list)


class HotelOption(BaseModel):
    hotel_name: str
    rating: Optional[float] = None

    # Final display fields. Example: "₹1,800.00"
    price_per_night: Optional[float] = None
    price_per_room_night: Optional[float] = None
    total_price: Optional[float] = None
    nights: Optional[int] = None
    rooms: Optional[int] = None
    # live | google_range | estimate
    price_type: Optional[str] = None
    address: Optional[str] = None


class PlaceOption(BaseModel):
    place_name: str
    description: Optional[str] = None

    # None means unknown, not free.
    estimated_cost: Optional[float] = None

    rating: float = 0.0
    user_rating_count: int = 0

    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_maps_url: Optional[str] = None
    photo_names: List[str] = Field(default_factory=list)


class ItineraryDay(BaseModel):
    day_number: int
    title: str
    activities: List[str]
    estimated_cost: Optional[float] = None


class BudgetSummary(BaseModel):
    total_transport: Optional[float] = None
    total_hotel: Optional[float] = None
    total_places: Optional[float] = None
    total_estimated_cost: Optional[float] = None
    remaining_budget: Optional[float] = None


class TravelPlanResponse(BaseModel):
    source: str
    destination: str
    budget_per_person: float
    total_budget: float
    travelers: int
    days: int
    departure_date: Optional[date] = None
    return_date: Optional[date] = None

    transport_options: List[TransportOption] = Field(default_factory=list)
    hotels: List[HotelOption] = Field(default_factory=list)
    places: List[PlaceOption] = Field(default_factory=list)

    # None means the complete trip cost could not be calculated
    # because one or more required prices were unavailable.
    total_estimated_cost: Optional[float] = None
    remaining_budget: Optional[float] = None

    itinerary: List[ItineraryDay] = Field(default_factory=list)
