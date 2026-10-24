from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, Trip
from ..schemas import TravelPlanRequest, SaveTripRequest
from ..agents.travel_agents import TravelCoordinator

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.post("/plan")
def create_travel_plan(
    request: TravelPlanRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        coordinator = TravelCoordinator()

        result = coordinator.create_plan(
            source=request.source,
            destination=request.destination,
            budget_per_person=request.budget_per_person,
            travelers=request.travelers,
            days=request.days,
            transport_option=request.transport_option,
            departure_date=request.departure_date,
            return_date=request.return_date,
        )

        return result

    except HTTPException:
        raise

    except Exception as e:
        print("\n" + "=" * 60)
        print("TRIP PLAN ERROR")
        print("=" * 60)
        print(str(e))
        print("=" * 60 + "\n")

        raise HTTPException(
            500,
            "Could not generate travel plan. Check backend logs and provider configuration.",
        )


@router.post("/save")
def save_trip(
    request: SaveTripRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        trip = Trip(
            user_id=current_user.id,
            source=request.source,
            destination=request.destination,
            budget=request.budget_per_person,
            travelers=request.travelers,
            days=request.days,
            transport_option=request.transport_option,
            departure_date=request.departure_date,
            return_date=request.return_date,
            total_estimated_cost=request.total_estimated_cost,
            remaining_budget=request.remaining_budget,
        )

        db.add(trip)
        db.commit()
        db.refresh(trip)

        return {
            "message": "Trip saved successfully",
            "trip": {
                "id": str(trip.id),
                "source": trip.source,
                "destination": trip.destination,
                "budget": float(trip.budget),
                "travelers": trip.travelers,
                "days": trip.days,
                "transport_option": trip.transport_option,
            },
        }

    except Exception as e:
        db.rollback()

        print("\nTRIP SAVE ERROR:", str(e))

        raise HTTPException(
            500,
            "Could not save trip. Check backend logs and database configuration.",
        )


@router.get("/mine")
def get_my_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    trips = (
        db.query(Trip)
        .filter(Trip.user_id == current_user.id)
        .order_by(Trip.created_at.desc())
        .all()
    )

    result = []

    for trip in trips:
        result.append({
            "id": str(trip.id),
            "source": trip.source,
            "destination": trip.destination,
            "budget": float(trip.budget),
            "travelers": trip.travelers,
            "days": trip.days,
            "transport_option": trip.transport_option,
            "departure_date": trip.departure_date.isoformat() if trip.departure_date else None,
            "return_date": trip.return_date.isoformat() if trip.return_date else None,
            "total_estimated_cost": (
                float(trip.total_estimated_cost)
                if trip.total_estimated_cost is not None
                else None
            ),
            "remaining_budget": (
                float(trip.remaining_budget)
                if trip.remaining_budget is not None
                else None
            ),
            "created_at": (
                trip.created_at.isoformat()
                if trip.created_at
                else None
            ),
        })

    return result


@router.delete("/{trip_id}")
def delete_trip(
    trip_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        trip_uuid = UUID(str(trip_id))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(404, "Trip not found")

    trip = (
        db.query(Trip)
        .filter(
            Trip.id == trip_uuid,
            Trip.user_id == current_user.id,
        )
        .first()
    )

    if not trip:
        raise HTTPException(
            404,
            "Trip not found",
        )

    db.delete(trip)
    db.commit()

    return {
        "message": "Trip deleted successfully",
    }
