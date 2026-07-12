"""FlightLogic Hotel API v6 Data Transfer Objects (DTOs).

These models match the FlightLogic Hotel API v6 structure exactly.
They should only be used within the FlightLogic integration.
Convert to domain models before returning to the application.

Note: mixedCase field names are required to match FlightLogic API format.
"""

# ruff: noqa: N815

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ============================================================
# SEARCH REQUEST DTOs
# ============================================================


class OccupancyDTO(BaseModel):
    """Room occupancy details for hotel search.

    Matches FlightLogic API format exactly.
    """

    room_no: int = Field(..., ge=1, description="Room number (1-indexed)")
    adult: int = Field(..., ge=1, description="Number of adults")
    child: int = Field(0, ge=0, description="Number of children")
    child_age: list[int] = Field(
        default_factory=lambda: [0],
        description="Ages of children (use [0] if no children)",
    )


class HotelSearchRequestDTO(BaseModel):
    """FlightLogic Hotel API v6 search request - matches documentation exactly.

    Supports three search methods:
    1. City-based: city_name + country_name
    2. Geolocation: latitude + longitude (+ optional radius)
    3. Hotel codes: hotel_codes list

    At least one search method must be provided.
    """

    # Authentication (required)
    user_id: str
    user_password: str
    access: Literal["Test", "Production"]
    ip_address: str

    # Dates (required)
    checkin: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    checkout: str = Field(..., description="Check-out date (YYYY-MM-DD)")

    # Search criteria (at least one required)
    city_name: str | None = Field(None, description="City name for search")
    country_name: str | None = Field(None, description="Country name for search")
    latitude: float | None = Field(None, description="Latitude for geolocation search")
    longitude: float | None = Field(
        None, description="Longitude for geolocation search"
    )
    hotel_codes: list[str] | None = Field(
        None, description="List of hotel codes (max 1000)"
    )

    # Optional search parameters
    radius: int | None = Field(
        None, description="Search radius in KM (OPTIONAL, use with lat/lng)"
    )
    maxResult: int | None = Field(
        None, description="Max results (≥20 if provided, OPTIONAL)"
    )
    resultsPerPage: int | None = Field(
        None, description="Results per page for pagination"
    )

    # Occupancy (required)
    occupancy: list[OccupancyDTO] = Field(..., description="Room occupancy details")

    # Currency and preferences
    requiredCurrency: str = Field("USD", description="ISO 4217 currency code")
    requiredLanguage: str | None = Field(None, description="Language code")
    nationality: str | None = Field(None, description="ISO 3166-1 alpha-2 nationality")


# ============================================================
# SEARCH RESPONSE DTOs
# ============================================================


class PerNightPriceDTO(BaseModel):
    """Price breakdown for a single night.

    Matches FlightLogic Hotel API response structure (camelCase).
    Following the flight pattern: DTO field names match API format exactly.
    """

    nightIndex: int = Field(..., ge=1, description="Night number (1-indexed)")
    currency: str = Field(..., description="ISO 4217 currency code")
    price: str = Field(..., description="Price for this night (string with decimals)")


