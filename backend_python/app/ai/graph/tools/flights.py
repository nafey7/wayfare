"""Flight search tool for LangGraph flight agent.

This tool wraps the FlightService to search for available flights
using the FlightLogic API.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Annotated, Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from pydantic import BaseModel, Field, model_validator

from app.ai.flight_scoring import (
    hour_from_time_str,
    sort_flights_by_best_value,
)
from app.ai.utils.error_message_generator import (
    detect_error_type,
    generate_error_message,
)
from app.domains.common import utc_date
from app.domains.flight.pricing import FLIGHTS_DISCOUNT_PERCENTAGE
from app.domains.flight.revalidation_filters import (
    filter_flights_after_revalidation,
)
from app.domains.flight.schemas import TimeWindow

logger = logging.getLogger(__name__)

# Cache for airport info to avoid repeated lookups
_airport_cache: dict[str, dict[str, str]] = {}

# Cache for FlightLogic-supported airport IATA codes.
# Populated on first unsupported-airport error; valid for 24 hours.
_fl_supported_airports_cache: set[str] = set()
_fl_supported_airports_fetched_at: float = 0.0
_FL_SUPPORTED_AIRPORTS_TTL = 24 * 60 * 60  # 24 hours


async def _get_fl_supported_airports() -> set[str]:
    """Return the set of IATA codes supported by FlightLogic.

    Fetches from /airport_list on first call (or after 24h TTL expires)
    and caches the result for the lifetime of the process. Falls back to
    an empty set on any error so the caller degrades gracefully (shows all
    nearby airports without FL-filtering rather than blocking the user).
    """
    global _fl_supported_airports_cache, _fl_supported_airports_fetched_at

    now = time.monotonic()
    if _fl_supported_airports_cache and (
        now - _fl_supported_airports_fetched_at < _FL_SUPPORTED_AIRPORTS_TTL
    ):
        return _fl_supported_airports_cache

    try:
        from app.domains.flight.schemas import AirportListRequest
        from integrations.flightlogic.client import FlightLogicClient

        client = FlightLogicClient()
        response = await client.get_airport_list(AirportListRequest())
        codes = {item.iata_code.upper() for item in response.airports if item.iata_code}
        logger.info("Cached %d FlightLogic-supported airports (TTL=24h)", len(codes))
        _fl_supported_airports_cache = codes
        _fl_supported_airports_fetched_at = now
        return codes
    except Exception:
        logger.warning(
            "Could not fetch FlightLogic airport list — nearby filtering disabled",
            exc_info=True,
        )
        return set()


# Time preference mappings (configurable)
TIME_PREFERENCE_WINDOWS = {
    "early_morning": {"min": "05:00", "max": "09:00"},
    "morning": {"min": "06:00", "max": "12:00"},
    "afternoon": {"min": "12:00", "max": "18:00"},
    "evening": {"min": "18:00", "max": "23:00"},
    "night": {"min": "23:00", "max": "05:00"},
}


def _split_search_result(
    result: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Split a flight-search result dict into a (content, artifact) tuple.

    Per issue #1034: the LLM never sees the heavy `flights` arrays. The
    public ``search_flights`` tool returns ``response_format="content_and_artifact"``;
    this helper performs the actual split.

    - For error / no_results / date_range_no_results / multicity_no_results
      → artifact=None (nothing heavy to hide).
    - For ``status="success"`` → flights array moves to artifact.
    - For ``status="multicity_results"`` → flights inside each leg move to artifact.
    - For ``status="date_range_results"`` → flights inside each date move to artifact.
    """
    status = result.get("status")
    if status not in ("success", "multicity_results", "date_range_results"):
        return result, None

    if status == "success":
        flights = result.get("flights", []) or []
        total = len(flights)
        artifact = {
            "session_id": result.get("session_id"),
            "search_params": result.get("search_params"),
            "summary": result.get("summary"),
            "origin_is_city": result.get("origin_is_city"),
            "destination_is_city": result.get("destination_is_city"),
            "origin_location": result.get("origin_location"),
            "destination_location": result.get("destination_location"),
            "flights": flights,
        }
        content = {
            "status": "success",
            "summary": result.get("summary"),
            "instruction": (
                f"Tell the user we found {total} flight options "
                f"— they're displayed above the chat. Booking is done by clicking "
                f"a card. Do NOT list flights in the chat reply."
            ),
        }
        return content, artifact

    if status == "multicity_results":
        legs = result.get("multicity_legs", []) or []
        artifact_legs = [dict(leg) for leg in legs]
        content_legs = [
            {k: v for k, v in leg.items() if k != "flights"} for leg in legs
        ]
        artifact = {**result, "multicity_legs": artifact_legs}
        content = {**result, "multicity_legs": content_legs}
        return content, artifact

    # date_range_results
    dates = result.get("dates", []) or []
    artifact_dates = [dict(d) for d in dates]
    content_dates = [{k: v for k, v in d.items() if k != "flights"} for d in dates]
    artifact = {**result, "dates": artifact_dates}
    content = {**result, "dates": content_dates}
    return content, artifact


def _map_time_preference_to_window(preference: str | None) -> TimeWindow | None:
    """Map time preference keyword to TimeWindow object.

    Args:
        preference: Time preference keyword (e.g., "morning", "afternoon", "evening")

    Returns:
        TimeWindow object with min/max times, or None if preference is invalid
    """
    if not preference:
        return None

    window_config = TIME_PREFERENCE_WINDOWS.get(preference.lower())
    if not window_config:
        logger.warning(f"Invalid time preference: {preference}")
        return None

    return TimeWindow(min=window_config["min"], max=window_config["max"])


async def _get_airport_names(iata_code: str) -> dict[str, str]:
    """Look up airport and city names from IATA code.

    Uses either mwgg/Airports (default) or FlightLogic API based on
    VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS environment variable.

    Returns dict with 'city' and 'name' keys, or empty strings if not found.
    """
    if not iata_code:
        return {"city": "", "name": ""}

    iata_code = iata_code.upper()
    if iata_code in _airport_cache:
        return _airport_cache[iata_code]

    try:
        from app.core.config import settings

        if settings.VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS:
            # Use FlightLogic API via FlightService
            logger.debug(
                f"Using FlightLogic API for airport name lookup in LangGraph tools: '{iata_code}'"
            )
            from app.domains.flight.service import FlightService

            flight_service = FlightService(current_user=None)
            airport_info = await flight_service.get_airport_info(iata_code)

            if airport_info:
                result = {
                    "city": airport_info.get("city", ""),
                    "name": airport_info.get("airport_name")
                    or airport_info.get("name", ""),
                }
            else:
                result = {"city": "", "name": ""}
        else:
            # Use mwgg/Airports (default)
            logger.debug(
                f"Using mwgg/Airports for airport name lookup in LangGraph tools: '{iata_code}'"
            )
            from app.domains.airport.airport_resolver import AirportResolver

            resolver = AirportResolver()
            airport_info = await resolver.get_airport_info(iata_code)

            if airport_info:
                result = {
                    "city": airport_info.get("city", ""),
                    "name": airport_info.get("name", ""),
                }
            else:
                result = {"city": "", "name": ""}

        _airport_cache[iata_code] = result
        return result

    except Exception as e:
        logger.warning(f"Failed to look up airport {iata_code}: {e}")
        return {"city": "", "name": ""}


