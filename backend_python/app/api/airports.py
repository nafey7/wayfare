"""Airport API endpoints.

Provides airport resolution and search functionality.
"""

import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.domains.airport import airport_resolver
from app.domains.flight.schemas import AirportListRequest
from app.domains.flight.service import FlightService, get_flight_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/airports", tags=["Airports"])


def _lat_lon_from_mwgg_airport_dict(
    airport_info: dict[str, Any] | None,
) -> tuple[Optional[float], Optional[float]]:
    """Extract coordinates from mwgg/Airports raw airport record."""
    if not airport_info:
        return None, None
    lat_raw, lon_raw = airport_info.get("lat"), airport_info.get("lon")
    if lat_raw is None or lon_raw is None:
        return None, None
    try:
        return float(lat_raw), float(lon_raw)
    except (TypeError, ValueError):
        return None, None


async def _coordinates_for_iata_from_mwgg(
    iata_code: str,
) -> tuple[Optional[float], Optional[float]]:
    """Lat/lon from mwgg dataset for any resolved IATA (e.g. map markers when FlightLogic resolved the code)."""
    await airport_resolver.ensure_loaded()
    raw = await airport_resolver.get_airport_info(iata_code)
    return _lat_lon_from_mwgg_airport_dict(raw)


class AirportResolveResponse(BaseModel):
    """Airport resolution response"""

    iata_code: str = Field(..., description="Resolved IATA code")
    name: Optional[str] = Field(None, description="Airport name")
    city: Optional[str] = Field(None, description="City name")
    country: Optional[str] = Field(None, description="Country name")
    latitude: Optional[float] = Field(
        None, description="Latitude from airport database (mwgg), when available"
    )
    longitude: Optional[float] = Field(
        None, description="Longitude from airport database (mwgg), when available"
    )


class AirportSearchResult(BaseModel):
    """Airport search result"""

    iata: str = Field(..., description="IATA code")
    name: str = Field(..., description="Airport name")
    city: str = Field(..., description="City name")
    state: Optional[str] = Field(None, description="State/Province name")
    country: str = Field(..., description="Country name")


@router.get("/resolve", response_model=AirportResolveResponse)
async def resolve_airport(
    query: str = Query(..., description="City name, airport name, or IATA/ICAO code"),
    service: FlightService = Depends(get_flight_service),
) -> AirportResolveResponse:
    """
    Resolve city name, airport name, or code to IATA airport code.

    Uses either mwgg/Airports (default) or FlightLogic API based on
    VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS environment variable.

    Supports:
    - City names: "New York", "London", "Paris"
    - Airport names: "John F Kennedy International"
    - IATA codes: "JFK", "LHR", "CDG"
    - ICAO codes: "KJFK", "EGLL", "LFPG" (only with mwgg, not FlightLogic)
    """
    try:
        if settings.VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS:
            # Use FlightLogic API
            logger.info(f"Using FlightLogic API for airport resolution: '{query}'")
            iata_code = await service.resolve_airport(query)

            if not iata_code:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Could not resolve airport: {query}",
                )

            # Get full airport information
            airport_info = await service.get_airport_info(iata_code)

            if not airport_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Airport info not found for: {iata_code}",
                )

            lat_fl, lon_fl = await _coordinates_for_iata_from_mwgg(
                airport_info["iata_code"]
            )
            return AirportResolveResponse(
                iata_code=airport_info["iata_code"],
                name=airport_info.get("airport_name") or airport_info.get("name"),
                city=airport_info.get("city"),
                country=airport_info.get("country"),
                latitude=lat_fl,
                longitude=lon_fl,
            )

        # Use mwgg/Airports (default)
        logger.info(f"Using mwgg/Airports for airport resolution: '{query}'")
        iata_code = await airport_resolver.resolve_airport(query)

        if not iata_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not resolve airport: {query}",
            )

        # Get additional airport details
        airport_info = await airport_resolver.get_airport_info(iata_code)
        lat_m, lon_m = _lat_lon_from_mwgg_airport_dict(airport_info)

        return AirportResolveResponse(
            iata_code=iata_code,
            name=airport_info.get("name") if airport_info else None,
            city=airport_info.get("city") if airport_info else None,
            country=airport_info.get("country") if airport_info else None,
            latitude=lat_m,
            longitude=lon_m,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Airport resolution failed for '{query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Airport resolution service error",
        ) from e