class HotelItineraryDTO(BaseModel):
    """Single hotel itinerary from search results.

    Matches FlightLogic Hotel API v6 response structure exactly.
    All fields use the exact casing from the API.
    """

    # Identification (required)
    hotelId: str = Field(..., description="Hotel ID")
    twxHotelId: str | int = Field(
        ..., description="TravelNext internal hotel ID (API may return int or str)"
    )
    productId: str = Field(..., description="Product/supplier code")
    tokenId: str = Field(
        ..., description="CRITICAL: Required for get_room_rates API call"
    )

    # Basic info (required)
    hotelName: str = Field(..., description="Hotel name")
    city: str | None = Field(
        None, description="City name (may be null for some hotels)"
    )
    locality: str | None = Field(
        None, description="Neighborhood/area (may be empty or null)"
    )
    address: str | None = Field(
        None, description="Street address (may be null for some hotels)"
    )
    country: str | None = Field(None, description="Country name (may be empty or null)")
    countryCode: str | None = Field(
        None, description="ISO country code (may be empty or null)"
    )
    postalCode: str | None = Field(None, description="Postal/ZIP code (may be null)")

    # Location (may be null for some hotels)
    latitude: str | None = Field(
        None, description="Latitude (20 decimal places precision, may be null)"
    )
    longitude: str | None = Field(
        None, description="Longitude (20 decimal places precision, may be null)"
    )
    distanceValue: float = Field(..., description="Distance from search center")
    distanceUnit: str = Field(..., description="Distance unit (KM or MI)")

    # Pricing (required)
    total: str = Field(
        ..., description="Total price for entire stay (string with decimals)"
    )
    perNightArray: list[PerNightPriceDTO] = Field(
        ..., description="Per-night price breakdown"
    )
    currency: str = Field(..., description="ISO 4217 currency code")
    fareType: str = Field(..., description="Refundable | Non-Refundable")

    # Hotel details
    hotelRating: float | str | int | None = Field(
        None, description="Star rating (API may return as int, float, string, or null)"
    )
    propertyType: str = Field("", description="Property type (hotel, resort, etc.)")
    facilities: list[str] = Field(default_factory=list, description="List of amenities")
    thumbNailUrl: str = Field(..., description="Thumbnail image URL")

    # Contact
    phone: str | None = Field(
        None, description="Comma-separated phone numbers (may be null)"
    )
    email: str | None = Field(None, description="Contact email (may be null or empty)")

    # Reviews
    tripAdvisorRating: float | str | int = Field(
        0, description="TripAdvisor rating (API may return float as string)"
    )
    tripAdvisorReview: int = Field(0, ge=0, description="Number of TripAdvisor reviews")

    # Special offers
    special: str = Field("", description="Special offers/notes (may be empty)")


class StatusDTO(BaseModel):
    """Search response status information.

    Matches FlightLogic API v6 status structure.
    """

    sessionId: str = Field(..., description="FlightLogic session ID (20-minute expiry)")
    moreResults: bool = Field(False, description="Whether more results are available")
    nextToken: str = Field("", description="Token for fetching next page")
    totalResults: int = Field(..., description="Total number of hotels found")


class HotelSearchResponseDTO(BaseModel):
    """FlightLogic Hotel API v6 search response.

    Top-level response structure containing status and hotel itineraries.
    """

    status: StatusDTO = Field(..., description="Response status and pagination info")
    itineraries: list[HotelItineraryDTO] = Field(
        default_factory=list, description="List of hotel search results"
    )


# ============================================================
# ROOM RATES REQUEST/RESPONSE DTOs (Phase 2)
# ============================================================


class HotelRoomRatesRequestDTO(BaseModel):
    """FlightLogic Hotel API v6 get_room_rates request.

    Gets detailed room options for a specific hotel from search results.

    IMPORTANT: Uses camelCase field names (NOT snake_case).
    IMPORTANT: Does NOT require authentication fields (only hotel_search does).
    """

    # Session & hotel identification (required) - camelCase!
    sessionId: str = Field(..., description="Session ID from hotel_search response")
    tokenId: str = Field(..., description="Hotel tokenId from search results")
    productId: str = Field(..., description="Product ID from search results")
    hotelId: str = Field(..., description="Hotel ID from search results")


class CancellationPolicyDTO(BaseModel):
    """Cancellation policy details for a room option."""

    cancelBy: str = Field(..., description="Cancellation deadline (ISO datetime)")
    charge: str = Field(..., description="Cancellation charge amount")
    currency: str = Field(..., description="Currency code")
    chargeType: str = Field(..., description="Percentage | Fixed")


