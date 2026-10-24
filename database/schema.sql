-- TripGenie schema for Supabase PostgreSQL. Run in Supabase SQL Editor.
-- Safe for repeated runs; ALTER statements add columns to an existing trips table.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_users_email ON public.users(email);

CREATE TABLE IF NOT EXISTS public.otp_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    otp VARCHAR(6) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_otp_verifications_email ON public.otp_verifications(email);

CREATE TABLE IF NOT EXISTS public.trips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    source VARCHAR(100),
    destination VARCHAR(100) NOT NULL,
    budget NUMERIC(12,2) NOT NULL,
    travelers INTEGER NOT NULL,
    days INTEGER NOT NULL,
    transport_option VARCHAR(20) NOT NULL,
    departure_date DATE,
    return_date DATE,
    total_estimated_cost NUMERIC(12,2),
    remaining_budget NUMERIC(12,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_trips_user_id ON public.trips(user_id);
ALTER TABLE public.trips ADD COLUMN IF NOT EXISTS departure_date DATE;
ALTER TABLE public.trips ADD COLUMN IF NOT EXISTS return_date DATE;
ALTER TABLE public.trips ADD COLUMN IF NOT EXISTS total_estimated_cost NUMERIC(12,2);
ALTER TABLE public.trips ADD COLUMN IF NOT EXISTS remaining_budget NUMERIC(12,2);

CREATE TABLE IF NOT EXISTS public.itineraries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    activities TEXT,
    estimated_cost NUMERIC(12,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_itineraries_trip_id ON public.itineraries(trip_id);

CREATE TABLE IF NOT EXISTS public.transport_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    transport_type VARCHAR(20) NOT NULL,
    estimated_price NUMERIC(12,2),
    travel_time VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_transport_options_trip_id ON public.transport_options(trip_id);

CREATE TABLE IF NOT EXISTS public.hotels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    hotel_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    price_per_night NUMERIC(12,2),
    total_price NUMERIC(12,2),
    rating NUMERIC(3,1),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_hotels_trip_id ON public.hotels(trip_id);

CREATE TABLE IF NOT EXISTS public.places (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
    place_name VARCHAR(255) NOT NULL,
    description TEXT,
    estimated_cost NUMERIC(12,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_places_trip_id ON public.places(trip_id);
