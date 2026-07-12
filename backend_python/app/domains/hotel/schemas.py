"""Hotel domain schemas.

Pydantic v2 models for hotel search, bookings, and related operations.
Uses Decimal for all monetary values to ensure precision.

Note: These are domain models (business logic layer), not DTOs.
The integration layer handles conversion to/from FlightLogic API format.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.domains.flight.enums import FlightAPIEnvironment

from .constants import (
    DEFAULT_CURRENCY,
    MAX_ADULTS_PER_ROOM,
    MAX_CHILDREN_PER_ROOM,
    MAX_MAX_RESULT,
    MAX_NIGHTS,
    MAX_ROOMS,
    MIN_ADULTS_PER_ROOM,
    MIN_MAX_RESULT,
    MIN_NIGHTS,
    MIN_ROOMS,
)

# =============================================================================
# Base Models
# =============================================================================


class BaseHotelLogicRequest(BaseModel):
    """Base for FlightLogic hotel API requests.

    Optional credential fields - will use config defaults if not provided.
    """

    user_id: str | None = Field(
        None, description="FlightLogic user ID (uses config if not provided)"
    )
    user_password: str | None = Field(
        None, description="FlightLogic password (uses config if not provided)"
    )
    access: FlightAPIEnvironment | None = Field(
        None, description="API environment (uses config if not provided)"
    )
    ip_address: str | None = Field(
        None, description="IP address (uses config if not provided)"
    )


# =============================================================================
# Search Request/Response Models
# =============================================================================


class OccupancyRoom(BaseModel):
    """Occupancy details for a single room."""

    room_no: int = Field(..., ge=1, description="Room number (1-indexed)")
    adult: int = Field(..., ge=MIN_ADULTS_PER_ROOM, le=MAX_ADULTS_PER_ROOM)
    child: int = Field(0, ge=0, le=MAX_CHILDREN_PER_ROOM)
    child_age: list[int] = Field(
        default_factory=lambda: [0],
        description="Ages of children (use [0] if no children)",
    )

    @model_validator(mode="after")
    def validate_child_ages(self) -> OccupancyRoom:
        """Ensure child_age list matches child count."""
        if self.child > 0 and len(self.child_age) != self.child:
            msg = f"child_age must have {self.child} entries for {self.child} children"
            raise ValueError(msg)
        if self.child == 0 and self.child_age != [0]:
            self.child_age = [0]
        return self


class NearbyLocation(BaseModel):
    """Reference point for distance-based hotel sorting.

    When provided in a search request, hotels are sorted by Haversine distance
    from this point (nearest first). Hotels with missing coordinates are appended last.
    """

    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lng: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")


class HotelSearchRequest(BaseHotelLogicRequest):
    """Hotel search request parameters.

    Supports city-based, geolocation-based, and hotel-code-based searches.
    """

    # Dates (required)
    checkin: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    checkout: str = Field(..., description="Check-out date (YYYY-MM-DD)")

    # Search criteria (at least one required)
    city_name: str | None = Field(None, min_length=2, description="City name")
    country_name: str | None = Field(None, min_length=2, description="Country name")
    latitude: float | None = Field(None, description="Latitude for geolocation search")
    longitude: float | None = Field(
        None, description="Longitude for geolocation search"
    )
    hotel_codes: list[str] | None = Field(
        None, max_length=1000, description="Hotel codes (max 1000)"
    )

    # Optional search parameters
    radius: int | None = Field(None, ge=1, description="Search radius in KM (OPTIONAL)")
    max_result: int | None = Field(
        default=MAX_MAX_RESULT,
        ge=MIN_MAX_RESULT,
        le=MAX_MAX_RESULT,
        alias="maxResult",
        description="Max results (≥20, default 9999999999 when omitted)",
    )
    results_per_page: int | None = Field(
        None,
        ge=1,
        alias="resultsPerPage",
        description="Results per page for pagination",
    )

    # Occupancy (required)
    occupancy: list[OccupancyRoom] = Field(
        ..., min_length=MIN_ROOMS, max_length=MAX_ROOMS
    )

    # Currency and language
    required_currency: str = Field(
        DEFAULT_CURRENCY, min_length=3, max_length=3, alias="requiredCurrency"
    )
    required_language: str | None = Field(
        None, alias="requiredLanguage", description="Language code for descriptions"
    )
    nationality: str | None = Field(
        None,
        min_length=2,
        max_length=2,
        description="Guest nationality (ISO 3166-1 alpha-2)",
    )

    # Optional nearby-location sort
    nearby_location: NearbyLocation | None = Field(
        None,
        description="Reference point for distance-based sorting (nearest first). "
        "When provided, hotels are sorted by Haversine distance from this point; "
        "hotels missing coordinates are appended last.",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> HotelSearchRequest:
        """Validate check-in and check-out dates."""
        try:
            # Using naive datetime for date-only validation (no timezone needed)
            checkin_date = datetime.strptime(self.checkin, "%Y-%m-%d").date()  # noqa: DTZ007
            checkout_date = datetime.strptime(self.checkout, "%Y-%m-%d").date()  # noqa: DTZ007
        except ValueError as e:
            msg = "Dates must be in YYYY-MM-DD format"
            raise ValueError(msg) from e

        if checkout_date <= checkin_date:
            msg = "Check-out date must be after check-in date"
            raise ValueError(msg)

        nights = (checkout_date - checkin_date).days
        if nights < MIN_NIGHTS:
            msg = f"Minimum {MIN_NIGHTS} night(s) required"
            raise ValueError(msg)
        if nights > MAX_NIGHTS:
            msg = f"Maximum {MAX_NIGHTS} nights allowed"
            raise ValueError(msg)

        # Using naive date.today() for date comparison (no timezone needed)
        today = date.today()  # noqa: DTZ011
        if checkin_date < today:
            msg = "Check-in date cannot be in the past"
            raise ValueError(msg)

        return self

    @model_validator(mode="after")
    def validate_search_criteria(self) -> HotelSearchRequest:
        """Ensure at least one search method is specified."""
        has_city = bool(self.city_name and self.country_name)
        has_geo = bool(self.latitude is not None and self.longitude is not None)
        has_codes = bool(self.hotel_codes)

        if not (has_city or has_geo or has_codes):
            msg = "Must provide either (city_name + country_name), (latitude + longitude), or hotel_codes"
            raise ValueError(msg)

        return self


class PerNightPrice(BaseModel):
    """Price breakdown for a single night."""

    night_index: int = Field(..., ge=1, description="Night number (1-indexed)")
    currency: str = Field(..., min_length=3, max_length=3)
    price: Decimal = Field(..., description="Price for this night")


class HotelSearchResult(BaseModel):
    """Single hotel from search results.

    Maps to the FlightLogic API hotel itinerary structure.
    """

    # Identification
    hotel_id: str = Field(..., description="Hotel ID")
    twx_hotel_id: str = Field(..., description="TravelNext internal ID")
    product_id: str = Field(..., description="Product/supplier code")
    token_id: str = Field(..., description="CRITICAL: Required for room rates API")

    # Basic info
    hotel_name: str = Field(..., description="Hotel name")
    city: str | None = Field(
        None, description="City name (may be null for some hotels)"
    )
    locality: str = Field("", description="Neighborhood/area")
    address: str | None = Field(None, description="Street address (may be null)")
    country: str = Field("", description="Country name")
    country_code: str = Field("", description="ISO country code")
    postal_code: str = Field("", description="Postal code (may be empty)")

    # Location (strings with high precision from API, may be null)
    latitude: str | None = Field(None, description="Decimal degrees (may be null)")
    longitude: str | None = Field(None, description="Decimal degrees (may be null)")
    distance_value: float = Field(..., description="Distance from search center")
    distance_unit: str = Field(..., description="Distance unit (KM or MI)")

    # Pricing (total is for ENTIRE STAY, not per night)
    total: Decimal = Field(
        ..., description="Total price for entire stay (with platform fee)"
    )
    currency: str = Field(..., min_length=3, max_length=3)
    fare_type: str = Field(..., description="Refundable | Non-Refundable")
    per_night_array: list[PerNightPrice] = Field(
        ..., description="Per-night price breakdown"
    )
    # Platform fee fields (set by pricing module)
    original_total: Decimal | None = Field(
        None,
        description="Original total price before platform fee (for frontend calculation)",
    )
    platform_fee_percentage: float | None = Field(
        None, description="Platform fee percentage (10.5% for hotels)"
    )

    # Hotel details
    hotel_rating: int | None = Field(
        None, ge=0, le=5, description="Star rating 0-5 (may be null)"
    )
    property_type: str = Field("", description="Property type")
    facilities: list[str] = Field(default_factory=list, description="List of amenities")
    thumbnail_url: str = Field(
        ...,
        description="Hotel image URL (max 800px width via imgproxy)",
    )

    # Contact
    phone: str | None = Field(
        None, description="Comma-separated phone numbers (may be null)"
    )
    email: str = Field("", description="Contact email")

    # Reviews
    trip_advisor_rating: int = Field(0, ge=0, description="TripAdvisor rating")
    trip_advisor_review: int = Field(
        0, ge=0, description="Number of TripAdvisor reviews"
    )

    # Special offers
    special: str = Field("", description="Special offers/notes")

    # Distance from caller-supplied nearby_location (set by service layer, None when not requested)
    nearby_distance_km: float | None = Field(
        None,
        description="Haversine distance in km from the requested nearby_location reference point. "
        "None when nearby_location was not provided or hotel coordinates are unavailable.",
    )

    def get_lat_lng(self) -> tuple[float, float] | None:
        """Convert string coordinates to floats for mapping.

        Returns:
            Tuple of (latitude, longitude) as floats, or None if coordinates unavailable
        """
        if self.latitude is None or self.longitude is None:
            return None
        return (float(self.latitude), float(self.longitude))

    def get_nights(self) -> int:
        """Calculate number of nights from per_night_array.

        Returns:
            Number of nights
        """
        return len(self.per_night_array)


class HotelSearchResponse(BaseModel):
    """Hotel search API response.

    Contains session information and list of available hotels.
    """

    session_id: str = Field(
        ..., description="FlightLogic session ID (20-minute expiry)"
    )
    total_results: int = Field(..., description="Total hotels found")
    more_results: bool = Field(False, description="Whether more results available")
    next_token: str = Field("", description="Token for pagination")
    itineraries: list[HotelSearchResult] = Field(
        default_factory=list, description="List of hotels"
    )


class HotelMoreResultsRequest(BaseHotelLogicRequest):
    """Request for additional hotel search results.

    Used to fetch more results when moreResults is true in the search response.
    """

    session_id: str = Field(..., description="Session ID from hotel search response")
    next_token: str = Field(..., description="Next token from previous search response")
    max_result: int = Field(
        20, ge=1, le=100, description="Maximum number of results to return"
    )
    # Pass nearby_location again so each paginated page is independently distance-sorted.
    # Note: combined order across pages is per-page sorted, not globally sorted.
    nearby_location: NearbyLocation | None = Field(
        None,
        description="Reference point for distance-based sorting (nearest first). "
        "Each page is independently sorted; not globally sorted across all pages.",
    )


# =============================================================================
# Room Rates Models (for Phase 2)
# =============================================================================


class RoomOption(BaseModel):
    """Individual room option with pricing details."""

    room_type: str = Field(..., description="Room category/type")
    rate_basis_id: str = Field(..., description="CRITICAL: Required for booking")
    price_per_night: Decimal = Field(
        ..., description="Price per night (with platform fee)"
    )
    total_price: Decimal = Field(
        ..., description="Total price for stay (with platform fee)"
    )
    currency: str = Field(..., min_length=3, max_length=3)
    meal_plan: str = Field("", description="Meal plan included")
    cancellation_policy: str = Field("", description="Cancellation terms")
    max_occupancy: dict[str, int] = Field(
        default_factory=dict, description="Max adults/children"
    )
    rooms_available: int = Field(0, ge=0, description="Rooms available")
    images: list[str] = Field(default_factory=list, description="Room image URLs")
    # Platform fee fields (set by pricing module)
    original_price_per_night: Decimal | None = Field(
        None,
        description="Original price per night before platform fee (for frontend calculation)",
    )
    original_total_price: Decimal | None = Field(
        None,
        description="Original total price before platform fee (for frontend calculation)",
    )
    platform_fee_percentage: float | None = Field(
        None, description="Platform fee percentage (10.5% for hotels)"
    )


class HotelRoomRatesRequest(BaseHotelLogicRequest):
    """Request for detailed room rates.

    IMPORTANT: FlightLogic API requires sessionId, tokenId, productId, hotelId (camelCase).
    These will be converted to camelCase by the adapter.
    """

    session_id: str = Field(..., description="Session ID from search")
    token_id: str = Field(..., description="Hotel token from search results")
    product_id: str = Field(..., description="Product ID from search results")
    hotel_id: str = Field(..., description="Hotel ID from search results")


class HotelRoomRatesResponse(BaseModel):
    """Room rates API response."""

    hotel_id: str
    session_id: str
    token_id: str
    rooms: list[RoomOption] = Field(default_factory=list)


# =============================================================================
# Rate Rules Models
# =============================================================================


class HotelRateRulesRequest(BaseHotelLogicRequest):
    """Request for rate validation before booking."""

    session_id: str = Field(..., description="Session ID from search")
    token_id: str = Field(..., description="Hotel token from search results")
    product_id: str = Field(..., description="Product ID from search results")
    rate_basis_id: str = Field(..., description="Rate basis ID from room rates")


class HotelRateRulesResponse(BaseModel):
    """Rate rules API response with validated pricing."""

    session_id: str
    hotel_id: str
    token_id: str
    room_type: str
    description: str = ""
    room_code: str
    fare_type: str
    rate_basis_id: str
    currency: str
    net_price: Decimal = Field(..., description="Net price (with platform fee applied)")
    board_basis: str = Field("", description="Meal plan included")
    max_occupancy_per_room: int
    inventory_type: str  # prepaid/postpaid
    cancellation_policy: str = ""
    facilities: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list, description="Room image URLs")
    remark: str = Field("", description="Special benefits or requirements")
    # Platform fee fields (set by pricing module)
    original_net_price: Decimal | None = Field(
        None,
        description="Original net price before platform fee (for frontend calculation)",
    )
    platform_fee_percentage: float | None = Field(
        None, description="Platform fee percentage (10.5% for hotels)"
    )


# =============================================================================
# Booking Models (for Phase 2)
# =============================================================================


class GuestInfo(BaseModel):
    """Guest information for booking - single guest."""

    title: str = Field(..., description="Mr | Mrs | Miss (for adults)")
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    room_number: int = Field(
        1, ge=1, description="Room number (1-indexed) for multi-room bookings"
    )
    is_child: bool = Field(
        False, description="True if guest is a child, False if adult"
    )


class HotelBookingRequest(BaseHotelLogicRequest):
    """Hotel booking creation request.

    IMPORTANT: FlightLogic API requires camelCase fields and paxDetails structure.
    The adapter will convert this domain model to the correct DTO format.
    """

    # Session & room identification
    session_id: str = Field(..., description="Session ID from search")
    product_id: str = Field(..., description="Product ID from search results")
    token_id: str = Field(..., description="Token ID from search results")
    rate_basis_id: str = Field(..., description="Rate basis ID from get_rate_rules")

    # Booking identification
    client_ref: str = Field(
        ..., description="Client-generated booking reference (VOYA ref)"
    )
    customer_email: str = Field(..., description="Customer email address")
    customer_phone: str = Field(
        ..., description="Customer phone number with country code"
    )
    booking_note: str = Field(..., description="Booking notes/remarks")

    # Guest details (simplified - adapter will convert to paxDetails format)
    guests: list[GuestInfo] = Field(
        ..., description="Guest details (adults and children)"
    )
    room_count: int = Field(1, ge=1, description="Number of rooms being booked")

    # Payment (optional - required for prepaid bookings)
    payment_intent_id: str | None = Field(
        None,
        description="Stripe PaymentIntent ID (pi_*) or Revolut order ID (UUID) for payment validation",
    )

    # Profile / booking_events snapshot only; not sent to FlightLogic book API
    hotel_image_url: str | None = Field(
        default=None,
        description="Property image URL to persist on booking_events (e.g. SPA sends at book time)",
    )
    hotel_name: str | None = Field(
        default=None,
        description="Hotel display name to persist on booking_events",
    )
    hotel_city: str | None = Field(
        default=None,
        description="City to persist on booking_events",
    )
    hotel_address: str | None = Field(
        default=None,
        description="Property street address to persist on booking_events",
    )
    hotel_latitude: float | None = Field(
        default=None,
        description="Property latitude (WGS84) to persist on booking_events for maps",
    )
    hotel_longitude: float | None = Field(
        default=None,
        description="Property longitude (WGS84) to persist on booking_events for maps",
    )
    saved_itinerary_id: str | None = Field(
        None,
        description="Optional saved itinerary id to link this booking after successful confirmation",
    )
    voucher_redemption_id: str | None = Field(
        default=None,
        description="Discounts collection id from POST /vouchers/apply; client_ref must match reservation",
    )
    parent_voya_booking_reference: str | None = Field(
        default=None,
        description="Shared group reference for multi-stay bookings (all legs share this ref)",
    )
    multistay_leg_index: int | None = Field(
        default=None,
        ge=0,
        le=50,
        description="Zero-based leg index for multi-stay bookings (used for ordering legs)",
    )

    @model_validator(mode="after")
    def validate_each_room_has_adult(self) -> HotelBookingRequest:
        """Validate that each room has at least one adult guest."""
        # Group guests by room number
        rooms_with_adults: dict[int, bool] = {}
        for guest in self.guests:
            if not guest.is_child:
                rooms_with_adults[guest.room_number] = True

        # Check that all rooms (1 to room_count) have at least one adult
        for room_no in range(1, self.room_count + 1):
            if room_no not in rooms_with_adults:
                raise ValueError(
                    f"Room {room_no} must have at least one adult guest. "
                    f"Hotels require a responsible adult in each room."
                )
        return self


class HotelBookingResponse(BaseModel):
    """Hotel booking API response."""

    status: str = Field(..., description="Success | Failed")
    supplier_confirmation_num: str | None = Field(
        None, description="FlightLogic confirmation number"
    )
    reference_num: str | None = Field(None, description="FlightLogic reference number")
    voya_booking_reference: str | None = Field(
        None, description="VOYA booking reference (VOYA-xxx)"
    )
    booking_details: dict[str, Any] = Field(default_factory=dict)
    errors: dict[str, Any] | None = None


# =============================================================================
# Cancellation Models
# =============================================================================


class HotelCancelRequest(BaseHotelLogicRequest):
    """Hotel booking cancellation request.

    Requires supplier confirmation number and reference number from booking response.
    """

    supplier_confirmation_num: str = Field(
        ..., description="Supplier confirmation number from booking response"
    )
    reference_num: str = Field(
        ..., description="Reference number from booking response"
    )


class HotelCancelResponse(BaseModel):
    """Hotel cancellation API response."""

    status: str = Field(..., description="CANCELLED | FAILED")
    cancel_reference_num: str | None = Field(
        None, description="Cancellation reference number"
    )
    message: str = Field(..., description="Cancellation message")
    errors: dict[str, Any] | None = None


# =============================================================================
# Booking Details Models
# =============================================================================


class HotelBookingDetailsRequest(BaseHotelLogicRequest):
    """Hotel booking details request.

    Retrieves complete booking details using supplier confirmation number
    and reference number from the booking response.
    """

    supplier_confirmation_num: str = Field(
        ..., description="Supplier confirmation number from booking response"
    )
    reference_num: str = Field(
        ..., description="Reference number from booking response"
    )


class HotelBookingDetailsResponse(BaseModel):
    """Hotel booking details API response."""

    booking_details: dict[str, Any] = Field(
        default_factory=dict, description="Complete booking details"
    )
    errors: dict[str, Any] | None = None


# =============================================================================
# Trip Details (by VOYA reference) — mirrors flights' TripDetailsRequest/Response
# =============================================================================


class HotelTripDetailsRequest(BaseModel):
    """Hotel trip details request — lookup by VOYA booking reference.

    Frontend sends voya_booking_reference; backend resolves supplier refs
    from the booking event and calls get_booking_details internally.

    When auth_token is provided (email link flow), backend decodes it and
    verifies the token's user_id matches the booking event's user_id.
    """

    voya_booking_reference: str = Field(
        ..., description="VOYA internal booking reference (VOYA-XXXXXXXXXX)"
    )
    auth_token: str | None = Field(
        None,
        description="Optional: short-lived JWT from email link; when present, token's user_id must match booking owner",
    )


class HotelTripDetailsResponse(BaseModel):
    """Hotel trip details response — returned to frontend booking details page."""

    success: bool = Field(..., description="Whether details were retrieved")
    voya_booking_reference: str | None = Field(
        None, description="VOYA booking reference echoed back"
    )
    booking_status: str | None = Field(
        None, description="Booking status from event (BOOKED/CANCELLED)"
    )
    booking_details: dict[str, Any] = Field(
        default_factory=dict, description="Complete booking details from supplier"
    )
    errors: list[str] | None = None


class HotelMyBookingListItem(BaseModel):
    """Stable JSON item for GET /hotels/my-bookings (profile list)."""

    voya_booking_reference: str | None = Field(
        None, description="VOYA-XXXXXXXXXX when assigned"
    )
    action: Literal["BOOKED", "CANCELLED", "PENDING"] = Field(
        ..., description="Event action from booking_events"
    )
    timestamp: datetime = Field(..., description="When the booking event was recorded")
    date_booked: datetime | None = Field(
        None, description="Supplier confirmation time when known (UTC)"
    )
    amount: float | None = Field(
        None, description="Total in major currency units when stored on the event"
    )
    hotel_image_url: str | None = Field(
        None, description="Property thumbnail URL persisted at book time"
    )
    hotel_name: str | None = Field(None, description="Hotel name snapshot at book time")
    hotel_city: str | None = Field(None, description="City snapshot at book time")
    hotel_check_in_date: str | None = Field(
        None,
        description="Check-in YYYY-MM-DD (property-local) when stored on the event",
    )
    hotel_check_out_date: str | None = Field(
        None, description="Check-out YYYY-MM-DD when stored on the event"
    )
    hotel_nights: int | None = Field(
        None, description="Number of nights when stored on the event"
    )
