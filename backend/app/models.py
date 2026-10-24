from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    Text,
    Numeric,
    DateTime,
    Date,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .database import Base


# ============================================
# USER MODEL
# ============================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    name = Column(String(100), nullable=False)

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = Column(Text, nullable=False)

    is_verified = Column(
        Boolean,
        default=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ============================================
# OTP MODEL
# ============================================

class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    email = Column(
        String(255),
        nullable=False,
        index=True
    )

    otp = Column(
        String(6),
        nullable=False
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ============================================
# TRIP MODEL
# ============================================

class Trip(Base):
    __tablename__ = "trips"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    source = Column(
        String(100),
        nullable=True
    )

    destination = Column(
        String(100),
        nullable=False
    )

    budget = Column(
        Numeric(12, 2),
        nullable=False
    )

    travelers = Column(
        Integer,
        nullable=False
    )

    days = Column(
        Integer,
        nullable=False
    )

    transport_option = Column(
        String(20),
        nullable=False
    )

    departure_date = Column(Date, nullable=True)
    return_date = Column(Date, nullable=True)

    total_estimated_cost = Column(
        Numeric(12, 2),
        nullable=True
    )

    remaining_budget = Column(
        Numeric(12, 2),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ============================================
# ITINERARY MODEL
# ============================================

class Itinerary(Base):
    __tablename__ = "itineraries"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    trip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    day_number = Column(
        Integer,
        nullable=False
    )

    title = Column(
        String(255),
        nullable=False
    )

    activities = Column(
        Text,
        nullable=True
    )

    estimated_cost = Column(
        Numeric(12, 2),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ============================================
# TRANSPORT MODEL
# ============================================

class TransportOption(Base):
    __tablename__ = "transport_options"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    trip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    transport_type = Column(
        String(20),
        nullable=False
    )

    estimated_price = Column(
        Numeric(12, 2),
        nullable=True
    )

    travel_time = Column(
        String(100),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ============================================
# HOTEL MODEL
# ============================================

class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    trip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    hotel_name = Column(
        String(255),
        nullable=False
    )

    location = Column(
        String(255),
        nullable=True
    )

    price_per_night = Column(
        Numeric(12, 2),
        nullable=True
    )

    total_price = Column(
        Numeric(12, 2),
        nullable=True
    )

    rating = Column(
        Numeric(3, 1),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ============================================
# PLACE MODEL
# ============================================

class Place(Base):
    __tablename__ = "places"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    trip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    place_name = Column(
        String(255),
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    estimated_cost = Column(
        Numeric(12, 2),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )