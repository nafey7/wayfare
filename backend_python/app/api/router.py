"""Assembled API router with all business endpoints.

This module performs the heavy imports (airports, chat, flights, hotels, etc.)
so that individual API modules (e.g. app.api.places) can be imported in isolation
for testing without pulling in those dependencies.
"""

from fastapi import APIRouter

from app.api import (
    airports,
    auth,
    chat,
    config,
    flights,
    geocoding,
    hotels,
    places,
    public_chat,
    public_places,
    transit,
    user,
    vouchers,
)
from app.api.admin import admin_router
from app.api.itinerary import itinerary_router
from app.api.saved_itineraries import router as saved_itineraries_router

api_router = APIRouter()

# Include business endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(user.router, prefix="/user", tags=["User"])
api_router.include_router(vouchers.router, prefix="/vouchers")
api_router.include_router(chat.router, tags=["Chat"])
api_router.include_router(public_chat.router)
api_router.include_router(public_places.router)
api_router.include_router(airports.router, tags=["Airports"])
api_router.include_router(geocoding.router, tags=["Geocoding"])
api_router.include_router(places.router, tags=["Places"])
api_router.include_router(flights.router, tags=["Flights"])
api_router.include_router(hotels.router, tags=["Hotels"])
api_router.include_router(transit.router, tags=["Transit"])
api_router.include_router(config.router, prefix="/config", tags=["Configuration"])

# Include itinerary capabilities API (for n8n integration)
api_router.include_router(itinerary_router, prefix="/itinerary", tags=["Itinerary"])

# Saved itineraries (user-saved AI-generated itineraries)
api_router.include_router(
    saved_itineraries_router,
    prefix="/itineraries",
    tags=["Saved Itineraries"],
)

# Include admin/debug endpoints
api_router.include_router(admin_router, prefix="/admin")