class RoomOptionDTO(BaseModel):
    """Individual room option from FlightLogic get_room_rates API.

    Matches actual FlightLogic Hotel API v6 perBookingRates structure.
    """

    # Product identification
    productId: str = Field(..., description="Product/supplier code")
    roomType: str = Field(..., description="Room category/type")
    description: str = Field("", description="Room description")
    roomCode: str = Field(..., description="Room code")
    fareType: str = Field(..., description="Refundable | Non-Refundable")
    rateBasisId: str = Field(..., description="CRITICAL: Required for booking (base64)")

    # Pricing
    currency: str = Field(..., description="ISO 4217 currency code")
    netPrice: str | float = Field(..., description="Total net price (string or float)")
    taxes: list[list[dict[str, Any]]] = Field(
        default_factory=list, description="Tax breakdown"
    )

    # Meal plan
    boardType: str = Field("", description="Meal plan (ROOM ONLY, BB, HB, etc.)")

    # Availability and occupancy
    maxOccupancyPerRoom: str = Field("", description="Max occupancy (string format)")
    inventoryType: str = Field(..., description="prepaid | postpaid")

    # Policies (string, not list!)
    cancellationPolicy: str = Field("", description="Cancellation policy text")

    # Additional info
    roomImages: list[str] = Field(default_factory=list, description="Room image URLs")
    facilities: list[str] = Field(default_factory=list, description="Room amenities")
    extrabeds: str = Field("0", description="Extra beds available (string format)")


class RoomRatesDTO(BaseModel):
    """Nested roomRates structure from FlightLogic API."""

    perBookingRates: list[RoomOptionDTO] = Field(
        default_factory=list, description="Available room options per booking"
    )


class HotelRoomRatesResponseDTO(BaseModel):
    """FlightLogic Hotel API v6 get_room_rates response.

    Contains available room options for a specific hotel.
    """

    # Hotel identification
    hotelId: str = Field(..., description="Hotel ID")
    sessionId: str = Field(..., description="Session ID")
    tokenId: str = Field(..., description="Hotel token ID")

    # Room options (nested structure)
    roomRates: RoomRatesDTO = Field(..., description="Room rates with perBookingRates")

    # Hotel summary (may be included)
    hotelName: str | None = None
    city: str | None = None
    checkIn: str | None = None
    checkOut: str | None = None


# ============================================================
# BOOKING REQUEST/RESPONSE DTOs (Phase 2)
# ============================================================


class AdultDetailsDTO(BaseModel):
    """Adult passenger details for a room.

    Matches flight booking pattern - uses direct camelCase field names (no aliases).
    """

    title: list[str] = Field(
        ..., description="Array of adult titles (e.g., ['Mr', 'Mrs'])"
    )
    firstName: list[str] = Field(..., description="Array of adult first names")
    lastName: list[str] = Field(..., description="Array of adult last names")


class ChildDetailsDTO(BaseModel):
    """Child passenger details for a room.

    Matches flight booking pattern - uses direct camelCase field names (no aliases).
    """

    title: list[str] = Field(..., description="Array of child titles")
    firstName: list[str] = Field(..., description="Array of child first names")
    lastName: list[str] = Field(..., description="Array of child last names")


class PaxDetailsDTO(BaseModel):
    """Passenger details for a single room.

    Matches FlightLogic paxDetails structure exactly.
    """

    room_no: int = Field(..., ge=1, description="Room number (1-indexed)")
    adult: AdultDetailsDTO = Field(..., description="Adult passenger details")
    child: ChildDetailsDTO | None = Field(
        None, description="Child passenger details (optional)"
    )