async def _enrich_flights_with_airport_names(
    flights: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Enrich flight data with airport and city names from our database.

    Returns a new list with enriched flight data containing origin_city,
    origin_airport, destination_city, destination_airport, and segment names.
    """
    # Collect all unique airport codes
    codes: set[str] = set()
    for flight in flights:
        if flight.get("origin_code"):
            codes.add(flight["origin_code"])
        if flight.get("destination_code"):
            codes.add(flight["destination_code"])
        for segment in flight.get("segments", []):
            if segment.get("departure_code"):
                codes.add(segment["departure_code"])
            if segment.get("destination_code"):
                codes.add(segment["destination_code"])

    # Look up all airport names
    airport_data: dict[str, dict[str, str]] = {}
    for code in codes:
        airport_data[code] = await _get_airport_names(code)

    # Build enriched flight list
    enriched_flights = []
    for flight in flights:
        enriched_flight = {**flight}  # Shallow copy
        origin = flight.get("origin_code", "")
        dest = flight.get("destination_code", "")

        if origin and origin in airport_data:
            if not enriched_flight.get("origin_city"):
                enriched_flight["origin_city"] = airport_data[origin]["city"]
            if not enriched_flight.get("origin_airport"):
                enriched_flight["origin_airport"] = airport_data[origin]["name"]

        if dest and dest in airport_data:
            if not enriched_flight.get("destination_city"):
                enriched_flight["destination_city"] = airport_data[dest]["city"]
            if not enriched_flight.get("destination_airport"):
                enriched_flight["destination_airport"] = airport_data[dest]["name"]

        # Enrich segments
        enriched_segments = []
        for segment in flight.get("segments", []):
            enriched_segment = {**segment}  # Shallow copy
            # Segments use origin_code, not departure_code
            dep_code = segment.get("origin_code", "")
            arr_code = segment.get("destination_code", "")

            if dep_code and dep_code in airport_data:
                # Fill origin_city if empty (FlightLogic often returns empty)
                if not enriched_segment.get("origin_city"):
                    enriched_segment["origin_city"] = airport_data[dep_code]["city"]
                if not enriched_segment.get("origin_airport"):
                    enriched_segment["origin_airport"] = airport_data[dep_code]["name"]

            if arr_code and arr_code in airport_data:
                if not enriched_segment.get("destination_city"):
                    enriched_segment["destination_city"] = airport_data[arr_code][
                        "city"
                    ]
                if not enriched_segment.get("destination_airport"):
                    enriched_segment["destination_airport"] = airport_data[arr_code][
                        "name"
                    ]

            enriched_segments.append(enriched_segment)

        enriched_flight["segments"] = enriched_segments
        enriched_flights.append(enriched_flight)

    return enriched_flights


def _apply_post_filters(
    flights: list[dict[str, Any]],
    max_stops: int | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    max_outbound_duration: float | None = None,
    max_inbound_duration: float | None = None,
) -> list[dict[str, Any]]:
    """Apply post-API filters to enriched flight results.

    These filters run AFTER the FlightLogic API call for filter types
    the API doesn't support natively:
    - max_stops > 0 (API only supports direct vs all)
    - price_min / price_max (not supported by API)
    - max_outbound_duration / max_inbound_duration (not supported by API)

    API-level filters (NOT handled here):
    - cabin_class → FlightSearchRequest.cabin_class
    - direct flights (max_stops=0) → FlightSearchRequest.direct_flight=1
    """
    filtered = flights

    if max_stops is not None and max_stops > 0:
        filtered = [f for f in filtered if f.get("stops", 0) <= max_stops]

    if price_min is not None or price_max is not None:
        filtered = [
            f
            for f in filtered
            if (price_min is None or f.get("price", 0) >= price_min)
            and (price_max is None or f.get("price", float("inf")) <= price_max)
        ]

    if max_outbound_duration is not None:
        max_outbound_minutes = max_outbound_duration * 60
        filtered = [
            f
            for f in filtered
            if f.get("outbound_duration_minutes") is None
            or f["outbound_duration_minutes"] <= max_outbound_minutes
        ]

    if max_inbound_duration is not None:
        max_inbound_minutes = max_inbound_duration * 60
        filtered = [
            f
            for f in filtered
            if f.get("inbound_duration_minutes") is None
            or f["inbound_duration_minutes"] <= max_inbound_minutes
        ]

    return filtered


# --- Output validation constants ---
MAX_FLIGHT_PRICE = 50_000
REQUIRED_FLIGHT_FIELDS = ("price", "duration_minutes", "airline", "segments")


def _validate_flight_results(
    flights: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate and filter flight results for data integrity.

    Removes flights with:
    - Price <= 0 or > MAX_FLIGHT_PRICE
    - Departure dates in the past
    - Missing required fields
    """
    today = utc_date()
    valid: list[dict[str, Any]] = []

    for flight in flights:
        # Check required fields
        if any(flight.get(f) is None for f in REQUIRED_FLIGHT_FIELDS):
            logger.warning(
                f"Flight {flight.get('id', '?')} missing required fields, skipping"
            )
            continue

        # Validate price
        price = flight.get("price", 0)
        if not (0 < price <= MAX_FLIGHT_PRICE):
            logger.warning(
                f"Flight {flight.get('id', '?')} has invalid price {price}, skipping"
            )
            continue

        # Validate departure date is not in the past
        dep_date_str = flight.get("departure_date", "")
        if dep_date_str and isinstance(dep_date_str, str):
            try:
                dep_date = datetime.strptime(dep_date_str, "%Y-%m-%d").date()
                if dep_date < today:
                    logger.warning(
                        f"Flight {flight.get('id', '?')} departs in the past ({dep_date_str}), skipping"
                    )
                    continue
            except ValueError:
                pass  # Can't parse — let it through, don't block on format

        valid.append(flight)

    if len(valid) < len(flights):
        logger.info(
            f"Flight validation: {len(flights)} → {len(valid)} "
            f"({len(flights) - len(valid)} filtered out)"
        )

    return valid


class FlightSearchInput(BaseModel):
    """Input schema for flight search.

    Three modes:
    - One-way / Round-trip: provide ``origin``, ``destination``, ``departure_date`` (and optionally ``return_date``).
    - Date-range: provide ``origin``, ``destination``, ``departure_dates`` list (and ``departure_window_end``).
    - Multi-city (Circle): provide ``segments`` list only; omit origin / destination / departure_date.
    """

    # ── Single-trip fields (one-way / round-trip / date-range) ──────────────────────────
    origin: str | None = Field(
        default=None,
        description=(
            "Origin airport IATA code (e.g., 'LHR'). "
            "Required for one-way/round-trip/date-range. Omit when using 'segments' for multi-city."
        ),
    )
    destination: str | None = Field(
        default=None,
        description=(
            "Destination airport IATA code (e.g., 'CDG'). "
            "Required for one-way/round-trip/date-range. Omit when using 'segments' for multi-city."
        ),
    )
    departure_date: str | None = Field(
        default=None,
        description=(
            "Departure date in YYYY-MM-DD format for single-date search. "
            "Required for one-way/round-trip. Omit when using 'segments' or 'departure_dates'. "
            "Provide this OR departure_dates, not both."
        ),
    )
    departure_dates: list[str] | None = Field(
        default=None,
        max_length=6,
        description=(
            "List of departure dates (YYYY-MM-DD) for date-range search (max 6). "
            "Used when parse_dates returns is_departure_window=True. "
            "Provide this OR departure_date, not both."
        ),
    )
    departure_window_end: str | None = Field(
        default=None,
        description=(
            "Full window end date (YYYY-MM-DD) for date-range search. "
            "Used to determine if more chunks exist beyond departure_dates."
        ),
    )
    trip_type: str | None = Field(
        default=None,
        description=(
            "The user's explicitly stated trip type: 'one-way' or 'round-trip'. "
            "Required for one-way/round-trip. Omit when using 'segments' for multi-city. "
            "You MUST have asked the user and received a clear answer before setting this. "
            "A single departure date does NOT mean one-way. "
            "The only exceptions: user said 'one-way'/'round-trip'/'return', "
            "or parse_dates returned both departure and return dates."
        ),
    )
    return_date: str | None = Field(
        default=None,
        description="Return date in YYYY-MM-DD format. Required when trip_type='round-trip', leave None for one-way.",
    )

    # ── Multi-city field ────────────────────────────────────────────────────
    segments: list[dict[str, str]] | None = Field(
        default=None,
        description=(
            "For multi-city (Circle) trips only. "
            "List of leg dicts, e.g. "
            '[{"origin":"LHR","destination":"CDG","departure_date":"2026-05-01"},'
            ' {"origin":"CDG","destination":"FCO","departure_date":"2026-05-08"}]. '
            "When provided, omit 'origin', 'destination', 'departure_date'."
        ),
    )

    @model_validator(mode="after")
    def validate_search_mode(self) -> "FlightSearchInput":
        if self.segments:
            # Multi-city mode — single-trip fields not needed
            return self
        # Single-trip / date-range mode — require origin and destination
        # Date validation (departure_date vs departure_dates) is done inside the tool
        missing = [
            field
            for field, val in [
                ("origin", self.origin),
                ("destination", self.destination),
            ]
            if not val
        ]
        if missing:
            raise ValueError(
                f"For one-way/round-trip/date-range search, '{', '.join(missing)}' is required. "
                "Use 'segments' instead for multi-city trips."
            )
        return self

    adults: int = Field(
        ge=1,
        le=9,
        description="Number of adult passengers. NEVER default to 1 — you MUST ask the user how many passengers before calling this tool.",
    )
    children: int = Field(default=0, ge=0, description="Number of children")
    infants: int = Field(default=0, ge=0, description="Number of infants")
    origin_is_city: bool = Field(
        default=True,
        description=(
            "MUST equal `query_is_city_name` from the LATEST resolve_airport(role='origin') "
            "call in this turn. True for city queries ('London', 'NYC') → searches all "
            "airports in the city; False for specific airport queries ('Gatwick', "
            "'Heathrow', 'LHR') → searches that airport only. Do NOT carry over the value "
            "from a previous turn — re-read the latest resolve_airport result every turn."
        ),
    )
    destination_is_city: bool = Field(
        default=True,
        description=(
            "MUST equal `query_is_city_name` from the LATEST resolve_airport(role='destination') "
            "call in this turn. True for city queries ('Paris', 'NYC'); False for specific "
            "airport queries ('CDG', 'JFK Airport'). Do NOT carry over from a previous turn."
        ),
    )
    departure_time_preference: str | None = Field(
        default=None,
        description="Preferred departure time: 'early_morning' (5-9 AM), 'morning' (6 AM-12 PM), 'afternoon' (12-6 PM), 'evening' (6-11 PM), or 'night' (11 PM-5 AM)",
    )
    arrival_time_preference: str | None = Field(
        default=None,
        description=(
            "Preferred arrival time: 'early_morning' (5-9 AM), 'morning' (6 AM-12 PM), "
            "'afternoon' (12-6 PM), 'evening' (6-11 PM), or 'night' (11 PM-5 AM). "
            "For 'arrive by X' or 'land before X', pick the window that ENDS at or before X. "
            "E.g. 'arrive by 3 pm' → 'morning' (flights arriving before noon), "
            "'arrive by 6 pm' → 'afternoon', 'arrive by noon' → 'morning'."
        ),
    )

    # Flight filters
    cabin_class: str | None = Field(
        default=None,
        description=(
            "Cabin class filter: 'economy', 'premium_economy', 'business', or 'first'. "
            "Extract from user message. Passed to FlightLogic API directly."
        ),
    )
    max_stops: int | None = Field(
        default=None,
        ge=0,
        le=3,
        description=(
            "Maximum number of stops. 0 = direct/non-stop, 1 = one stop, 2+ = multiple stops. "
            "ONLY set this when the user explicitly says 'direct', 'non-stop', or 'no stops'. "
            "Do NOT infer from arrival time preferences like 'arrive by 3 pm' — use arrival_time instead. "
            "Leave as null (default) to get all flights including connections."
        ),
    )
    price_min: float | None = Field(
        default=None,
        ge=0,
        description="Minimum price filter (numeric value only, ignore currency symbols). Extract from 'minimum 200', 'at least 300', 'over $200'.",
    )
    price_max: float | None = Field(
        default=None,
        ge=0,
        description="Maximum price filter (numeric value only, ignore currency symbols). Extract from 'under 500', 'below $600', 'max €450'.",
    )
    preferred_airline: str | None = Field(
        default=None,
        description=(
            "Preferred airline IATA code (e.g., 'BA', 'EK', 'LH'). "
            "Extract from 'British Airways', 'Emirates', 'Lufthansa', etc."
        ),
    )
    max_outbound_duration: float | None = Field(
        default=None,
        gt=0,  # gt=0 (not ge=0): 0-hour duration is meaningless, minimum useful is 0.5 (30 min)
        description=(
            "Maximum outbound flight duration in hours (decimal). "
            "Extract from 'max 3 hour flight', 'under 2.5 hours', 'flights shorter than 4 hours'."
        ),
    )
    max_inbound_duration: float | None = Field(
        default=None,
        gt=0,  # gt=0 (not ge=0): 0-hour duration is meaningless, minimum useful is 0.5 (30 min)
        description=(
            "Maximum inbound/return flight duration in hours (decimal). "
            "Extract from 'max 3 hours each way', 'return under 4 hours'. "
            "Only set for round-trips when user specifies inbound duration."
        ),
    )


async def _search_multicity(
    segments_input: list[dict[str, str]],
    adults: int,
    children: int,
    infants: int,
    cabin_class: str | None,
) -> dict[str, Any]:
    """Handle multi-city (Circle) flight search: N parallel OneWay leg searches.

    Builds a JourneyType.CIRCLE request, calls FlightService (which internally
    runs _search_multicity_parallel), best-value-sorts each leg's flights and
    revalidates the top fares.

    Returns a dict with ``status="multicity_results"`` and ``multicity_legs`` list.
    """
    from datetime import datetime as _dt

    from app.domains.flight.enums import CabinClass, JourneyType
    from app.domains.flight.schemas import (
        AirportInfo,
        FlightSearchRequest,
        OriginDestinationSegment,
    )
    from app.domains.flight.service import FlightService

    if len(segments_input) < 2:
        return {
            "status": "error",
            "error": "Multi-city search requires at least 2 segments.",
            "instruction": "Ask the user for all legs of their multi-city trip before searching.",
        }

    # ── Validate and build segments ────────────────────────────────────────
    leg_segments: list[OriginDestinationSegment] = []
    for i, seg in enumerate(segments_input):
        origin = str(seg.get("origin", "")).upper()
        destination = str(seg.get("destination", "")).upper()
        dep_date_str = str(seg.get("departure_date", ""))

        if len(origin) != 3 or len(destination) != 3:
            return {
                "status": "error",
                "error": f"Segment {i}: invalid IATA codes (origin={origin}, destination={destination}).",
                "instruction": "Use resolve_airport to get valid 3-letter IATA codes for each leg.",
            }
        if origin == destination:
            return {
                "status": "error",
                "error": f"Segment {i}: origin and destination cannot be the same ({origin}).",
                "instruction": f"Check segment {i}: origin and destination are the same airport.",
            }
        try:
            dep_date = _dt.strptime(dep_date_str, "%Y-%m-%d").date()
        except ValueError:
            return {
                "status": "error",
                "error": f"Segment {i}: invalid departure_date '{dep_date_str}'. Use YYYY-MM-DD.",
                "instruction": "Use parse_dates to get dates in YYYY-MM-DD format for each leg.",
            }

        leg_segments.append(
            OriginDestinationSegment(
                departure_date=dep_date,
                return_date=None,
                origin_airport=AirportInfo(
                    iata_code=origin,
                    icao_code=None,
                    airport_name=None,
                    city_name=None,
                    country_code=None,
                ),
                destination_airport=AirportInfo(
                    iata_code=destination,
                    icao_code=None,
                    airport_name=None,
                    city_name=None,
                    country_code=None,
                ),
            )
        )

    # ── Map cabin class ────────────────────────────────────────────────────
    CABIN_CLASS_MAP = {
        "economy": CabinClass.ECONOMY,
        "premium_economy": CabinClass.PREMIUM_ECONOMY,
        "business": CabinClass.BUSINESS,
        "first": CabinClass.FIRST,
    }
    cabin_class_enum = (
        CABIN_CLASS_MAP.get(cabin_class.lower(), CabinClass.ECONOMY)
        if cabin_class
        else CabinClass.ECONOMY
    )

    # ── Build and execute request ──────────────────────────────────────────
    request = FlightSearchRequest(
        user_id=None,
        user_password=None,
        access=None,
        ip_address=None,
        required_currency_code=None,
        journey_type=JourneyType.CIRCLE,
        origin_destination_info=leg_segments,
        cabin_class=cabin_class_enum,
        adults=adults,
        children=children,
        infants=infants,
        preferred_airline=None,
        direct_flight=None,
        filters=None,
        revalidate_flights_count=0,
        city_wise_search_origin=True,
        city_wise_search_destination=True,
    )

    service = FlightService(current_user=None)
    try:
        response = await service.search_flights(request)
    except Exception as e:
        logger.exception("Multicity search error: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "instruction": "Inform the user about the search error and suggest trying again.",
        }

    if not response.multicity_legs:
        return {
            "status": "no_results",
            "message": "No results returned for multi-city search.",
            "instruction": (
                "No multi-city flights found. Call find_nearby_airports() for any "
                "small or regional airports in the itinerary and suggest alternative "
                "routes. Do NOT just tell the user to try again."
            ),
        }

    # ── Per-leg curation pipeline ──────────────────────────────────────────
    processed_legs: list[dict[str, Any]] = []
    for leg in response.multicity_legs:
        leg_flights: list[dict[str, Any]] = []
        for itinerary in leg.fare_itineraries:
            flight_info = _extract_flight_info(itinerary)
            if flight_info:
                leg_flights.append(flight_info)

        if not leg_flights:
            leg_errors = [e.message for e in (leg.errors or [])]
            processed_legs.append(
                {
                    "leg_index": leg.leg_index,
                    "origin": leg.origin,
                    "destination": leg.destination,
                    "departure_date": leg.departure_date.isoformat(),
                    "session_id": leg.session_id,
                    "summary": {
                        "total_flights": 0,
                        "direct_count": 0,
                        "price_range": {},
                    },
                    "flights": [],
                    "errors": leg_errors if leg_errors else None,
                }
            )
            continue

        leg_flights = await _enrich_flights_with_airport_names(leg_flights)
        leg_flights = _validate_flight_results(leg_flights)

        # Issue #1034: single best-value sort over the FULL leg result set.
        # No cheapest/fastest buckets, no truncation — frontend handles its
        # own filter/sort UI on the flat list.
        sorted_flights = sort_flights_by_best_value(
            leg_flights,
            get_price=lambda f: f["price"],
            get_duration=lambda f: f["duration_minutes"],
            get_departure_hour=lambda f: hour_from_time_str(f.get("departure_time")),
            get_arrival_hour=lambda f: hour_from_time_str(f.get("arrival_time")),
            get_return_departure_hour=lambda f: hour_from_time_str(
                f.get("return_departure_time")
            ),
            get_return_arrival_hour=lambda f: hour_from_time_str(
                f.get("return_arrival_time")
            ),
        )

        if leg.session_id:

            def _fare_source(flight_item: object) -> str | None:
                if isinstance(flight_item, dict):
                    val = flight_item.get("id")
                    return str(val) if val is not None else None
                return None

            sorted_flights = await filter_flights_after_revalidation(
                session_id=leg.session_id,
                flights=sorted_flights,
                adults=adults,
                children=children,
                infants=infants,
                revalidate_fn=service.revalidate_fare,
                get_fare_source_code=_fare_source,
            )

        prices = [f["price"] for f in sorted_flights]
        processed_legs.append(
            {
                "leg_index": leg.leg_index,
                "origin": leg.origin,
                "destination": leg.destination,
                "departure_date": leg.departure_date.isoformat(),
                "session_id": leg.session_id,
                "summary": {
                    "total_flights": len(sorted_flights),
                    "direct_count": sum(
                        1 for f in sorted_flights if f.get("stops", 0) == 0
                    ),
                    "price_range": {
                        "min": min(prices) if prices else 0,
                        "max": max(prices) if prices else 0,
                        "currency": sorted_flights[0].get("currency", "GBP")
                        if sorted_flights
                        else "GBP",
                    },
                },
                "flights": sorted_flights,
            }
        )

    total_results = sum(
        lg.get("summary", {}).get("total_flights", 0) for lg in processed_legs
    )
    if total_results == 0:
        return {
            "status": "no_results",
            "message": "No flights found for any leg of the multi-city itinerary.",
            "instruction": (
                "No flights found for any leg. Call find_nearby_airports() for the "
                "smallest airports in the itinerary and suggest alternative routes. "
                "Do NOT just tell the user to try different dates."
            ),
        }

    logger.info(
        "Multicity search: %d legs, %d total flights",
        len(processed_legs),
        total_results,
    )
    return {
        "status": "multicity_results",
        "multicity_legs": processed_legs,
        "search_params": {
            "journey_type": "Circle",
            "adults": adults,
            "children": children,
            "infants": infants,
            "cabin_class": cabin_class.capitalize() if cabin_class else "Economy",
        },
        "instruction": (
            "Present these multi-city flight options. "
            "Ask the user which flight they'd like for each leg."
        ),
    }


# ── Date-range search helpers ────────────────────────────────────────


async def _search_single_date(
    date_str: str,
    *,
    origin: str,
    destination: str,
    trip_type: str,
    adults: int,
    children: int,
    infants: int,
    origin_is_city: bool,
    destination_is_city: bool,
    departure_time_preference: str | None,
    arrival_time_preference: str | None,
    cabin_class: str | None,
    max_stops: int | None,
    price_min: float | None,
    price_max: float | None,
    preferred_airline: str | None,
    max_outbound_duration: float | None,
    max_inbound_duration: float | None,
) -> dict[str, Any]:
    """Run a single-date search and return per-date result dict.

    Returns:
        {date, available, session_id, flights, summary} on success, or
        {date, available: False} on failure / no results.
    """
    try:
        # Call the internal helper directly (not the @tool) so we get the full
        # dict back. The @tool would split into content/artifact and we'd only
        # get content, losing the flights list (#1034).
        result = await _do_flight_search(
            origin=origin,
            destination=destination,
            trip_type=trip_type,
            departure_date=date_str,
            adults=adults,
            children=children,
            infants=infants,
            origin_is_city=origin_is_city,
            destination_is_city=destination_is_city,
            departure_time_preference=departure_time_preference,
            arrival_time_preference=arrival_time_preference,
            cabin_class=cabin_class,
            max_stops=max_stops,
            price_min=price_min,
            price_max=price_max,
            preferred_airline=preferred_airline,
            max_outbound_duration=max_outbound_duration,
            max_inbound_duration=max_inbound_duration,
        )

        if result.get("status") == "success":
            return {
                "date": date_str,
                "available": True,
                "session_id": result.get("session_id", ""),
                "flights": result.get("flights", []),
                "summary": result.get("summary", {}),
                "origin_location": result.get("origin_location"),
                "destination_location": result.get("destination_location"),
            }
        return {"date": date_str, "available": False}

    except Exception as e:
        logger.warning("Date-range search failed for %s: %s", date_str, e)
        return {"date": date_str, "available": False}


def _aggregate_date_range_results(
    dates: list[str],
    results: list[dict[str, Any] | BaseException],
    window_end: str | None,
) -> dict[str, Any]:
    """Aggregate parallel per-date search results into a single response.

    Args:
        dates: The dates that were searched.
        results: Per-date result dicts (or exceptions from asyncio.gather).
        window_end: The full departure window end date (to calculate has_more).

    Returns:
        Aggregated response with per-date data, overall best, and chunk info.
    """
    per_date: list[dict[str, Any]] = []
    for i, r in enumerate(results):
        date_str = dates[i] if i < len(dates) else "unknown"
        if isinstance(r, BaseException):
            per_date.append({"date": date_str, "available": False})
            continue
        if not isinstance(r, dict):
            per_date.append({"date": date_str, "available": False})
            continue

        if r.get("available"):
            day_name = datetime.strptime(r["date"], "%Y-%m-%d").strftime("%A")
            per_date.append(
                {
                    "date": r["date"],
                    "day_name": day_name,
                    "available": True,
                    "session_id": r.get("session_id", ""),
                    "flights": r.get("flights", []),
                    "summary": r.get("summary", {}),
                    "origin_location": r.get("origin_location"),
                    "destination_location": r.get("destination_location"),
                }
            )
        else:
            per_date.append({"date": r.get("date", date_str), "available": False})

    available_dates = [d for d in per_date if d.get("available")]

    # All dates unavailable
    if not available_dates:
        searched_from = dates[0] if dates else ""
        searched_to = dates[-1] if dates else ""
        has_more = False
        next_chunk_start = None
        next_chunk_end = None
        if window_end and searched_to and searched_to < window_end:
            has_more = True
            next_start = datetime.strptime(searched_to, "%Y-%m-%d").date() + timedelta(
                days=1
            )
            next_end = min(
                next_start + timedelta(days=5),
                datetime.strptime(window_end, "%Y-%m-%d").date(),
            )
            next_chunk_start = next_start.strftime("%Y-%m-%d")
            next_chunk_end = next_end.strftime("%Y-%m-%d")
        return {
            "status": "date_range_no_results",
            "searched_from": searched_from,
            "searched_to": searched_to,
            "has_more": has_more,
            "next_chunk_start": next_chunk_start,
            "next_chunk_end": next_chunk_end,
            "instruction": (
                "No flights found for any date in this window. "
                "If has_more is True, automatically check the next chunk before "
                "telling the user. Otherwise inform user and suggest different dates or route."
            ),
        }

    # Issue #1034: single overall winner across dates — the top of each date's
    # best-value-sorted list, then pick the one with the lowest score (best).
    overall_best: dict[str, Any] | None = None
    for d in available_dates:
        flights = d.get("flights", [])
        if not flights:
            continue
        top = flights[0]
        if overall_best is None or top.get(
            "best_value_score", float("inf")
        ) < overall_best.get("best_value_score", float("inf")):
            overall_best = {**top, "date": d["date"]}

    searched_from = dates[0]
    searched_to = dates[-1]
    has_more = False
    next_chunk_start = None
    next_chunk_end = None

    if window_end and searched_to < window_end:
        has_more = True
        next_start = datetime.strptime(searched_to, "%Y-%m-%d").date() + timedelta(
            days=1
        )
        next_end = min(
            next_start + timedelta(days=5),
            datetime.strptime(window_end, "%Y-%m-%d").date(),
        )
        next_chunk_start = next_start.strftime("%Y-%m-%d")
        next_chunk_end = next_end.strftime("%Y-%m-%d")

    return {
        "status": "date_range_results",
        "dates": per_date,
        "overall_best": overall_best,
        "searched_from": searched_from,
        "searched_to": searched_to,
        "has_more": has_more,
        "next_chunk_start": next_chunk_start,
        "next_chunk_end": next_chunk_end,
        "instruction": (
            "Present a brief text summary using the overall_best section: mention the date range searched, "
            "then describe overall_best (date, price, airline, duration). "
            + (
                f"Ask: 'Want me to check the next 6 days ({next_chunk_start} to {next_chunk_end}) too?' "
                if has_more
                else "Ask: 'Which date works best for you?' "
            )
            + "Do NOT show flight cards in chat — the full per-date breakdown is on the recommendations page."
        ),
    }


async def _search_date_range(
    *,
    origin: str,
    destination: str,
    departure_dates: list[str],
    departure_window_end: str | None,
    adults: int,
    children: int,
    infants: int,
    origin_is_city: bool,
    destination_is_city: bool,
    departure_time_preference: str | None,
    arrival_time_preference: str | None,
    cabin_class: str | None,
    max_stops: int | None,
    price_min: float | None,
    price_max: float | None,
    preferred_airline: str | None,
    max_outbound_duration: float | None,
    max_inbound_duration: float | None,
) -> dict[str, Any]:
    """Run parallel flight searches for multiple dates and aggregate results."""
    logger.info(
        "Date-range search: %d dates (%s to %s), window_end=%s",
        len(departure_dates),
        departure_dates[0],
        departure_dates[-1],
        departure_window_end,
    )

    search_kwargs = {
        "origin": origin,
        "destination": destination,
        "trip_type": "one-way",  # date-range searches are always one-way per date
        "adults": adults,
        "children": children,
        "infants": infants,
        "origin_is_city": origin_is_city,
        "destination_is_city": destination_is_city,
        "departure_time_preference": departure_time_preference,
        "arrival_time_preference": arrival_time_preference,
        "cabin_class": cabin_class,
        "max_stops": max_stops,
        "price_min": price_min,
        "price_max": price_max,
        "preferred_airline": preferred_airline,
        "max_outbound_duration": max_outbound_duration,
        "max_inbound_duration": max_inbound_duration,
    }

    tasks = [_search_single_date(d, **search_kwargs) for d in departure_dates]  # type: ignore[arg-type]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return _aggregate_date_range_results(
        dates=departure_dates,
        results=list(results),
        window_end=departure_window_end,
    )


