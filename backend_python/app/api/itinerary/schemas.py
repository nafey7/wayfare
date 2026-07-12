"""Pydantic schemas for Itinerary Capabilities API.

These schemas define the request/response contracts for the
n8n Itinerary Agent integration endpoints.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Enums
# =============================================================================


class LocationType(StrEnum):
    """Type of location to resolve."""

    AIRPORT = "airport"
    CITY = "city"


class LocationStatus(StrEnum):
    """Status of location resolution."""

    RESOLVED = "resolved"
    NEEDS_USER_CHOICE = "needs_user_choice"
    NEEDS_DISAMBIGUATION = "needs_disambiguation"
    NO_OWN_AIRPORT = "no_own_airport"
    NOT_FOUND = "not_found"


class DisambiguationType(StrEnum):
    """Type of disambiguation needed."""

    MULTI_CITY = "MULTI_CITY"
    MULTI_AIRPORT = "MULTI_AIRPORT"
    CODE_VS_CITY = "CODE_VS_CITY"


# =============================================================================
# Resolve Location
# =============================================================================


class ResolveLocationContext(BaseModel):
    """Optional context for location resolution."""

    country_hint: str | None = Field(
        None, description="Country hint to narrow down results"
    )
    type: LocationType = Field(
        LocationType.AIRPORT,
        description="Type of location to resolve (airport or city)",
    )


class ResolveLocationRequest(BaseModel):
    """Request to resolve a location (city/airport)."""

    query: str = Field(
        ...,
        description="City name, airport code, or airport name to resolve",
        min_length=1,
        max_length=100,
    )
    context: ResolveLocationContext | None = Field(
        None, description="Optional context for resolution"
    )


class AirportInfo(BaseModel):
    """Airport information."""

    iata: str = Field(..., description="IATA code (3 letters)")
    name: str = Field(..., description="Airport name")
    city: str | None = Field(None, description="City name")
    country: str | None = Field(None, description="Country name")
    lat: float | None = Field(None, description="Latitude")
    lng: float | None = Field(None, description="Longitude")


class LocationOption(BaseModel):
    """Option for disambiguation."""

    display: str = Field(..., description="Display name for user selection")
    airports: list[AirportInfo] = Field(
        default_factory=list, description="Airports in this option"
    )


class NearbyAirport(BaseModel):
    """Nearby airport with distance."""

    iata: str = Field(..., description="IATA code")
    name: str = Field(..., description="Airport name")
    distance_km: int | None = Field(None, description="Distance in km (optional)")


class ResolveLocationResponse(BaseModel):
    """Response from location resolution."""

    status: LocationStatus = Field(..., description="Resolution status")
    location: AirportInfo | None = Field(
        default=None, description="Resolved location (if status=resolved)"
    )
    all_options: list[AirportInfo] | None = Field(
        default=None, description="All airports in city (if multiple)"
    )
    disambiguation_type: DisambiguationType | None = Field(
        default=None, description="Type of disambiguation (if needs_disambiguation)"
    )
    options: list[LocationOption] | None = Field(
        default=None, description="Options for user selection (if needs_disambiguation)"
    )
    suggested_prompt: str | None = Field(
        default=None, description="Suggested prompt to show user"
    )
    original_city: str | None = Field(
        default=None, description="Original city name (if no_own_airport)"
    )
    nearest_airports: list[NearbyAirport] | None = Field(
        default=None, description="Nearest airports (if no_own_airport)"
    )
    error: str | None = Field(default=None, description="Error message (if not_found)")


# =============================================================================
# Parse Dates
# =============================================================================


class ParseDatesRequest(BaseModel):
    """Request to parse natural language dates."""

    expression: str = Field(
        ...,
        description="Date expression to parse (e.g., 'next Christmas for 2 weeks')",
        min_length=1,
        max_length=200,
    )
    reference_date: str | None = Field(
        None, description="Reference date (YYYY-MM-DD), defaults to today"
    )


class ParseDatesResponse(BaseModel):
    """Response from date parsing."""

    status: str = Field(..., description="'success' or 'error'")
    departure_date: str | None = Field(
        default=None, description="Departure date (YYYY-MM-DD)"
    )
    return_date: str | None = Field(
        default=None, description="Return date (YYYY-MM-DD)"
    )
    trip_days: int | None = Field(default=None, description="Trip duration in days")
    journey_type: str | None = Field(default=None, description="'OneWay' or 'Return'")
    parsed_from: str | None = Field(
        default=None, description="Original expression that was parsed"
    )
    error: str | None = Field(
        default=None, description="Error message (if status=error)"
    )
    suggestion: str | None = Field(
        default=None, description="Suggestion for fixing error"
    )


# =============================================================================
# Search Flights
# =============================================================================


class SearchFlightsRequest(BaseModel):
    """Request to search for flights."""

    origin_iata: str = Field(
        ...,
        description="Origin airport IATA code",
        min_length=3,
        max_length=3,
    )
    destination_iata: str = Field(
        ...,
        description="Destination airport IATA code",
        min_length=3,
        max_length=3,
    )
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: str | None = Field(
        None, description="Return date (YYYY-MM-DD), null for one-way"
    )
    adults: int = Field(1, ge=1, le=9, description="Number of adults")
    children: int = Field(0, ge=0, le=9, description="Number of children")
    infants: int = Field(0, ge=0, le=9, description="Number of infants")
    cabin_class: str = Field("Economy", description="Cabin class")
    direct_only: bool = Field(False, description="Only search direct flights")
    session_id: str | None = Field(None, description="Session ID for tracking")


class FlightInfo(BaseModel):
    """Flight information for display."""

    id: str = Field(..., description="Unique flight identifier")
    departure_time: str = Field(..., description="Departure time (HH:MM)")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    arrival_time: str = Field(..., description="Arrival time (HH:MM)")
    arrival_date: str = Field(..., description="Arrival date (YYYY-MM-DD)")
    origin_code: str = Field(..., description="Origin IATA code")
    origin_city: str | None = Field(None, description="Origin city")
    destination_code: str = Field(..., description="Destination IATA code")
    destination_city: str | None = Field(None, description="Destination city")
    duration: str = Field(..., description="Duration (e.g., '2h 30m')")
    duration_minutes: int = Field(..., description="Duration in minutes")
    stops: int = Field(0, description="Number of stops")
    price: float = Field(..., description="Price")
    currency: str = Field("EUR", description="Currency code")
    airline: str = Field(..., description="Airline name")
    airline_code: str | None = Field(None, description="Airline IATA code")
    flight_number: str | None = Field(None, description="Flight number")
    segments: list[dict[str, Any]] | None = Field(
        None, description="Segment details for layovers"
    )


class CuratedFlight(BaseModel):
    """Curated flight with label."""

    label: str = Field(..., description="Label (e.g., 'Lowest Price')")
    flight: FlightInfo = Field(..., description="Flight details")


class FlightSearchSummary(BaseModel):
    """Summary of flight search results."""

    total_found: int = Field(..., description="Total flights found")
    direct_flights: int = Field(0, description="Number of direct flights")
    price_range: dict[str, Any] = Field(
        ..., description="Price range (min, max, currency)"
    )


class SearchFlightsResponse(BaseModel):
    """Response from flight search."""

    status: str = Field(..., description="'success', 'no_results', or 'error'")
    search_id: str | None = Field(default=None, description="Search ID for reference")
    summary: FlightSearchSummary | None = Field(
        default=None, description="Search summary (if success)"
    )
    curated: dict[str, CuratedFlight] | None = Field(
        default=None, description="Curated flights by category"
    )
    all_flights: list[FlightInfo] | None = Field(
        default=None, description="All flight results (optional)"
    )
    error: str | None = Field(default=None, description="Error message (if error)")
    suggestion: str | None = Field(
        default=None, description="Suggestion for next steps"
    )


# =============================================================================
# Search Hotels (Endpoint only, no n8n integration yet)
# =============================================================================


class SearchHotelsRequest(BaseModel):
    """Request to search for hotels."""

    city: str = Field(..., description="City name")
    country: str | None = Field(None, description="Country name")
    check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)")
    rooms: int = Field(1, ge=1, le=5, description="Number of rooms")
    adults: int = Field(2, ge=1, le=9, description="Number of adults")
    children: int = Field(0, ge=0, le=9, description="Number of children")
    session_id: str | None = Field(None, description="Session ID for tracking")


class HotelInfo(BaseModel):
    """Hotel information for display."""

    id: str = Field(..., description="Unique hotel identifier")
    name: str = Field(..., description="Hotel name")
    address: str | None = Field(None, description="Hotel address")
    city: str = Field(..., description="City")
    country: str | None = Field(None, description="Country")
    star_rating: int | None = Field(None, description="Star rating (1-5)")
    user_rating: float | None = Field(None, description="User rating (0-10)")
    price: float = Field(..., description="Price per night")
    total_price: float | None = Field(None, description="Total price")
    currency: str = Field("EUR", description="Currency code")
    amenities: list[str] | None = Field(None, description="Available amenities")
    image_url: str | None = Field(None, description="Hotel image URL")


class CuratedHotel(BaseModel):
    """Curated hotel with label."""

    label: str = Field(..., description="Label (e.g., 'Best Value')")
    hotel: HotelInfo = Field(..., description="Hotel details")


class HotelSearchSummary(BaseModel):
    """Summary of hotel search results."""

    total_found: int = Field(..., description="Total hotels found")
    price_range: dict[str, Any] = Field(
        ..., description="Price range (min, max, currency)"
    )


class SearchHotelsResponse(BaseModel):
    """Response from hotel search."""

    status: str = Field(..., description="'success', 'no_results', or 'error'")
    search_id: str | None = Field(default=None, description="Search ID for reference")
    summary: HotelSearchSummary | None = Field(
        default=None, description="Search summary (if success)"
    )
    curated: dict[str, CuratedHotel] | None = Field(
        default=None, description="Curated hotels by category"
    )
    all_hotels: list[HotelInfo] | None = Field(
        default=None, description="All hotel results (optional)"
    )
    error: str | None = Field(default=None, description="Error message (if error)")
    suggestion: str | None = Field(
        default=None, description="Suggestion for next steps"
    )


__all__ = [
    "AirportInfo",
    "CuratedFlight",
    "CuratedHotel",
    "DisambiguationType",
    "FlightInfo",
    "FlightSearchSummary",
    "HotelInfo",
    "HotelSearchSummary",
    "LocationOption",
    "LocationStatus",
    "LocationType",
    "NearbyAirport",
    "ParseDatesRequest",
    "ParseDatesResponse",
    "ResolveLocationContext",
    "ResolveLocationRequest",
    "ResolveLocationResponse",
    "SearchFlightsRequest",
    "SearchFlightsResponse",
    "SearchHotelsRequest",
    "SearchHotelsResponse",
]