class HotelBookingRequestDTO(BaseModel):
    """FlightLogic Hotel API v6 hotel_book request.

    Creates a hotel booking reservation.

    IMPORTANT: Uses camelCase field names (NOT snake_case).
    IMPORTANT: Does NOT require authentication fields (only hotel_search does).
    IMPORTANT: paxDetails uses snake_case internally (room_no, adult, child) - matches API exactly.
    """

    # Session & room identification (required) - camelCase!
    sessionId: str = Field(..., description="Session ID from search")
    productId: str = Field(..., description="Product ID from search results")
    tokenId: str = Field(..., description="Token ID from search results")
    rateBasisId: str = Field(..., description="Rate basis ID from get_rate_rules")

    # Booking identification (required)
    clientRef: str = Field(..., description="Client-generated booking reference")
    customerEmail: str = Field(..., description="Customer email address")
    customerPhone: str = Field(..., description="Customer phone number")
    bookingNote: str = Field(..., description="Booking notes/remarks")

    # Passenger details (required)
    paxDetails: list[PaxDetailsDTO] = Field(
        ..., description="Passenger details for each room"
    )


class RoomBookDetailsDTO(BaseModel):
    """Room booking details from successful booking."""

    hotelId: str = Field(..., description="Hotel ID")
    checkIn: str = Field(..., description="Check-in date")
    checkOut: str = Field(..., description="Check-out date")
    days: int = Field(..., description="Number of nights")
    currency: str = Field(..., description="Currency code")
    NetPrice: str | float = Field(..., description="Net price")
    fareType: str = Field(..., description="Fare type")
    cancellationPolicy: str = Field("", description="Cancellation policy")
    customerEmail: str = Field(..., description="Customer email")
    customerPhone: str = Field(..., description="Customer phone")
    rooms: list[dict[str, Any]] = Field(
        default_factory=list, description="Room details"
    )


class HotelBookingResponseDTO(BaseModel):
    """FlightLogic Hotel API v6 hotel_book response.

    Matches actual API structure from documentation.
    """

    # Main response fields (REQUIRED for success, but may be missing in error response)
    status: str | dict[str, Any] = Field(
        ..., description="CONFIRMED | PENDING | FAILED, or error dict"
    )
    supplierConfirmationNum: str | None = Field(
        None, description="Supplier confirmation number"
    )
    referenceNum: int | str | None = Field(None, description="API reference number")
    clientRefNum: str | None = Field(None, description="Client reference number")
    productId: str | None = Field(None, description="Product ID")
    roomBookDetails: RoomBookDetailsDTO | None = Field(
        None, description="Booking details"
    )
    error: str = Field("", description="Error message if booking failed")


# ============================================================
# RATE RULES DTOs (Check Room Rates)
# ============================================================


class HotelRateRulesRequestDTO(BaseModel):
    """FlightLogic Hotel API v6 get_rate_rules request.

    Used to validate rates before booking.

    IMPORTANT: Uses camelCase field names (NOT snake_case).
    IMPORTANT: Does NOT require authentication fields (only hotel_search does).
    """

    # Rate validation parameters (required) - camelCase!
    sessionId: str = Field(..., description="Session ID from search")
    productId: str = Field(..., description="Product ID from search results")
    tokenId: str = Field(..., description="Token ID from search results")
    rateBasisId: str = Field(..., description="Rate basis ID from room rates")


class RateRuleRoomDTO(BaseModel):
    """Single room rate from rate rules response."""

    productId: str
    roomType: str
    description: str = ""
    roomCode: str
    fareType: str
    rateBasisId: str
    currency: str
    netPrice: str | float  # FlightLogic may return string or float
    boardType: str = Field("", description="Meal plan")
    maxOccupancyPerRoom: str  # String in API, convert to int
    inventoryType: str  # prepaid/postpaid
    cancellationPolicy: str = ""
    roomImages: list[str] = Field(default_factory=list)
    facilities: list[str] = Field(default_factory=list)
    remark: str = ""


class HotelRateRulesResponseDTO(BaseModel):
    """FlightLogic Hotel API v6 get_rate_rules response.

    Contains validated rate information.
    """

    sessionId: str
    hotelId: str | int = Field(..., description="Hotel ID (string or int)")
    tokenId: str
    roomRates: dict[str, list[RateRuleRoomDTO]] = Field(
        ..., description="Contains 'perBookingRates' array"
    )


