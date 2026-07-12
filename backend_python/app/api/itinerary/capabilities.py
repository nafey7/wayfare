"""Capabilities API endpoints for n8n Itinerary Agent integration.

This module exposes backend functionality as HTTP endpoints that n8n can
call during the CREATE_ITINERARY flow. It wraps existing LangGraph tools
and services to provide a consistent API for:
- Airport/location resolution
- Date parsing
- Flight search
- Hotel search (endpoint only, no n8n integration yet)
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.itinerary.schemas import (
    AirportInfo,
    CuratedFlight,
    DisambiguationType,
    FlightInfo,
    FlightSearchSummary,
    LocationOption,
    LocationStatus,
    NearbyAirport,
    ParseDatesRequest,
    ParseDatesResponse,
    ResolveLocationRequest,
    ResolveLocationResponse,
    SearchFlightsRequest,
    SearchFlightsResponse,
    SearchHotelsRequest,
    SearchHotelsResponse,
)
from app.core.config import settings
from app.shared.geocoding import GeocodingService

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Authentication
# =============================================================================


async def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> str:
    """Verify the n8n API key.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The verified API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Get expected API key from settings
    expected_key = getattr(settings, "N8N_CAPABILITIES_API_KEY", None)

    # In development, allow missing key
    if settings.ENVIRONMENT == "development" and not expected_key:
        logger.warning("N8N_CAPABILITIES_API_KEY not configured, allowing request")
        return "dev-mode"

    if not x_api_key:
        logger.warning("Missing X-API-Key header in capabilities request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    if x_api_key != expected_key:
        logger.warning("Invalid X-API-Key in capabilities request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return x_api_key


# =============================================================================
# Resolve Location
# =============================================================================


@router.post(
    "/resolve-location",
    response_model=ResolveLocationResponse,
    summary="Resolve location to airport(s)",
    description="Resolve a city name, airport code, or airport name to IATA code(s)",
)
async def resolve_location(
    request: ResolveLocationRequest,
    _api_key: str = Depends(verify_api_key),  # Used for auth, not in function body
) -> ResolveLocationResponse:
    """Resolve a location (city/airport) to IATA code(s).

    This endpoint wraps the AirportService to provide:
    - Direct IATA/ICAO code resolution
    - City-based airport lookup
    - Disambiguation for ambiguous cities (Birmingham UK vs USA)
    - Nearby airport suggestions for cities without airports

    Args:
        request: Location resolution request
        _api_key: Verified API key (used for auth via Depends)

    Returns:
        ResolveLocationResponse with status and resolved data
    """
    start_time = time.time()
    query = request.query.strip()

    logger.info(f"resolve-location: query='{query}', context={request.context}")

    try:
        from app.domains.airport import get_airport_service
        from app.domains.airport.models import ResolveContext

        service = get_airport_service()

        # Build context from request
        context = None
        if request.context and request.context.country_hint:
            context = ResolveContext(country_hint=request.context.country_hint)

        # Resolve the location
        result = await service.resolve(query, context)

        elapsed = time.time() - start_time

        # Handle resolved status
        if result.status == "resolved":
            airport = result.airport

            # Check if city has multiple airports (needs user choice)
            if result.needs_airport_preference and result.all_airports:
                airports_list = result.all_airports[:5]

                # Detect if this is a "no own airport" case by comparing
                # query city with airport cities. If none match, it means
                # these are nearby airports, not airports IN the city.
                query_lower = query.lower().strip()
                has_own_airport = any(
                    a.city.lower().strip() == query_lower for a in airports_list
                )

                if not has_own_airport:
                    # City has no own airport - return nearby airports
                    logger.info(
                        f"resolve-location: no_own_airport for '{query}', "
                        f"nearby={[a.iata for a in airports_list]}, elapsed={elapsed:.3f}s"
                    )
                    return ResolveLocationResponse(
                        status=LocationStatus.NO_OWN_AIRPORT,
                        original_city=query.title(),
                        nearest_airports=[
                            NearbyAirport(
                                iata=a.iata,
                                name=a.name,
                                distance_km=None,  # Distance not available here
                            )
                            for a in airports_list
                        ],
                        suggested_prompt=(
                            f"{query.title()} doesn't have its own airport. "
                            f"Nearest options:\n"
                            + "\n".join(
                                f"  {i + 1}. {a.name} ({a.iata})"
                                for i, a in enumerate(airports_list)
                            )
                        ),
                    )

                # Multi-airport city (e.g., London, Paris)
                logger.info(
                    f"resolve-location: needs_user_choice for '{query}', "
                    f"airports={[a.iata for a in airports_list]}, elapsed={elapsed:.3f}s"
                )
                return ResolveLocationResponse(
                    status=LocationStatus.NEEDS_USER_CHOICE,
                    all_options=[
                        AirportInfo(
                            iata=a.iata,
                            name=a.name,
                            city=a.city,
                            country=a.country,
                            lat=a.lat,
                            lng=a.lon,
                        )
                        for a in airports_list
                    ],
                    suggested_prompt=(
                        f"{query.title()} has multiple airports. Which do you prefer?\n"
                        + "\n".join(
                            f"  {i + 1}. {a.name} ({a.iata})"
                            for i, a in enumerate(airports_list)
                        )
                    ),
                )

            # Single airport resolved
            logger.info(
                f"resolve-location: resolved '{query}' -> {airport.iata if airport else 'None'}, "
                f"elapsed={elapsed:.3f}s"
            )
            return ResolveLocationResponse(
                status=LocationStatus.RESOLVED,
                location=AirportInfo(
                    iata=airport.iata if airport else "",
                    name=airport.name if airport else "",
                    city=airport.city if airport else None,
                    country=airport.country if airport else None,
                    lat=airport.lat if airport else None,
                    lng=airport.lon if airport else None,
                )
                if airport
                else None,
                all_options=[
                    AirportInfo(
                        iata=airport.iata,
                        name=airport.name,
                        city=airport.city,
                        country=airport.country,
                        lat=airport.lat,
                        lng=airport.lon,
                    )
                ]
                if airport
                else None,
            )

        # Handle needs_disambiguation status
        if result.status == "needs_disambiguation":
            logger.info(
                f"resolve-location: needs_disambiguation for '{query}', "
                f"type={result.disambiguation_type}, options={len(result.options or [])}, "
                f"elapsed={elapsed:.3f}s"
            )
            return ResolveLocationResponse(
                status=LocationStatus.NEEDS_DISAMBIGUATION,
                disambiguation_type=DisambiguationType(result.disambiguation_type.value)
                if result.disambiguation_type
                else None,
                options=[
                    LocationOption(
                        display=opt.display_name,
                        airports=[
                            AirportInfo(
                                iata=a.iata,
                                name=a.name,
                                city=a.city,
                                country=a.country,
                                lat=a.lat,
                                lng=a.lon,
                            )
                            for a in opt.airports[:3]
                        ],
                    )
                    for opt in (result.options or [])
                ],
                suggested_prompt=result.suggested_prompt,
            )

        # Check if this is a city without its own airport
        # Try to find nearby airports using geocoding
        geocoding = GeocodingService()
        geo_results = await geocoding.geocode_city(query)

        if geo_results and geo_results[0].lat and geo_results[0].lng:
            geo = geo_results[0]
            nearby = service.get_nearby_airports(
                geo.lat, geo.lng, radius_km=150, limit=5
            )

            if nearby:
                logger.info(
                    f"resolve-location: no_own_airport for '{query}', "
                    f"nearby={[a.iata for a, _ in nearby[:3]]}, elapsed={elapsed:.3f}s"
                )
                return ResolveLocationResponse(
                    status=LocationStatus.NO_OWN_AIRPORT,
                    original_city=geo.city or query,
                    nearest_airports=[
                        NearbyAirport(
                            iata=airport.iata,
                            name=airport.name,
                            distance_km=int(distance),
                        )
                        for airport, distance in nearby
                    ],
                    suggested_prompt=(
                        f"{query} doesn't have its own airport. Nearest options:\n"
                        + "\n".join(
                            f"  {i + 1}. {a.name} ({a.iata}) - {int(d)} km"
                            for i, (a, d) in enumerate(nearby[:5])
                        )
                    ),
                )

        # Not found
        logger.warning(
            f"resolve-location: not_found for '{query}', elapsed={elapsed:.3f}s"
        )
        return ResolveLocationResponse(
            status=LocationStatus.NOT_FOUND,
            error=f"No airports found for '{query}'",
            suggested_prompt=f"I couldn't find airports for '{query}'. "
            "Could you check the spelling or try a different city name?",
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"resolve-location: error for '{query}': {e}, elapsed={elapsed:.3f}s",
            exc_info=True,
        )
        return ResolveLocationResponse(
            status=LocationStatus.NOT_FOUND,
            error=f"Error resolving location: {e!s}",
        )


# =============================================================================
# Parse Dates
# =============================================================================


@router.post(
    "/parse-dates",
    response_model=ParseDatesResponse,
    summary="Parse natural language dates",
    description="Convert natural language date expressions to ISO format dates",
)
async def parse_dates(
    request: ParseDatesRequest,
    _api_key: str = Depends(verify_api_key),  # Used for auth, not in function body
) -> ParseDatesResponse:
    """Parse natural language date expressions.

    This endpoint wraps the DateParser utility to handle:
    - Relative dates: "tomorrow", "next Tuesday", "in 2 weeks"
    - Absolute dates: "January 15", "15/01/2025", "Jan 15th"
    - Date ranges: "Monday to Friday", "Dec 5-10", "for a week"

    Args:
        request: Date parsing request
        _api_key: Verified API key (used for auth via Depends)

    Returns:
        ParseDatesResponse with parsed dates or error
    """
    start_time = time.time()
    expression = request.expression.strip()

    logger.info(f"parse-dates: expression='{expression}'")

    try:
        # Import the parse_dates tool (it's synchronous)
        from app.ai.graph.tools.dates import parse_dates as parse_dates_tool

        # Call the tool
        result = parse_dates_tool.invoke({"text": expression})

        elapsed = time.time() - start_time

        # Check for errors
        if result.get("error"):
            logger.warning(
                f"parse-dates: error for '{expression}': {result['error']}, "
                f"elapsed={elapsed:.3f}s"
            )
            return ParseDatesResponse(
                status="error",
                parsed_from=expression,
                error=result["error"],
                suggestion=result.get("instruction") or result.get("suggestion"),
            )

        # Extract dates
        departure_date = result.get("departure_date")
        return_date = result.get("return_date")

        # Calculate trip days
        trip_days = None
        if departure_date and return_date:
            try:
                dep = datetime.strptime(departure_date, "%Y-%m-%d")
                ret = datetime.strptime(return_date, "%Y-%m-%d")
                trip_days = (ret - dep).days
            except ValueError:
                pass

        # Determine journey type
        journey_type = "Return" if return_date else "OneWay"

        logger.info(
            f"parse-dates: success for '{expression}' -> "
            f"departure={departure_date}, return={return_date}, "
            f"elapsed={elapsed:.3f}s"
        )

        return ParseDatesResponse(
            status="success",
            departure_date=departure_date,
            return_date=return_date,
            trip_days=trip_days,
            journey_type=journey_type,
            parsed_from=expression,
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"parse-dates: error for '{expression}': {e}, elapsed={elapsed:.3f}s",
            exc_info=True,
        )
        return ParseDatesResponse(
            status="error",
            parsed_from=expression,
            error=f"Error parsing dates: {e!s}",
        )


# =============================================================================
# Search Flights
# =============================================================================


@router.post(
    "/search-flights",
    response_model=SearchFlightsResponse,
    summary="Search for flights",
    description="Search for flights and return curated results",
)
async def search_flights(
    request: SearchFlightsRequest,
    _api_key: str = Depends(verify_api_key),  # Used for auth, not in function body
) -> SearchFlightsResponse:
    """Search for available flights.

    This endpoint wraps the search_flights tool to provide:
    - Flight search via FlightLogic API
    - Curated results (cheapest, fastest, best value)
    - Summary with price range and direct flight count

    Args:
        request: Flight search request
        _api_key: Verified API key (used for auth via Depends)

    Returns:
        SearchFlightsResponse with curated results or error
    """
    start_time = time.time()
    search_id = f"FL_{uuid.uuid4().hex[:8]}"

    logger.info(
        f"search-flights: {request.origin_iata} -> {request.destination_iata}, "
        f"departure={request.departure_date}, return={request.return_date}, "
        f"adults={request.adults}, session={request.session_id}"
    )

    try:
        # Issue #1034: call the internal ``_do_flight_search`` helper directly
        # rather than the @tool wrapper. The @tool uses
        # ``response_format="content_and_artifact"`` so ``.ainvoke(plain_dict)``
        # returns only the content (summary + instruction) — flights, search_params
        # and session_id live on the artifact and would be inaccessible from
        # here. The helper returns the full unsplit dict, matching how
        # ``_search_single_date`` calls into the same function.
        from app.ai.graph.tools.flights import _do_flight_search

        result = await _do_flight_search(
            origin=request.origin_iata.upper(),
            destination=request.destination_iata.upper(),
            departure_date=request.departure_date,
            return_date=request.return_date,
            adults=request.adults,
            children=request.children,
            infants=request.infants,
        )

        elapsed = time.time() - start_time

        # Check for errors
        if result.get("error"):
            logger.warning(
                f"search-flights: error {search_id}: {result['error']}, "
                f"elapsed={elapsed:.3f}s"
            )
            return SearchFlightsResponse(
                status="error",
                search_id=search_id,
                error=result["error"],
                suggestion=result.get("instruction"),
            )

        # Check for no results
        if result.get("status") == "no_results":
            logger.info(
                f"search-flights: no_results {search_id}, elapsed={elapsed:.3f}s"
            )
            return SearchFlightsResponse(
                status="no_results",
                search_id=search_id,
                suggestion=result.get("suggestion", "Try different dates or airports."),
            )

        # Issue #1034: tool now emits a flat best-value-sorted list.
        # Expose the top flight as `curated.best_value` for n8n; cheapest/fastest
        # buckets no longer exist (n8n consumers should switch to `all_flights`).
        flights = result.get("flights", []) or []
        summary_data = result.get("summary", {})

        # Convert to response format
        def convert_flight(f: dict) -> FlightInfo:
            return FlightInfo(
                id=f.get("id", ""),
                departure_time=f.get("departure_time", ""),
                departure_date=f.get("departure_date", ""),
                arrival_time=f.get("arrival_time", ""),
                arrival_date=f.get("arrival_date", ""),
                origin_code=f.get("origin_code", ""),
                origin_city=f.get("origin_city"),
                destination_code=f.get("destination_code", ""),
                destination_city=f.get("destination_city"),
                duration=f.get("duration", ""),
                duration_minutes=f.get("duration_minutes", 0),
                stops=f.get("stops", 0),
                price=f.get("price", 0),
                currency=f.get("currency", "EUR"),
                airline=f.get("airline", ""),
                airline_code=f.get("airline_code"),
                flight_number=f.get("flight_number"),
                segments=f.get("segments"),
            )

        curated: dict[str, CuratedFlight] = {}
        if flights:
            curated["best_value"] = CuratedFlight(
                label="Best Value",
                flight=convert_flight(flights[0]),
            )

        logger.info(
            f"search-flights: success {search_id}, "
            f"found={summary_data.get('total_found', 0)}, elapsed={elapsed:.3f}s"
        )

        return SearchFlightsResponse(
            status="success",
            search_id=search_id,
            summary=FlightSearchSummary(
                total_found=summary_data.get("total_found", 0),
                direct_flights=summary_data.get("direct_flights", 0),
                price_range=summary_data.get("price_range", {}),
            ),
            curated=curated if curated else None,
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(
            f"search-flights: error {search_id}: {e}, elapsed={elapsed:.3f}s",
            exc_info=True,
        )
        return SearchFlightsResponse(
            status="error",
            search_id=search_id,
            error=f"Error searching flights: {e!s}",
            suggestion="Please try again or contact support.",
        )


# =============================================================================
# Search Hotels (Endpoint only, no n8n integration)
# =============================================================================


@router.post(
    "/search-hotels",
    response_model=SearchHotelsResponse,
    summary="Search for hotels (Coming Soon)",
    description="Search for hotels - endpoint placeholder for future n8n integration",
    deprecated=True,
)
async def search_hotels(
    request: SearchHotelsRequest,
    _api_key: str = Depends(verify_api_key),  # Used for auth, not in function body
) -> SearchHotelsResponse:
    """Search for available hotels.

    NOTE: This endpoint is created for future integration but is not
    yet connected to n8n workflow.

    Args:
        request: Hotel search request
        _api_key: Verified API key (used for auth via Depends)

    Returns:
        SearchHotelsResponse with results or error
    """
    search_id = f"HT_{uuid.uuid4().hex[:8]}"

    logger.info(
        f"search-hotels: city={request.city}, "
        f"check_in={request.check_in}, check_out={request.check_out}, "
        f"rooms={request.rooms}, adults={request.adults}, session={request.session_id}"
    )

    # For now, return a placeholder response
    # Future: Implement actual hotel search
    return SearchHotelsResponse(
        status="error",
        search_id=search_id,
        error="Hotel search not yet implemented",
        suggestion="Hotel search will be available in a future update.",
    )


__all__ = ["router"]
