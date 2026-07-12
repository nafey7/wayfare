"""Geocoding API endpoints.

Provides city-to-country resolution using Google Geocoding API.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.shared.geocoding import GeocodingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/geocoding", tags=["Geocoding"])

# Initialize geocoding service instance
_geocoding_service = GeocodingService()


class GeocodingResolveResponse(BaseModel):
    """Geocoding resolution response - single result (most relevant)."""

    city: str = Field(..., description="City name")
    country: str = Field(..., description="Full country name (e.g., 'France')")
    country_code: str = Field(
        ..., description="ISO 3166-1 alpha-2 country code (e.g., 'FR')"
    )
    formatted_address: str = Field(
        ..., description="Full formatted address from Google"
    )
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")


class GeocodingResolveAllResponse(BaseModel):
    """Geocoding resolution response - all results (for ambiguous cities)."""

    results: list[GeocodingResolveResponse] = Field(
        ..., description="List of geocoding results, sorted by relevance"
    )


@router.get("/resolve", response_model=GeocodingResolveResponse)
async def resolve_city(
    city: str = Query(
        ..., description="City name to geocode (e.g., 'Paris', 'London', 'New York')"
    ),
) -> GeocodingResolveResponse:
    """
    Resolve city name to country and location details.

    Returns the most relevant (first) result. For ambiguous cities (e.g., "Birmingham"
    exists in both UK and USA), this returns the most relevant match.

    Use /api/geocoding/resolve-all if you need all possible matches for disambiguation.

    Supports:
    - City names: "Paris", "London", "New York"
    - City with country: "Paris, France" (helps disambiguation)
    """
    try:
        results = await _geocoding_service.geocode_city(city)

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not resolve city: {city}",
            )

        # Return the first (most relevant) result
        result = results[0]

        return GeocodingResolveResponse(
            city=result.city,
            country=result.country,
            country_code=result.country_code,
            formatted_address=result.formatted_address,
            lat=result.lat,
            lng=result.lng,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Geocoding resolution failed for '{city}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Geocoding service error",
        ) from e


@router.get("/resolve-all", response_model=GeocodingResolveAllResponse)
async def resolve_city_all(
    city: str = Query(
        ..., description="City name to geocode (e.g., 'Birmingham', 'Utrecht')"
    ),
) -> GeocodingResolveAllResponse:
    """
    Resolve city name to all possible country matches.

    Useful for ambiguous city names that exist in multiple countries.
    Returns all results sorted by relevance (most relevant first).

    Example ambiguous cities:
    - "Birmingham" -> UK and USA
    - "Utrecht" -> Netherlands and South Africa
    - "Cambridge" -> UK and USA
    """
    try:
        results = await _geocoding_service.geocode_city(city)

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not resolve city: {city}",
            )

        # Convert all results to response format
        response_results = [
            GeocodingResolveResponse(
                city=result.city,
                country=result.country,
                country_code=result.country_code,
                formatted_address=result.formatted_address,
                lat=result.lat,
                lng=result.lng,
            )
            for result in results
        ]

        return GeocodingResolveAllResponse(results=response_results)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Geocoding resolution failed for '{city}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Geocoding service error",
        ) from e