async def _do_flight_search(
    adults: int,
    origin: str | None = None,
    destination: str | None = None,
    trip_type: str | None = None,
    departure_date: str | None = None,
    departure_dates: list[str] | None = None,
    departure_window_end: str | None = None,
    segments: list[dict[str, str]] | None = None,
    return_date: str | None = None,
    children: int = 0,
    infants: int = 0,
    origin_is_city: bool = True,
    destination_is_city: bool = True,
    departure_time_preference: str | None = None,
    arrival_time_preference: str | None = None,
    cabin_class: str | None = None,
    max_stops: int | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    preferred_airline: str | None = None,
    max_outbound_duration: float | None = None,
    max_inbound_duration: float | None = None,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """Internal flight-search implementation returning a full dict.

    The public ``search_flights`` @tool wraps this and splits the dict into a
    ``(content, artifact)`` tuple so the LLM never sees the heavy flight list
    (issue #1034). Direct internal callers (e.g. ``_search_single_date``) call
    this helper to get the full dict back.
    """
    from datetime import datetime

    # ── Multi-city (Circle) routing ────────────────────────────────────────
    if segments:
        logger.info(
            "search_flights: multi-city mode — %d segments, adults=%d",
            len(segments),
            adults,
        )
        return await _search_multicity(
            segments_input=segments,
            adults=adults,
            children=children,
            infants=infants,
            cabin_class=cabin_class,
        )

    # ── Single-trip / date-range ───────────────────────────────────────────
    # model_validator ensures origin/destination are set here
    if not origin or not destination:
        return {
            "status": "error",
            "error": "origin and destination are required for one-way/round-trip/date-range search.",
            "instruction": "Provide all required fields or use 'segments' for multi-city.",
        }

    # Log the search parameters for debugging
    logger.info(
        f"search_flights called: origin={origin}, destination={destination}, "
        f"departure={departure_date}, return={return_date}, "
        f"adults={adults}, children={children}, infants={infants}, "
        f"origin_is_city={origin_is_city}, destination_is_city={destination_is_city}, "
        f"departure_time={departure_time_preference}, arrival_time={arrival_time_preference}, "
        f"cabin_class={cabin_class}, max_stops={max_stops}, "
        f"price_min={price_min}, price_max={price_max}, "
        f"preferred_airline={preferred_airline}"
    )

    from app.domains.flight.enums import CabinClass, JourneyType
    from app.domains.flight.schemas import (
        AirlineInfo,
        AirportInfo,
        FlightSearchRequest,
        OriginDestinationSegment,
    )

    # Validate IATA codes
    if len(origin) != 3 or len(destination) != 3:
        return {
            "status": "error",
            "error": "Invalid airport codes. Both origin and destination must be 3-letter IATA codes.",
            "origin": origin,
            "destination": destination,
            "instruction": "Use resolve_airport tool first to get valid IATA codes.",
        }

    # Validate origin != destination
    if origin.upper() == destination.upper():
        return {
            "error": f"Origin and destination cannot be the same airport ({origin}). "
            "Please check: origin is where user is flying FROM, destination is where user is flying TO.",
            "origin": origin,
            "destination": destination,
            "instruction": "You have confused origin and destination. Review the conversation to find the correct destination airport.",
        }

    # Validate trip_type is explicitly provided — reject if the LLM guessed
    valid_trip_types = {"one-way", "round-trip"}
    if trip_type not in valid_trip_types:
        return {
            "status": "error",
            "error": f"Invalid trip_type: '{trip_type}'. Must be 'one-way' or 'round-trip'.",
            "instruction": "Ask the user: 'Is this a one-way or round-trip flight?'",
        }

    # Consistency check: round-trip requires return_date
    if trip_type == "round-trip" and not return_date:
        return {
            "status": "error",
            "error": "trip_type is 'round-trip' but no return_date provided.",
            "instruction": "Ask the user for their return date.",
        }

    # Validate that exactly one of departure_date / departure_dates is provided
    if not departure_date and not departure_dates:
        return {
            "status": "error",
            "error": "Either departure_date or departure_dates must be provided.",
            "instruction": "Use parse_dates tool first to get dates.",
        }
    if departure_date and departure_dates:
        return {
            "status": "error",
            "error": "Provide departure_date OR departure_dates, not both.",
            "instruction": "Use departure_date for single-date search, departure_dates for date-range search.",
        }

    # ── Date-range search (parallel multi-date) ─────────────────────
    if departure_dates:
        return await _search_date_range(
            origin=origin,
            destination=destination,
            departure_dates=departure_dates,
            departure_window_end=departure_window_end,
            adults=adults,
            children=children,
            infants=infants,
            origin_is_city=origin_is_city,
            destination_is_city=destination_is_city,
            departure_time_preference=departure_time_preference,
            arrival_time_preference=arrival_time_preference,
            cabin_class=cabin_class,
            max_stops=max_stops,
            price_min=price_min,
            price_max=price_max,
            preferred_airline=preferred_airline,
            max_outbound_duration=max_outbound_duration,
            max_inbound_duration=max_inbound_duration,
        )

    # ── Single-date search (existing path) ──────────────────────────
    # By this point departure_dates was falsy, so departure_date must be set
    if departure_date is None:
        return {
            "status": "error",
            "error": "departure_date is required for single-date search.",
            "instruction": "Use parse_dates tool first to get a date in YYYY-MM-DD format.",
        }
    # Parse departure date
    try:
        dep_date = datetime.strptime(departure_date, "%Y-%m-%d").date()
    except ValueError:
        return {
            "status": "error",
            "error": f"Invalid departure date format: {departure_date}. Use YYYY-MM-DD.",
            "instruction": "Use parse_dates tool first to get dates in YYYY-MM-DD format.",
        }

    # Parse return date if provided
    ret_date = None
    if return_date:
        try:
            ret_date = datetime.strptime(return_date, "%Y-%m-%d").date()
        except ValueError:
            return {
                "status": "error",
                "error": f"Invalid return date format: {return_date}. Use YYYY-MM-DD.",
                "instruction": "Use parse_dates tool first to get dates in YYYY-MM-DD format.",
            }

    # Build origin destination segments (renamed to avoid shadowing the 'segments' parameter)
    od_segments: list[OriginDestinationSegment] = [
        OriginDestinationSegment(
            departure_date=dep_date,
            return_date=None,
            origin_airport=AirportInfo(
                iata_code=origin.upper(),
                icao_code=None,
                airport_name=None,
                city_name=None,
                country_code=None,
            ),
            destination_airport=AirportInfo(
                iata_code=destination.upper(),
                icao_code=None,
                airport_name=None,
                city_name=None,
                country_code=None,
            ),
        )
    ]

    # For round trips, add return segment
    journey_type = JourneyType.ONE_WAY
    if ret_date:
        journey_type = JourneyType.RETURN
        od_segments.append(
            OriginDestinationSegment(
                departure_date=ret_date,
                return_date=None,
                origin_airport=AirportInfo(
                    iata_code=destination.upper(),
                    icao_code=None,
                    airport_name=None,
                    city_name=None,
                    country_code=None,
                ),
                destination_airport=AirportInfo(
                    iata_code=origin.upper(),
                    icao_code=None,
                    airport_name=None,
                    city_name=None,
                    country_code=None,
                ),
            )
        )

    # Build filters with time preferences (if provided)
    from app.domains.flight.schemas import FlightSearchFilters, LegFilter

    leg_filters = []

    # Map time preferences to time windows
    departure_window = _map_time_preference_to_window(departure_time_preference)
    arrival_window = _map_time_preference_to_window(arrival_time_preference)

    # Apply time preferences to outbound leg (always) and return leg (if round-trip)
    # Note: Backend only filters legs that have a LegFilter - legs without filters pass all flights
    if departure_window or arrival_window:
        # Outbound leg (leg_index=0) - always apply if time preferences specified
        leg_filters.append(
            LegFilter(
                leg_index=0,
                description="Outbound flight time preferences",
                city_wise_search=None,
                departure_window=departure_window,
                arrival_window=arrival_window,
            )
        )

        # Return leg (leg_index=1) - only for round trips
        # Apply SAME time preferences to return leg to maintain consistency
        # (e.g., "morning flight" → both outbound and return in morning)
        # Backend behavior: If we don't add leg_index=1 filter, return leg won't be filtered at all
        if ret_date:  # Only for round-trip flights
            leg_filters.append(
                LegFilter(
                    leg_index=1,
                    description="Return flight time preferences",
                    city_wise_search=None,
                    departure_window=departure_window,  # Same as outbound
                    arrival_window=arrival_window,  # Same as outbound
                )
            )

        logger.info(
            f"Applied time filters to {'both outbound and return' if ret_date else 'outbound only'}: "
            f"departure={departure_time_preference} ({departure_window}), "
            f"arrival={arrival_time_preference} ({arrival_window})"
        )

    # Build filters object
    filters = FlightSearchFilters(
        city_wise_search_origin=origin_is_city,
        city_wise_search_destination=destination_is_city,
        journey_filters=leg_filters if leg_filters else None,
    )

    # Map cabin_class string to CabinClass enum (API-level filter)
    CABIN_CLASS_MAP = {
        "economy": CabinClass.ECONOMY,
        "premium_economy": CabinClass.PREMIUM_ECONOMY,
        "business": CabinClass.BUSINESS,
        "first": CabinClass.FIRST,
    }
    if cabin_class and cabin_class.lower() not in CABIN_CLASS_MAP:
        logger.warning(
            f"Unrecognised cabin_class '{cabin_class}', falling back to Economy"
        )
    cabin_class_enum = (
        CABIN_CLASS_MAP.get(cabin_class.lower(), CabinClass.ECONOMY)
        if cabin_class
        else CabinClass.ECONOMY
    )

    # Map max_stops=0 to direct_flight API param (API-level filter)
    direct_flight_param = 1 if max_stops == 0 else None

    if cabin_class and cabin_class_enum != CabinClass.ECONOMY:
        logger.info(f"API-level filter: cabin_class={cabin_class_enum.value}")
    if direct_flight_param:
        logger.info("API-level filter: direct_flight=1 (non-stop only)")

    # Build search request
    request = FlightSearchRequest(
        # BaseFlightLogicRequest fields (optional - will use config defaults)
        user_id=None,
        user_password=None,
        access=None,
        ip_address=None,
        # FlightSearchRequest fields
        required_currency_code=None,
        journey_type=journey_type,
        origin_destination_info=od_segments,
        cabin_class=cabin_class_enum,
        adults=adults,
        children=children,
        infants=infants,
        # Unknown IATA codes are passed through intentionally — the FlightLogic API
        # will simply return no matches for that airline, which is acceptable behaviour.
        preferred_airline=AirlineInfo(
            iata_code=preferred_airline.upper(),
            icao_code=None,
            airline_name=None,
            logo_url=None,
        )
        if preferred_airline
        else None,
        direct_flight=direct_flight_param,
        # Pass filters with time windows and city-wise search flags
        filters=filters,
        revalidate_flights_count=0,
        # Legacy fields for backward compatibility (will be merged into filters by validator)
        city_wise_search_origin=origin_is_city,
        city_wise_search_destination=destination_is_city,
    )

    # Execute search using FlightService (handles filtering, platform fees, logging)
    try:
        # Import here to avoid circular dependencies
        from app.domains.flight.service import FlightService

        # Create service instance without user context (LangGraph tool doesn't need user)
        service = FlightService(current_user=None)
        response = await service.search_flights(request)

        # FlightService automatically handles:
        # - Platform fee application (5% markup)
        # - Filter application (time windows, city-wise search, etc.)
        # - Structured logging with FlightLogger
        # - Consistent error handling

        # Check for FlightLogic API errors in response (even if HTTP 200)
        if response.errors and len(response.errors) > 0:
            # Extract error information for LLM
            error = response.errors[0]  # Get first error
            error_type = "FLIGHT_API_ERROR"
            error_message = error.message if hasattr(error, "message") else str(error)
            error_code = error.code if hasattr(error, "code") else None

            # Detect unsupported airport errors and provide nearby alternatives.
            # Match on error_code first (stable), then keyword fallback (handles
            # providers that don't set a structured code).
            unsupported_keywords = [
                "not supported",
                "unsupported",
                "not available",
                "invalid airport",
                "airport not found",
            ]
            error_lower = error_message.lower()
            is_unsupported_airport = error_code == "INVALID_AIRPORT" or any(
                kw in error_lower for kw in unsupported_keywords
            )

            if is_unsupported_airport:
                from app.domains.airport.airport_resolver import AirportResolver

                resolver = AirportResolver()

                # Determine which airport(s) FlightLogic rejected.
                # Check if the error message explicitly mentions the IATA code;
                # if not, assume the destination (most commonly unsupported).
                error_upper = error_message.upper()
                problematic = [
                    code
                    for code in [origin.upper(), destination.upper()]
                    if code in error_upper
                ]
                if not problematic:
                    problematic = [destination.upper()]

                # Fetch FL-supported airports to filter nearby candidates.
                # Only suggest airports FlightLogic can actually search —
                # prevents back-and-forth when the DB returns nearby airports
                # that are also unsupported by FlightLogic.
                fl_supported = await _get_fl_supported_airports()

                suggestions: list[str] = []
                for code in problematic:
                    # Look up city name so we say "Buffalo" not "BUF" to the user.
                    await resolver.ensure_loaded()
                    airport_info: dict[str, Any] = next(
                        (
                            a
                            for a in resolver.airports_data.values()
                            if a.get("iata", "").upper() == code
                        ),
                        {},
                    )
                    city_name = airport_info.get("city") or code
                    display = f"{city_name} ({code})" if city_name != code else code

                    nearby = await resolver.find_nearby_airports(
                        code, radius_km=200, limit=10
                    )
                    # Filter to only FL-supported airports (skip if set is empty
                    # meaning FL airport list fetch failed — show all nearby).
                    if fl_supported:
                        nearby = [
                            a for a in nearby if a["iata"].upper() in fl_supported
                        ][:4]
                    else:
                        nearby = nearby[:4]

                    if nearby:
                        options = ", ".join(
                            f"{a['city']} ({a['iata']}) — {a['distance_km']} km away"
                            for a in nearby
                        )
                        suggestions.append(
                            f"{display} is not in our search system. "
                            f"Nearby alternatives: {options}"
                        )
                    else:
                        suggestions.append(
                            f"{display} is not in our search system and no nearby airports were found within 200 km."
                        )

                logger.info(
                    f"Unsupported airport detected: {problematic}. "
                    f"Nearby alternatives found: {bool(suggestions)}"
                )
                return {
                    "status": "unsupported_airport",
                    "error": error_message,
                    "unsupported_airports": problematic,
                    "instruction": (
                        "The flight search failed because one or more airports are not supported. "
                        "Present the alternatives below as a numbered list and ask the user which "
                        "they would like to use. Do NOT say the airport is 'temporarily unavailable' "
                        "— say it is not in our search system.\n"
                        + "\n".join(suggestions)
                    ),
                }

            # Generate empathetic error message using LLM for all other errors
            try:
                user_friendly_message = await generate_error_message(
                    error_type=error_type,
                    error_message=error_message,
                    operation="search",
                    error_code=error_code,
                    status_code=None,
                    additional_context={
                        "origin": origin,
                        "destination": destination,
                        "departure_date": departure_date,
                    },
                )
            except Exception as llm_error:
                logger.warning(
                    f"Failed to generate LLM error message, using fallback: {llm_error}"
                )
                # Fallback to generic message if LLM fails
                user_friendly_message = (
                    f"I encountered an error while searching for flights: {error_message}. "
                    "Would you like to try again or modify your search criteria?"
                )

            return {
                "status": "error",
                "error": error_message,  # Technical error for logging
                "error_type": error_type,
                "message": user_friendly_message,  # LLM-generated user-friendly message
                "instruction": "Inform the user about the error and suggest next steps.",
            }

        # Extract flight options - process all flights for accurate category calculations
        total_flights_received = (
            len(response.fare_itineraries) if response.fare_itineraries else 0
        )
        logger.info(
            "🔢 [funnel] flight_search %s→%s on %s: provider_returned=%d fare_itineraries",
            origin,
            destination,
            departure_date,
            total_flights_received,
        )

        # Extract flight options
        flights = []
        for itinerary in response.fare_itineraries:
            flight_info = _extract_flight_info(itinerary)
            if flight_info:
                flights.append(flight_info)
        logger.info(
            "🔢 [funnel] after _extract_flight_info: %d/%d kept",
            len(flights),
            total_flights_received,
        )

        # Enrich flights with airport names from our database
        flights = await _enrich_flights_with_airport_names(flights)

        # Apply post-filters (for fields API doesn't support: price range, max_stops > 0)
        total_before_filter = len(flights)
        flights = _apply_post_filters(
            flights,
            max_stops=max_stops,
            price_min=price_min,
            price_max=price_max,
            max_outbound_duration=max_outbound_duration,
            max_inbound_duration=max_inbound_duration,
        )
        logger.info(
            "🔢 [funnel] after _apply_post_filters: %d/%d kept "
            "(max_stops=%s, price_min=%s, price_max=%s)",
            len(flights),
            total_before_filter,
            max_stops,
            price_min,
            price_max,
        )

        # Validate flight results for data integrity
        before_validate = len(flights)
        flights = _validate_flight_results(flights)
        logger.info(
            "🔢 [funnel] after _validate_flight_results: %d/%d kept",
            len(flights),
            before_validate,
        )

        if not flights and total_before_filter > 0:
            return {
                "status": "no_results",
                "message": (
                    f"Found {total_before_filter} flights from {origin} to {destination}, "
                    "but none match your filters. Try relaxing some filters."
                ),
                "suggestion": "Try removing a filter or widening the price range.",
                "instruction": "Inform the user that flights exist but none match their filters, and suggest adjustments.",
            }

        if not flights:
            return {
                "status": "no_results",
                "message": f"No flights found from {origin} to {destination} on {departure_date}.",
                "instruction": (
                    "No flights found. Immediately call find_nearby_airports() for the "
                    "smaller or regional airport (whichever of origin/destination is less "
                    "likely to be a major hub). Present the nearby alternatives with "
                    "distances and offer to search those instead. Do NOT just tell the "
                    "user to 'try different dates or nearby airports' — actually search "
                    "the alternatives for them.\n"
                    "IMPORTANT: If the destination is a small/domestic airport in an island "
                    "nation (Maldives, Fiji, etc.), the main international gateway is almost "
                    "certainly the only option for international flights. Suggest it explicitly "
                    "(e.g. 'Ifuru is a small domestic airport — for international flights to "
                    "the Maldives, Male International Airport (MLE) is the main gateway. "
                    "Want me to search there instead?')."
                ),
            }

        # Only a real non-empty session_id should enable revalidation.
        raw_session_id = getattr(response, "session_id", None)
        flightlogic_session_id = (
            raw_session_id.strip()
            if isinstance(raw_session_id, str) and raw_session_id.strip()
            else None
        )
        if not flightlogic_session_id:
            logger.warning("FlightLogic search response missing session_id")

        # Fetch user preferences to decide how to populate the Best Value category.
        # Reads user_id from the graph configurable so the LLM never sees this parameter.
        user_prefs = None
        try:
            configurable = (config or {}).get("configurable", {}) if config else {}
            uid = configurable.get("user_id")
            if uid:
                from app.domains.user_preferences.repository import get_preferences

                prefs_response = await get_preferences(uid)
                user_prefs = prefs_response.flights if prefs_response else None
        except Exception as pref_err:
            logger.warning("Could not fetch user preferences for scoring: %s", pref_err)

        # Issue #1034: single best-value sort over the FULL result set.
        # No cheapest/fastest buckets, no truncation. User preferences (if set)
        # are passed in and influence the sort via PREFERENCE_WEIGHT — no
        # separate preference-sort path anymore. The frontend handles its own
        # sort/filter UI on the flat list.
        sorted_flights = sort_flights_by_best_value(
            flights,
            get_price=lambda f: f["price"],
            get_duration=lambda f: f["duration_minutes"],
            get_departure_hour=lambda f: hour_from_time_str(f.get("departure_time")),
            get_arrival_hour=lambda f: hour_from_time_str(f.get("arrival_time")),
            get_return_departure_hour=lambda f: hour_from_time_str(
                f.get("return_departure_time")
            ),
            get_return_arrival_hour=lambda f: hour_from_time_str(
                f.get("return_arrival_time")
            ),
            user_preferences=user_prefs,
        )

        def _extract_fare_source_code(flight_item: object) -> str | None:
            return flight_item.get("id") if isinstance(flight_item, dict) else None

        from app.core.config import settings

        if flightlogic_session_id and settings.FLIGHT_SEARCH_CONCURRENT_REVALIDATION:
            before_revalidate = len(sorted_flights)
            sorted_flights = await filter_flights_after_revalidation(
                session_id=flightlogic_session_id,
                flights=sorted_flights,
                adults=adults,
                children=children,
                infants=infants,
                revalidate_fn=service.revalidate_fare,
                get_fare_source_code=_extract_fare_source_code,
            )
            logger.info(
                "🔢 [funnel] after revalidation: %d/%d kept",
                len(sorted_flights),
                before_revalidate,
            )

            # If revalidation removed all flights, report no results so the LLM
            # informs the user instead of presenting empty flight cards.
            if not sorted_flights:
                return {
                    "status": "no_results",
                    "message": f"No flights available from {origin} to {destination} on {departure_date}.",
                    "instruction": (
                        "All flights failed revalidation. Call find_nearby_airports() "
                        "for the smaller airport and offer alternative routes. Do NOT "
                        "just tell the user to try different dates — search alternatives "
                        "for them."
                    ),
                }
        elif flightlogic_session_id:
            logger.debug(
                "🔢 [funnel] revalidation skipped (FLIGHT_SEARCH_CONCURRENT_REVALIDATION disabled)"
            )

        prices = [f["price"] for f in sorted_flights]

        # Extract city names from enriched flight data for frontend display
        origin_city = flights[0].get("origin_city", "") if flights else ""
        destination_city = flights[0].get("destination_city", "") if flights else ""

        search_params = {
            "origin": origin_city or origin,
            "destination": destination_city or destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "journey_type": "Return"
            if return_date
            else "OneWay",  # Frontend needs this!
            "adults": adults,
            "children": children,
            "infants": infants,
            "origin_is_city": origin_is_city,  # Multi-airport search flag
            "destination_is_city": destination_is_city,  # Multi-airport search flag
            "cabin_class": cabin_class_enum.value if cabin_class else "Economy",
            "direct_flight": 1 if max_stops == 0 else 0,
            "preferred_airline": preferred_airline.upper()
            if preferred_airline
            else None,
            "max_outbound_duration": max_outbound_duration,
            "max_inbound_duration": max_inbound_duration,
        }
        logger.info(f"🔍 TOOL returning search_params: {search_params}")
        logger.info(
            "🔢 [funnel] FINAL outgoing to frontend: %d flights (provider_returned=%d)",
            len(sorted_flights),
            total_flights_received,
        )

        return {
            "status": "success",
            "session_id": flightlogic_session_id,  # FlightLogic session_id for revalidation
            "origin_is_city": origin_is_city,  # Pass through for frontend redirect
            "destination_is_city": destination_is_city,  # Pass through for frontend redirect
            "search_params": search_params,
            "summary": {
                "total_found": len(sorted_flights),
                "direct_flights": sum(
                    1 for f in sorted_flights if f.get("stops", 0) == 0
                ),
                "price_range": {
                    "min": min(prices) if prices else 0,
                    "max": max(prices) if prices else 0,
                    "currency": sorted_flights[0].get("currency", "GBP")
                    if sorted_flights
                    else "GBP",
                },
            },
            # Issue #1034: full best-value-sorted list (no categories, no truncation).
            "flights": sorted_flights,
            "instruction": "Present these options to the user and ask which they'd like to book.",
        }

    except Exception as e:
        logger.exception(f"search_flights error: {e}")

        # Extract structured error information for LLM
        error_type, error_message, error_code, status_code = detect_error_type(e)

        # AI-CHAT-010: classify once and reuse for both the fallback user
        # message and the error_class field downstream consumers read.
        from app.ai.errors import classify_exception

        classified = classify_exception(e)

        # Generate empathetic error message using LLM; fall back to the
        # classifier's user message if the LLM call itself fails.
        try:
            user_friendly_message = await generate_error_message(
                error_type=error_type,
                error_message=error_message,
                operation="search",
                error_code=error_code,
                status_code=status_code,
                additional_context={
                    "origin": origin,
                    "destination": destination,
                    "departure_date": departure_date,
                },
            )
        except Exception as llm_error:
            logger.warning(
                f"Failed to generate LLM error message, using fallback: {llm_error}"
            )
            user_friendly_message = classified.user_message

        return {
            "status": "error",
            "error": error_message,
            "error_type": error_type,
            "error_class": classified.cls.value,
            "message": user_friendly_message,
            "instruction": "Inform the user about the error and suggest next steps.",
        }


@tool(
    "search_flights",
    args_schema=FlightSearchInput,
    response_format="content_and_artifact",
)
async def search_flights(
    adults: int,
    origin: str | None = None,
    destination: str | None = None,
    trip_type: str | None = None,
    departure_date: str | None = None,
    departure_dates: list[str] | None = None,
    departure_window_end: str | None = None,
    segments: list[dict[str, str]] | None = None,
    return_date: str | None = None,
    children: int = 0,
    infants: int = 0,
    origin_is_city: bool = True,
    destination_is_city: bool = True,
    departure_time_preference: str | None = None,
    arrival_time_preference: str | None = None,
    # Flight filters
    cabin_class: str | None = None,
    max_stops: int | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    preferred_airline: str | None = None,
    max_outbound_duration: float | None = None,
    max_inbound_duration: float | None = None,
    # Injected from graph config — not visible to the LLM
    config: Annotated[RunnableConfig | None, InjectedToolArg] = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Search for available flights with optional filters.

    PREREQUISITE: You MUST call resolve_airport for BOTH origin AND destination
    BEFORE calling this tool. Use ONLY the IATA codes returned by resolve_airport.
    NEVER use IATA codes from your own knowledge — they may be wrong.

    Per issue #1034: returns a ``(content, artifact)`` tuple. The LLM only sees
    the content (summary + instruction). The full best-value-sorted flight list
    lives on ``ToolMessage.artifact`` and is consumed by the graph extractor
    for the frontend payload — it is NEVER sent to the LLM.

    Filter args (all optional):
        cabin_class: 'economy', 'premium_economy', 'business', or 'first' (API-level)
        max_stops: 0=direct (API-level), >0 post-filtered on results
        price_min: Minimum price post-filter
        price_max: Maximum price post-filter
    """
    result = await _do_flight_search(
        adults=adults,
        origin=origin,
        destination=destination,
        trip_type=trip_type,
        departure_date=departure_date,
        departure_dates=departure_dates,
        departure_window_end=departure_window_end,
        segments=segments,
        return_date=return_date,
        children=children,
        infants=infants,
        origin_is_city=origin_is_city,
        destination_is_city=destination_is_city,
        departure_time_preference=departure_time_preference,
        arrival_time_preference=arrival_time_preference,
        cabin_class=cabin_class,
        max_stops=max_stops,
        price_min=price_min,
        price_max=price_max,
        preferred_airline=preferred_airline,
        max_outbound_duration=max_outbound_duration,
        max_inbound_duration=max_inbound_duration,
        config=config,
    )
    return _split_search_result(result)


def _extract_segment_info(segment: Any) -> dict[str, Any]:
    """Extract segment information for layover display.

    Args:
        segment: FlightSegment object

    Returns:
        Dict with segment details for frontend FlightDetailsModal
    """
    # Extract departure info
    departure_code = ""
    departure_city = ""
    departure_airport = ""
    if hasattr(segment, "departure_airport") and segment.departure_airport:
        departure_code = segment.departure_airport.iata_code or ""
        departure_city = getattr(segment.departure_airport, "city_name", "") or ""
        departure_airport = getattr(segment.departure_airport, "airport_name", "") or ""

    # Extract arrival info
    destination_code = ""
    destination_city = ""
    destination_airport = ""
    if hasattr(segment, "arrival_airport") and segment.arrival_airport:
        destination_code = segment.arrival_airport.iata_code or ""
        destination_city = getattr(segment.arrival_airport, "city_name", "") or ""
        destination_airport = getattr(segment.arrival_airport, "airport_name", "") or ""

    # Extract times and dates (field is departure_datetime with .value containing datetime)
    departure_time = ""
    departure_date = ""
    arrival_time = ""
    arrival_date = ""
    if hasattr(segment, "departure_datetime") and segment.departure_datetime:
        dt = segment.departure_datetime
        # Handle DateTime wrapper object with .value
        if hasattr(dt, "value"):
            dt = dt.value
        if hasattr(dt, "strftime"):
            departure_time = dt.strftime("%H:%M")
            departure_date = dt.strftime("%Y-%m-%d")
        elif isinstance(dt, str):
            departure_time = dt[11:16] if len(dt) > 16 else ""
            departure_date = dt[:10] if len(dt) >= 10 else ""

    if hasattr(segment, "arrival_datetime") and segment.arrival_datetime:
        dt = segment.arrival_datetime
        # Handle DateTime wrapper object with .value
        if hasattr(dt, "value"):
            dt = dt.value
        if hasattr(dt, "strftime"):
            arrival_time = dt.strftime("%H:%M")
            arrival_date = dt.strftime("%Y-%m-%d")
        elif isinstance(dt, str):
            arrival_time = dt[11:16] if len(dt) > 16 else ""
            arrival_date = dt[:10] if len(dt) >= 10 else ""

    # Extract segment duration (required by frontend for layover calculations)
    duration = "0h 0m"
    seg_duration_minutes = 0
    if hasattr(segment, "flight_duration") and segment.flight_duration:
        seg_duration_minutes = getattr(segment.flight_duration, "total_minutes", 0) or 0
        if seg_duration_minutes > 0:
            hours = seg_duration_minutes // 60
            minutes = seg_duration_minutes % 60
            duration = f"{hours}h {minutes}m"

    # Extract flight number info
    # Uses marketing_flight_number when available (preferred for display),
    # falls back to operating_flight_number for codeshare flights.
    # Named "flight_number_info" to avoid confusion when operating data is used as fallback.
    flight_number = ""
    flight_number_info = None
    if hasattr(segment, "marketing_flight_number") and segment.marketing_flight_number:
        fn = segment.marketing_flight_number
        if hasattr(fn, "formatted_number") and fn.formatted_number:
            flight_number = fn.formatted_number
            flight_number_info = {
                "formatted_number": fn.formatted_number,
                "number": getattr(fn, "flight_number", ""),
                "airline_prefix": getattr(fn, "carrier_code", ""),
            }
        else:
            carrier = getattr(fn, "carrier_code", "") or ""
            number = getattr(fn, "flight_number", "") or ""
            flight_number = f"{carrier}{number}"
            flight_number_info = {
                "formatted_number": flight_number,
                "number": number,
                "airline_prefix": carrier,
            }
    elif (
        hasattr(segment, "operating_flight_number") and segment.operating_flight_number
    ):
        fn = segment.operating_flight_number
        if hasattr(fn, "formatted_number") and fn.formatted_number:
            flight_number = fn.formatted_number
            flight_number_info = {
                "formatted_number": fn.formatted_number,
                "number": getattr(fn, "flight_number", ""),
                "airline_prefix": getattr(fn, "carrier_code", ""),
            }
        else:
            # Symmetric fallback: construct from carrier_code + flight_number
            carrier = getattr(fn, "carrier_code", "") or ""
            number = getattr(fn, "flight_number", "") or ""
            flight_number = f"{carrier}{number}"
            flight_number_info = {
                "formatted_number": flight_number,
                "number": number,
                "airline_prefix": carrier,
            }

    # Extract airline info per segment (marketing preferred, operating fallback).
    # logo_url is populated by _enrich_airline_logos before this is called.
    seg_airline_code = ""
    seg_airline_name = ""
    seg_logo_url: str | None = None
    if hasattr(segment, "marketing_airline") and segment.marketing_airline:
        seg_airline_code = getattr(segment.marketing_airline, "iata_code", "") or ""
        seg_airline_name = getattr(segment.marketing_airline, "airline_name", "") or ""
        raw_logo = getattr(segment.marketing_airline, "logo_url", None)
        seg_logo_url = raw_logo if isinstance(raw_logo, str) else None
    elif hasattr(segment, "operating_airline") and segment.operating_airline:
        seg_airline_code = getattr(segment.operating_airline, "iata_code", "") or ""
        seg_airline_name = getattr(segment.operating_airline, "airline_name", "") or ""
        raw_logo = getattr(segment.operating_airline, "logo_url", None)
        seg_logo_url = raw_logo if isinstance(raw_logo, str) else None

    return {
        # Origin/departure info (use "origin" to match frontend expectations)
        "origin_code": departure_code,
        "origin_city": departure_city,
        "origin_airport": departure_airport,
        # Destination/arrival info
        "destination_code": destination_code,
        "destination_city": destination_city,
        "destination_airport": destination_airport,
        "departure_time": departure_time,
        "departure_date": departure_date,
        "arrival_time": arrival_time,
        "arrival_date": arrival_date,
        "duration": duration,  # Required by frontend FlightResultMessage
        "duration_minutes": seg_duration_minutes,
        # Flight number info (see extraction logic above for details)
        "flight_number": flight_number,
        "flight_number_info": flight_number_info,
        # Airline info per segment — used by frontend segmentInfoToSegmentCamel
        # to populate marketingAirline (code, name, logo) for FlightCard display.
        "airline_code": seg_airline_code,
        "airline": seg_airline_name,
        "logo_url": seg_logo_url,
    }


def _extract_flight_info(itinerary: Any) -> dict[str, Any] | None:
    """Extract flight information from a FareItinerary.

    Schema reference:
    - itinerary.pricing.fare_totals.total_fare (MoneyAmount)
    - itinerary.pricing.fare_source_code (str) - unique identifier
    - itinerary.flight_legs[].flight_segments[] (FlightSegment)
    - itinerary.flight_legs[].total_stops (int)
    - segment.operating_airline (AirlineInfo)
    - segment.operating_flight_number (FlightNumber)
    - segment.departure_airport/arrival_airport (AirportInfo)
    - segment.departure_date_time/arrival_date_time (datetime)
    - segment.flight_duration.total_minutes (int)

    Returns a dict compatible with frontend FlightDetailsCard component.
    """
    try:
        # Get pricing info from pricing.fare_totals
        # FlightService already applied platform fee to total_fare
        price = 0.0
        original_price = 0.0
        currency = "USD"
        fare_source_code = ""
        platform_fee_percentage = float(FLIGHTS_DISCOUNT_PERCENTAGE)

        if itinerary.pricing:
            fare_source_code = getattr(itinerary.pricing, "fare_source_code", "") or ""
            if itinerary.pricing.fare_totals:
                fare_totals = itinerary.pricing.fare_totals
                total_fare = fare_totals.total_fare

                if total_fare:
                    # FlightService already applied platform fee to total_fare
                    price = float(total_fare.amount or 0)
                    currency = total_fare.currency or "USD"

                    # Get original price from fare_totals (set by FlightService)
                    if (
                        hasattr(fare_totals, "original_total_fare")
                        and fare_totals.original_total_fare
                    ):
                        original_price = float(
                            fare_totals.original_total_fare.amount or 0
                        )
                    else:
                        original_price = price  # Fallback if not set

                    # Get platform fee percentage from fare_totals (set by FlightService)
                    if (
                        hasattr(fare_totals, "platform_fee_percentage")
                        and fare_totals.platform_fee_percentage
                    ):
                        platform_fee_percentage = float(
                            fare_totals.platform_fee_percentage
                        )

        # Get first leg (outbound) for flight details
        # Note: For round-trips, flight_legs[0] is outbound, flight_legs[1] is return
        # We display the OUTBOUND journey's origin/destination, not the full round-trip
        if not itinerary.flight_legs:
            return None

        first_leg = itinerary.flight_legs[0]  # Outbound leg

        if not first_leg.flight_segments:
            return None

        first_segment = first_leg.flight_segments[0]
        # Get last segment of OUTBOUND leg for arrival info (not return leg!)
        last_segment = first_leg.flight_segments[-1]

        # Calculate total duration including layover times
        # Total time = Flight Duration + Layover Time (for "fastest" category accuracy)
        def _extract_datetime(dt_obj: Any) -> datetime | None:
            """Extract datetime from various formats (DateTime wrapper, datetime object, or string)."""
            if not dt_obj:
                return None
            # Handle DateTime wrapper object with .value
            if hasattr(dt_obj, "value"):
                dt_obj = dt_obj.value
            # If it's already a datetime-like object
            if hasattr(dt_obj, "timestamp"):
                return dt_obj
            # If it's a string, try to parse it
            if isinstance(dt_obj, str):
                try:
                    # Try ISO format first
                    return datetime.fromisoformat(dt_obj.replace("Z", "+00:00"))
                except Exception:
                    # Try common datetime formats
                    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                        try:
                            return datetime.strptime(dt_obj, fmt)
                        except ValueError:
                            continue
                    return None
            return None

        duration_minutes = 0
        outbound_duration_minutes: float = 0
        inbound_duration_minutes: float | None = None
        for leg_idx, leg in enumerate(itinerary.flight_legs):
            if not leg.flight_segments:
                continue

            # Calculate flight duration (sum of all segment flight times)
            leg_flight_minutes = 0
            for seg in leg.flight_segments:
                if seg.flight_duration and seg.flight_duration.total_minutes:
                    leg_flight_minutes += seg.flight_duration.total_minutes

            # Calculate total layover time between segments in this leg
            total_layover_minutes = 0.0
            segments = leg.flight_segments
            for i in range(len(segments) - 1):
                # Get arrival time of current segment
                current_arr = None
                if hasattr(segments[i], "arrival_datetime"):
                    current_arr = _extract_datetime(segments[i].arrival_datetime)

                # Get departure time of next segment
                next_dep = None
                if hasattr(segments[i + 1], "departure_datetime"):
                    next_dep = _extract_datetime(segments[i + 1].departure_datetime)

                # Calculate layover time if both datetimes are available
                if current_arr and next_dep:
                    try:
                        # Calculate difference in minutes
                        layover_mins = int(
                            (next_dep.timestamp() - current_arr.timestamp()) / 60
                        )
                        if layover_mins > 0:  # Only add positive layover times
                            total_layover_minutes += layover_mins
                    except (AttributeError, TypeError, ValueError) as e:
                        # If datetime calculation fails, skip this layover
                        logger.debug(f"Could not calculate layover time: {e}")
                        pass

            # Total time for this leg = Flight Duration + Layover Time
            leg_total_minutes = int(leg_flight_minutes + total_layover_minutes)
            duration_minutes += leg_total_minutes

            # Store per-leg durations for post-filtering.
            # Only leg 0 (outbound) and leg 1 (inbound) are tracked.
            # This covers OneWay and Return trips. Circle/multi-city trips
            # with 3+ legs are not supported in chat — legs 2+ contribute
            # to total duration_minutes but not to per-leg filtering.
            if leg_idx == 0:
                outbound_duration_minutes = leg_total_minutes
            elif leg_idx == 1:
                inbound_duration_minutes = leg_total_minutes

        # Count stops from total_stops field
        stops = sum(leg.total_stops or 0 for leg in itinerary.flight_legs)

        # Extract airline info (prefer marketing_airline, fallback to operating)
        airline_name = "Unknown"
        airline_code = ""
        if (
            hasattr(first_segment, "marketing_airline")
            and first_segment.marketing_airline
        ):
            airline_name = first_segment.marketing_airline.airline_name or "Unknown"
            airline_code = first_segment.marketing_airline.iata_code or ""
        elif first_segment.operating_airline:
            airline_name = first_segment.operating_airline.airline_name or "Unknown"
            airline_code = first_segment.operating_airline.iata_code or ""

        # Extract flight number
        flight_number = ""
        if (
            hasattr(first_segment, "marketing_flight_number")
            and first_segment.marketing_flight_number
        ):
            fn = first_segment.marketing_flight_number
            if hasattr(fn, "formatted_number") and fn.formatted_number:
                flight_number = fn.formatted_number
            else:
                carrier = getattr(fn, "carrier_code", "") or ""
                number = getattr(fn, "flight_number", "") or ""
                flight_number = f"{carrier}{number}"
        elif first_segment.operating_flight_number:
            flight_number = first_segment.operating_flight_number.formatted_number or ""

        # Extract origin info
        origin_code = ""
        origin_city = ""
        origin_airport = ""
        if first_segment.departure_airport:
            origin_code = first_segment.departure_airport.iata_code or ""
            origin_city = (
                getattr(first_segment.departure_airport, "city_name", "") or ""
            )
            origin_airport = (
                getattr(first_segment.departure_airport, "airport_name", "") or ""
            )

        # Extract destination info (from last segment)
        destination_code = ""
        destination_city = ""
        destination_airport = ""
        if last_segment.arrival_airport:
            destination_code = last_segment.arrival_airport.iata_code or ""
            destination_city = (
                getattr(last_segment.arrival_airport, "city_name", "") or ""
            )
            destination_airport = (
                getattr(last_segment.arrival_airport, "airport_name", "") or ""
            )

        # Extract times (field is departure_datetime with .value containing datetime)
        departure_time = ""
        departure_date = ""
        if (
            hasattr(first_segment, "departure_datetime")
            and first_segment.departure_datetime
        ):
            dt = first_segment.departure_datetime
            # Handle DateTime wrapper object with .value
            if hasattr(dt, "value"):
                dt = dt.value
            if hasattr(dt, "strftime"):
                departure_time = dt.strftime("%H:%M")
                departure_date = dt.strftime("%Y-%m-%d")
            elif isinstance(dt, str):
                # Parse string datetime
                departure_time = dt[11:16] if len(dt) > 16 else ""
                departure_date = dt[:10] if len(dt) >= 10 else ""

        arrival_time = ""
        arrival_date = ""
        if hasattr(last_segment, "arrival_datetime") and last_segment.arrival_datetime:
            dt = last_segment.arrival_datetime
            # Handle DateTime wrapper object with .value
            if hasattr(dt, "value"):
                dt = dt.value
            if hasattr(dt, "strftime"):
                arrival_time = dt.strftime("%H:%M")
                arrival_date = dt.strftime("%Y-%m-%d")
            elif isinstance(dt, str):
                arrival_time = dt[11:16] if len(dt) > 16 else ""
                arrival_date = dt[:10] if len(dt) >= 10 else ""

        # Return leg times for penalty scoring (23:00–07:00 penalties)
        return_departure_time = ""
        return_arrival_time = ""
        if len(itinerary.flight_legs) > 1:
            return_leg = itinerary.flight_legs[1]
            if return_leg.flight_segments:
                ret_first = return_leg.flight_segments[0]
                ret_last = return_leg.flight_segments[-1]
                if (
                    hasattr(ret_first, "departure_datetime")
                    and ret_first.departure_datetime
                ):
                    dt = ret_first.departure_datetime
                    if hasattr(dt, "value"):
                        dt = dt.value
                    if hasattr(dt, "strftime"):
                        return_departure_time = dt.strftime("%H:%M")
                    elif isinstance(dt, str):
                        return_departure_time = dt[11:16] if len(dt) > 16 else ""
                if hasattr(ret_last, "arrival_datetime") and ret_last.arrival_datetime:
                    dt = ret_last.arrival_datetime
                    if hasattr(dt, "value"):
                        dt = dt.value
                    if hasattr(dt, "strftime"):
                        return_arrival_time = dt.strftime("%H:%M")
                    elif isinstance(dt, str):
                        return_arrival_time = dt[11:16] if len(dt) > 16 else ""

        # Extract all segments for layover display
        segments = []
        for leg_idx, leg in enumerate(itinerary.flight_legs):
            if leg.flight_segments:
                for seg_idx, seg in enumerate(leg.flight_segments):
                    segment_info = _extract_segment_info(seg)
                    segment_info["leg_index"] = leg_idx
                    logger.debug(
                        f"Leg {leg_idx}, Segment {seg_idx}: "
                        f"{segment_info.get('origin_code')} → {segment_info.get('destination_code')} "
                        f"at {segment_info.get('departure_time')}"
                    )
                    segments.append(segment_info)

        # Generate unique ID from fare_source_code or sequence_number
        flight_id = fare_source_code or str(itinerary.sequence_number or "")

        logger.info(
            f"✈️ Flight {flight_id}: {len(itinerary.flight_legs)} legs, "
            f"{len(segments)} total segments, is_round_trip={len(itinerary.flight_legs) > 1}"
        )

        return {
            # Frontend-required fields
            "id": flight_id,
            "departure_time": departure_time,
            "departure_date": departure_date,
            "arrival_time": arrival_time,
            "arrival_date": arrival_date,
            # Return leg times for penalty scoring (empty if one-way)
            "return_departure_time": return_departure_time,
            "return_arrival_time": return_arrival_time,
            "origin_code": origin_code,
            "origin_city": origin_city,
            "origin_airport": origin_airport,
            "destination_code": destination_code,
            "destination_city": destination_city,
            "destination_airport": destination_airport,
            "duration": f"{duration_minutes // 60}h {duration_minutes % 60}m",
            "duration_minutes": duration_minutes,
            "outbound_duration_minutes": outbound_duration_minutes,
            "inbound_duration_minutes": inbound_duration_minutes,
            "stops": stops,
            "price": price,  # Total price including platform fee (for display in tabs)
            "currency": currency,
            # Price breakdown fields (for modal display)
            "original_total_fare": original_price,  # Original fare without platform fee
            "platform_fee_percentage": platform_fee_percentage,  # Platform fee percentage
            # Segments for layover display in modal
            "segments": segments,
            # Additional fields
            "airline": airline_name,
            "airline_code": airline_code,
            "flight_number": flight_number,
            "sequence_number": itinerary.sequence_number,
            # Round trip indicator for frontend
            "is_round_trip": len(itinerary.flight_legs) > 1,
        }
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(f"Failed to extract flight info: {e}")
        return None


__all__ = ["FlightSearchInput", "search_flights"]