# ============================================================
# CANCEL BOOKING DTOs
# ============================================================


class HotelCancelRequestDTO(BaseModel):
    """FlightLogic Hotel API v6 cancel request.

    Cancels a hotel booking using supplier confirmation number and reference number.

    IMPORTANT: Requires authentication fields (user_id, user_password, access, ip_address).
    """

    # Authentication (required)
    user_id: str = Field(..., description="FlightLogic user ID")
    user_password: str = Field(..., description="FlightLogic password")
    access: Literal["Test", "Production"] = Field(..., description="API environment")
    ip_address: str = Field(..., description="IP address")

    # Booking identification (required)
    supplierConfirmationNum: str = Field(
        ..., description="Supplier confirmation number from booking response"
    )
    referenceNum: str = Field(..., description="Reference number from booking response")


class HotelCancelResponseDTO(BaseModel):
    """FlightLogic Hotel API v6 cancel response.

    Matches actual API structure from documentation.
    """

    status: str = Field(..., description="CANCELLED | FAILED")
    cancelReferenceNum: str | None = Field(
        None, description="Cancellation reference number"
    )
    message: str = Field(..., description="Cancellation message")


# ============================================================
# BOOKING DETAILS REQUEST/RESPONSE DTOs
# ============================================================


class HotelBookingDetailsRequestDTO(BaseModel):
    """FlightLogic Hotel API v6 bookingDetails request.

    Retrieves complete booking details using supplier confirmation number
    and reference number from the booking response.

    IMPORTANT: Requires authentication fields (user_id, user_password, access, ip_address).
    """

    # Authentication (required)
    user_id: str = Field(..., description="FlightLogic user ID")
    user_password: str = Field(..., description="FlightLogic password")
    access: Literal["Test", "Production"] = Field(..., description="API environment")
    ip_address: str = Field(..., description="IP address")

    # Booking identification (required)
    supplierConfirmationNum: str = Field(
        ..., description="Supplier confirmation number from booking response"
    )
    referenceNum: str = Field(..., description="Reference number from booking response")


class HotelBookingDetailsResponseDTO(BaseModel):
    """FlightLogic Hotel API v6 bookingDetails response.

    Contains complete booking details. The structure may vary based on
    the booking, so we use a flexible dict structure.

    FlightLogic API can return data in different formats:
    1. With roomBookDetails nested (most common)
    2. With bookingDetails wrapper
    3. Direct booking fields

    This DTO accepts all formats and the adapter handles normalization.
    """

    bookingDetails: dict[str, Any] = Field(
        default_factory=dict, description="Complete booking details"
    )
    roomBookDetails: dict[str, Any] | None = Field(
        None, description="Room booking details (alternative format)"
    )
    errors: dict[str, Any] | None = Field(None, description="Error details if any")
    error: str | dict[str, Any] | None = Field(
        None, description="Error field (singular)"
    )
    status: str | dict[str, Any] | None = Field(None, description="Status field")
    supplierConfirmationNum: str | None = Field(
        None, description="Supplier confirmation"
    )
    referenceNum: str | int | None = Field(None, description="Reference number")
    clientRefNum: str | None = Field(None, description="Client reference")
    productId: str | None = Field(None, description="Product ID")

    # Allow any additional fields from the actual API response
    model_config = {"extra": "allow"}


# ============================================================
# MORE RESULTS REQUEST/RESPONSE DTOs
# ============================================================


class HotelMoreResultsRequestDTO(BaseModel):
    """FlightLogic Hotel API v6 moreResults request.

    IMPORTANT: Uses camelCase field names (sessionId, nextToken, maxResult).
    IMPORTANT: Does NOT require authentication fields (only hotel_search does).
    """

    sessionId: str = Field(..., description="Session ID from hotel_search response")
    nextToken: str = Field(..., description="Next token from previous search response")
    maxResult: int = Field(20, ge=1, description="Maximum number of results to return")


