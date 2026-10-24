
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi import HTTPException, Query
import requests
from sqlalchemy import text

from .database import engine
from .routers.auth import router as auth_router
from .routers.trips import router as trips_router


app = FastAPI(
    title="TripGenie API",
    description="AI Multi-Agent Travel Planner API",
    version="1.0.0",
)

from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://trip-genie-ai-multi-agent-travel-pl.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth_router)
app.include_router(trips_router)


@app.get("/")
def root():
    return {
        "message": "TripGenie API is running!"
    }


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception:
        # Return a non-2xx status so deployment health checks do not mistake
        # a database outage or invalid DATABASE_URL for a healthy service.
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "not connected",
            },
        )


@app.get("/places/photo")
def place_photo(photo_name: str = Query(..., min_length=1, max_length=1000), max_width: int = Query(1000, ge=200, le=1600)):
    """Proxy Google Places photo media without exposing the API key to the frontend."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Google Places photo service is not configured")
    if not photo_name.startswith("places/") or "/photos/" not in photo_name:
        raise HTTPException(status_code=400, detail="Invalid photo reference")
    try:
        response = requests.get(
            f"https://places.googleapis.com/v1/{photo_name}/media",
            params={"maxWidthPx": max_width, "key": api_key},
            timeout=15,
            allow_redirects=True,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "image/jpeg")
        if not content_type.startswith("image/"):
            raise HTTPException(status_code=502, detail="Photo provider did not return an image")
        return Response(content=response.content, media_type=content_type, headers={"Cache-Control": "public, max-age=3600"})
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail="Could not load place photo from Google Places") from error