@router.get("/search", response_model=list[AirportSearchResult])
async def search_airports(
    query: str = Query(
        ..., description="City name, airport name, country, or IATA code"
    ),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    service: FlightService = Depends(get_flight_service),
) -> list[AirportSearchResult]:
    """
    Search airports by city name, airport name, country, or IATA code.

    Returns multiple matching airports sorted by relevance.

    Uses either mwgg/Airports (default) or FlightLogic API based on
    VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS environment variable.

    Supports:
    - City names: "Goa", "New York", "London"
    - Airport names: "John F Kennedy International"
    - IATA codes: "GOI", "JFK", "LHR"
    - Country names: "India", "United States"
    - State names: "Goa" (only with mwgg, not FlightLogic)
    """
    try:
        if settings.VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS:
            # Use FlightLogic API
            logger.info(f"Using FlightLogic API for airport search: '{query}'")
            # Get airport list from FlightLogic (cached with 24h TTL)
            airport_list_response = await service.get_airport_list(
                AirportListRequest.model_validate({})
            )
            airports = airport_list_response.airports

            query_lower = query.lower().strip()
            query_upper = query.upper().strip()
            query_words = set(query_lower.split())

            results: list[dict[str, Any]] = []

            # Search through FlightLogic airports
            for airport in airports:
                iata = airport.iata_code.strip().upper()
                if not iata or len(iata) != 3:
                    continue

                name = airport.airport_name.lower()
                city = airport.city.lower()
                country = airport.country.lower()

                score = 0

                # Priority 1: Exact IATA code match (highest priority)
                if query_upper == iata:
                    score = 200
                # Priority 2: Exact city name match (very high priority)
                elif query_lower == city:
                    score = 195
                # Priority 3: Airport name starts with query or query is a whole word in name
                elif (
                    name.startswith(query_lower)
                    or f" {query_lower} " in f" {name} "
                    or name.endswith(f" {query_lower}")
                    or name.startswith(f"{query_lower} ")
                ):
                    score = 130
                # Priority 4: Exact matches for country
                elif query_lower == country:
                    score = 100
                # Priority 5: City name starts with query
                elif city.startswith(query_lower):
                    score = 110
                # Priority 6: IATA code contains query
                elif query_upper in iata:
                    score = 90
                # Priority 7: Country starts with query
                elif country.startswith(query_lower):
                    score = 80
                # Priority 8: Query contained in city (partial match)
                elif query_lower in city:
                    score = 60
                # Priority 9: Query contained in country (partial match)
                elif query_lower in country:
                    score = 50
                # Priority 10: Query contained in airport name as substring
                elif query_lower in name:
                    score = 35
                else:
                    # Priority 11: Word-based matching
                    city_words = set(city.split())
                    name_words = set(name.split())
                    country_words = set(country.split())

                    city_overlap = len(query_words & city_words)
                    name_overlap = len(query_words & name_words)
                    country_overlap = len(query_words & country_words)

                    if city_overlap > 0:
                        score = city_overlap * 20
                    elif country_overlap > 0:
                        score = country_overlap * 15
                    elif name_overlap > 0:
                        score = name_overlap * 10

                if score > 0:
                    results.append(
                        {
                            "score": score,
                            "iata": iata,
                            "name": airport.airport_name,
                            "city": airport.city,
                            "country": airport.country,
                        }
                    )

            # Sort by score and return top results
            results.sort(key=lambda x: int(x["score"]), reverse=True)
            results = results[:limit]

            # Convert to response models (state is None for FlightLogic data)
            return [
                AirportSearchResult(
                    iata=str(result["iata"]),
                    name=str(result["name"]),
                    city=str(result["city"]),
                    state=None,  # FlightLogic doesn't provide state
                    country=str(result["country"]),
                )
                for result in results
            ]

        # Use mwgg/Airports (default)
        logger.info(f"Using mwgg/Airports for airport search: '{query}'")
        await airport_resolver.ensure_loaded()

        # Scoring is CPU-bound over ~29K airports; offload to a worker thread
        # so the event loop stays free for concurrent requests.
        mwgg_results = await asyncio.to_thread(
            airport_resolver.search_mwgg_sync, query, limit
        )

        return [
            AirportSearchResult(
                iata=str(result["iata"]),
                name=str(result["name"]),
                city=str(result["city"]),
                state=(str(s) if (s := result.get("state")) else None),
                country=str(result["country"]),
            )
            for result in mwgg_results
        ]
    except Exception as e:
        logger.error(f"Airport search failed for '{query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Airport search service error",
        ) from e
