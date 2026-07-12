"""Direct itinerary generation endpoint (POST /api/itinerary/generate).

Calls generate_itinerary tool directly — no LLM message parsing, no hotel/flight
side searches. Designed for the Day Plan tab "Plan a trip" form.
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.domains.auth.dependencies import require_authenticated
from app.domains.saved_itinerary import SavedItineraryCreate, create_saved_itinerary
from app.domains.user.schemas import UserPublic

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateItineraryRequest(BaseModel):
    destination: str = Field(
        ..., min_length=1, description="Destination city, e.g. 'London'"
    )
    origin: str | None = Field(None, description="Departure city, e.g. 'Paris'")
    departure_date: str | None = Field(None, description="Departure date YYYY-MM-DD")
    return_date: str | None = Field(None, description="Return date YYYY-MM-DD")
    num_days: int = Field(
        0, ge=0, le=30, description="Trip duration in days (0 = derive from dates)"
    )
    adults: int = Field(1, ge=1, le=9)
    children: int = Field(0, ge=0, le=9)
    interests: list[str] = Field(default_factory=list)


class GenerateItineraryDirectResponse(BaseModel):
    saved_itinerary_id: str
    structured_itinerary: dict[str, Any]
    trip_meta: dict[str, Any]


@router.post(
    "/generate",
    response_model=GenerateItineraryDirectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate itinerary directly (no chat/LLM overhead)",
    description=(
        "Generates a structured itinerary by calling the planning tool directly, "
        "bypassing the chat supervisor and hotel/flight side searches. "
        "Saves the result to the user's saved itineraries and returns it."
    ),
)
async def generate_itinerary_direct(
    request: GenerateItineraryRequest,
    current_user: UserPublic = Depends(require_authenticated),
) -> GenerateItineraryDirectResponse:
    from app.ai.graph.tools.itinerary import generate_itinerary

    # skip_flights_requested bypasses the origin-required gate — the Day Plan
    # form is a day-plan-only surface and never fires hotel/flight side searches.
    config = RunnableConfig(configurable={"skip_flights_requested": True})

    content_str, itinerary_dict = await generate_itinerary.coroutine(
        destination=request.destination,
        origin=request.origin,
        departure_date=request.departure_date,
        return_date=request.return_date,
        num_days=request.num_days,
        adults=request.adults,
        children=request.children,
        interests=request.interests or [],
        config=config,
    )

    content = json.loads(content_str)
    if content.get("status") != "success":
        # Surface the tool's actionable message so the frontend can show it.
        detail = (
            content.get("message")
            or content.get("error")
            or "Itinerary generation failed"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        )

    trip_meta: dict[str, Any] = {
        "origin": request.origin,
        "destination": request.destination,
        "departure_date": request.departure_date,
        "return_date": request.return_date,
        "adults": request.adults,
        "children": request.children,
        "trip_type": "round_trip" if request.return_date else "one_way",
    }

    # Geocode origin + destination for map center
    try:
        from app.shared.geocoding import GeocodingService

        geocoding = GeocodingService()

        async def _geocode(city: str | None) -> dict[str, float] | None:
            if not city:
                return None
            try:
                results = await geocoding.geocode_city(city)
                if results:
                    return {"latitude": results[0].lat, "longitude": results[0].lng}
            except Exception:
                logger.debug("Geocoding failed for city %r", city, exc_info=True)
            return None

        origin_loc, dest_loc = await asyncio.gather(
            _geocode(request.origin),
            _geocode(request.destination),
        )
        if origin_loc:
            trip_meta["origin_location"] = origin_loc
        if dest_loc:
            trip_meta["destination_location"] = dest_loc
    except Exception:
        logger.debug(
            "Geocoding setup failed in generate_itinerary_direct", exc_info=True
        )

    saved = await create_saved_itinerary(
        str(current_user.id),
        SavedItineraryCreate(
            structured_itinerary=itinerary_dict,
            trip_meta=trip_meta,
        ),
    )

    return GenerateItineraryDirectResponse(
        saved_itinerary_id=saved.id,
        structured_itinerary=itinerary_dict,
        trip_meta=trip_meta,
    )