class StatusMoreResultsDTO(BaseModel):
    """More results response status information.

    Note: This status object does NOT include totalResults field,
    only sessionId, moreResults, and nextToken.
    """

    sessionId: str = Field(..., description="FlightLogic session ID")
    moreResults: bool = Field(False, description="Whether more results are available")
    nextToken: str = Field("", description="Token for fetching next page")


class HotelMoreResultsItineraryDTO(BaseModel):
    """Single hotel itinerary from moreResults API response.

    Note: This differs from search API - total is numeric (not string)
    and perNightArray is not included in the response.
    """

    # Identification (required)
    hotelId: str = Field(..., description="Hotel ID")
    twxHotelId: str | int = Field(
        ..., description="TravelNext internal hotel ID (API may return int or str)"
    )
    productId: str = Field(..., description="Product/supplier code")
    tokenId: str = Field(
        ..., description="CRITICAL: Required for get_room_rates API call"
    )

    # Basic info (required)
    hotelName: str = Field(..., description="Hotel name")
    city: str | None = Field(
        None, description="City name (may be null for some hotels)"
    )
    locality: str | None = Field(
        None, description="Neighborhood/area (may be empty or null)"
    )
    address: str | None = Field(
        None, description="Street address (may be null for some hotels)"
    )
    country: str | None = Field(None, description="Country name (may be empty or null)")
    countryCode: str | None = Field(
        None, description="ISO country code (may be empty or null)"
    )
    postalCode: str | None = Field(None, description="Postal/ZIP code (may be null)")

    # Location (may be null for some hotels)
    latitude: str | None = Field(
        None, description="Latitude (20 decimal places precision, may be null)"
    )
    longitude: str | None = Field(
        None, description="Longitude (20 decimal places precision, may be null)"
    )
    distanceValue: float = Field(..., description="Distance from search center")
    distanceUnit: str = Field(..., description="Distance unit (KM or MI)")

    # Pricing (required) - Note: total is numeric in moreResults API, not string
    total: float | int = Field(
        ..., description="Total price for entire stay (numeric, not string)"
    )
    # Note: perNightArray is NOT included in moreResults API response
    currency: str = Field(..., description="ISO 4217 currency code")
    fareType: str = Field(..., description="Refundable | Non-Refundable")

    # Hotel details
    hotelRating: float | str | int | None = Field(
        None, description="Star rating (API may return as int, float, string, or null)"
    )
    propertyType: str = Field("", description="Property type (hotel, resort, etc.)")
    facilities: list[str] = Field(default_factory=list, description="List of amenities")
    thumbNailUrl: str = Field(..., description="Thumbnail image URL")

    # Contact
    phone: str | None = Field(
        None, description="Comma-separated phone numbers (may be null)"
    )
    email: str | None = Field(None, description="Contact email (may be null or empty)")

    # Reviews
    tripAdvisorRating: float | str | int = Field(
        0, description="TripAdvisor rating (API may return float as string)"
    )
    tripAdvisorReview: int | str = Field(
        0, description="Number of TripAdvisor reviews (may be string in some responses)"
    )

    # Special offers
    special: str = Field("", description="Special offers/notes (may be empty)")


class HotelMoreResultsResponseDTO(BaseModel):
    """FlightLogic Hotel API v6 moreResults response.

    Top-level response structure containing status and hotel itineraries.
    Note: Status does not include totalResults field.
    Note: Itineraries use different structure (no perNightArray, numeric total).
    """

    status: StatusMoreResultsDTO = Field(
        ..., description="Response status and pagination info"
    )
    itineraries: list[HotelMoreResultsItineraryDTO] = Field(
        default_factory=list, description="List of additional hotel search results"
    )
