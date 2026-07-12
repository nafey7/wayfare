"""Booking log domain schemas - Simplified booking event schemas.

This module contains simplified schemas for booking events.
Only essential information is stored - details are fetched on-demand.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.database.flight_route import RouteLeg
from app.shared.flight_leg_summary import FlightLegSummary
from app.shared.schemas import StrictModel

# ============================================================
# SIMPLIFIED BOOKING SCHEMAS
# ============================================================


class TicketStatusSnapshotResponse(StrictModel):
    """Snapshot of ticket status from a trip-details fetch."""

    status: str
    time: datetime


class BookingAction(StrictModel):
    """Simplified booking action - just the essentials."""

    external_booking_reference: str = Field(
        ..., description="FlightLogic booking reference"
    )
    action: Literal["BOOKED", "CANCELLED", "PENDING"] = Field(
        ..., description="Action performed; PENDING = GDS awaiting FlightLogic booking"
    )


# Legacy content schemas - kept for backwards compatibility
# These are no longer used for new bookings
class FlightContent(StrictModel):
    """Legacy flight content - kept for old data."""

    flight_number: str | None = None
    airline: str | None = None
    origin: str | None = None
    destination: str | None = None
    departure_time: datetime | None = None
    arrival_time: datetime | None = None
    external_booking_reference: str | None = None
    flightlogic_booking_id: str | None = None


class HotelContent(StrictModel):
    """Legacy hotel content."""

    name: str | None = None
    external_booking_reference: str | None = None


class ActivityContent(StrictModel):
    """Legacy activity content."""

    name: str | None = None
    external_booking_reference: str | None = None


class NoteContent(StrictModel):
    """Legacy note content."""

    text: str | None = None
    tags: list[str] | None = Field(default=None)


# ============================================================
# REQUEST SCHEMAS (API Input)
# ============================================================


class CreateBookingEventRequest(StrictModel):
    """Request to create a new booking event - simplified version."""

    external_booking_reference: str = Field(
        ...,
        description="FlightLogic booking reference; use TEMP-REF when creating LCC event before booking API",
    )
    action: Literal["BOOKED", "CANCELLED", "PENDING"] = Field(
        ..., description="Action performed; PENDING = GDS awaiting FlightLogic booking"
    )
    event_type: Literal["FLIGHT", "HOTEL"] = Field(
        default="FLIGHT", description="Type of booking"
    )

    # Optional PNR fields (default=None required for pydantic.mypy init_typed)
    airline_pnr_code: str | None = Field(
        default=None, description="Airline PNR code (6-character)"
    )
    airline_pnr_airline_code: str | None = Field(
        default=None, description="IATA code of airline that issued PNR"
    )
    airline_pnr_airline_name: str | None = Field(
        default=None, description="Name of airline that issued PNR"
    )
    airline_pnr_status: str | None = Field(default=None, description="PNR status")
    # PNR list from trip details (flights only)
    pnr: list[str] | None = Field(
        default=None,
        description="Airline PNR codes from trip details (may vary per segment)",
    )
    ticket_status: str | None = Field(
        default=None,
        description="Latest ticket status synchronized from trip details",
    )
    e_ticket_numbers: list[str] | None = Field(
        default=None,
        description="Passenger e-ticket numbers synchronized from trip details",
    )
    flight_leg_summaries: list[FlightLegSummary] | None = Field(
        None,
        description="Leg-level itinerary snapshot (optional at create; usually from trip_details sync)",
    )
    flight_segment_departure_dates: list[str] | None = Field(
        None,
        description="Per-segment departure dates YYYY-MM-DD (UTC); from trip_details sync",
    )

    # Contact information for email routing
    contact_email: str | None = Field(
        default=None,
        description="Original contact email from booking request (for email routing)",
    )

    # Cancellation policy text from fare rules
    cancellation_policy_text: str | None = Field(
        default=None,
        description="Cancellation policy text from fare rules (stored for ticket email)",
    )

    # Ticket time limit (UTC) - for validation before payment processing
    ticket_time_limit: datetime | None = Field(
        default=None,
        description="Ticket time limit in UTC (converted from departure city local time)",
    )

    # Departure airport IATA — legacy TTL helpers; also set from route_legs[0] first hop
    departure_airport_iata: str | None = Field(
        default=None,
        description="IATA code of departure airport (e.g., 'JFK', 'LHR') for timezone conversion",
    )
    flight_trip_type: Literal["one_way", "round_trip", "multi_city"] | None = Field(
        default=None,
        description="Persisted trip type for this booking row",
    )
    route_legs: list[RouteLeg] | None = Field(
        default=None,
        description="Structured route: legs with segment-level IATA hops",
    )
    primary_marketing_airline_name: str | None = Field(
        default=None,
        description="Marketing carrier display name for list cards",
    )

    # Flight carrier type: GDS or LCC (WebFare); only for FLIGHT events
    carrier_type: Literal["GDS", "LCC"] | None = Field(
        default=None,
        description="GDS or LCC (WebFare) for flight bookings; None for hotel or cancellation-only",
    )

    # Payment intent ID - set at creation for LCC (pay-before-book); GDS may get it later via webhook
    payment_intent_id: str | None = Field(
        default=None,
        description="Stripe payment intent ID (pi_xxx); pass when booking is created after payment (e.g. LCC)",
    )
    # Optional: use this ref instead of generating (e.g. hotel: from Revolut metadata)
    voya_booking_reference: str | None = Field(
        default=None,
        description="Use this ref instead of generating; from Revolut order metadata for hotel bookings",
    )

    # FlightLogic booking API payload - stored for admin retry (LCC) and audit; not exposed in API responses
    payload: dict | None = Field(
        default=None,
        description="Exact JSON body sent to FlightLogic booking endpoint; stored at creation (GDS) or before API call (LCC)",
    )

    # Optional: set when creating event with known amount (e.g. at creation after booking API)
    amount: float | None = Field(
        default=None,
        description="Total original amount of the booking (flight or hotel)",
    )
    # Optional: date booked in UTC (e.g. when creating GDS event at booking API success)
    date_booked: datetime | None = Field(
        default=None,
        description="When the booking was confirmed by the supplier (UTC)",
    )
    # Optional: date paid in UTC (e.g. when creating hotel event after payment validation)
    date_paid: datetime | None = Field(
        default=None,
        description="When payment was completed successfully (UTC)",
    )

    # HOTEL-only display fields (from session at book time)
    hotel_image_url: str | None = Field(
        None,
        description="Property thumbnail URL; HOTEL events only",
    )
    hotel_name: str | None = Field(
        None,
        description="Hotel name snapshot; HOTEL events only",
    )
    hotel_city: str | None = Field(
        None,
        description="City snapshot; HOTEL events only",
    )
    hotel_address: str | None = Field(
        None,
        description="Property address snapshot; HOTEL events only",
    )
    hotel_latitude: float | None = Field(
        None,
        description="Property latitude (WGS84); HOTEL events only",
    )
    hotel_longitude: float | None = Field(
        None,
        description="Property longitude (WGS84); HOTEL events only",
    )
    hotel_check_in_date: str | None = Field(
        None,
        description="Check-in YYYY-MM-DD; HOTEL events only (supplier overwrites on book)",
    )
    hotel_check_out_date: str | None = Field(
        None,
        description="Check-out YYYY-MM-DD; HOTEL events only",
    )
    hotel_nights: int | None = Field(
        None,
        description="Stay length in nights when known; HOTEL events only",
    )
    # Optional link to saved itinerary (caller must validate ownership)
    saved_itinerary_id: str | None = Field(
        None,
        description="MongoDB ObjectId string of saved itinerary to associate with this event",
    )
    parent_voya_booking_reference: str | None = Field(
        default=None,
        description="Optional multicity group id shared by all leg booking events (e.g. VOYA-MC-…)",
    )
    multistay_leg_index: int | None = Field(
        default=None,
        description="Zero-based itinerary leg index for multi-stay/multicity (persisted for group list ordering)",
    )

    voucher_redemption_id: str | None = Field(
        default=None,
        description="Discounts collection _id (from /vouchers/apply). Linked on this row; "
        "a VOYA ref is generated when omitted.",
    )


class UpdateBookingEventRequest(StrictModel):
    """Request to update a booking event - simplified."""

    action: Literal["BOOKED", "CANCELLED", "PENDING"] | None = Field(
        default=None, description="Update action"
    )


# ============================================================
# RESPONSE SCHEMAS (API Output)
# ============================================================


class BookingEventResponse(StrictModel):
    """Response with booking event details - simplified."""

    id: str
    user_id: str

    # Booking reference fields
    voya_booking_reference: str = Field(
        ..., description="VOYA internal booking reference"
    )
    external_booking_reference: str = Field(..., description="FlightLogic UniqueID")

    action: Literal["BOOKED", "CANCELLED", "PENDING"]
    timestamp: datetime
    event_type: Literal["FLIGHT", "HOTEL"]

    # Optional PNR fields
    airline_pnr_code: str | None = Field(
        None, description="Airline PNR code (6-character)"
    )
    airline_pnr_airline_code: str | None = Field(
        None, description="IATA code of airline that issued PNR"
    )
    airline_pnr_airline_name: str | None = Field(
        None, description="Name of airline that issued PNR"
    )
    airline_pnr_status: str | None = Field(None, description="PNR status")

    # Contact information for email routing
    contact_email: str | None = Field(
        None,
        description="Original contact email from booking request (for email routing)",
    )

    # Cancellation policy text from fare rules
    cancellation_policy_text: str | None = Field(
        None,
        description="Cancellation policy text from fare rules (stored for ticket email)",
    )

    # Ticket time limit (UTC) - for validation before payment processing
    ticket_time_limit: datetime | None = Field(
        None,
        description="Ticket time limit in UTC (converted from departure city local time)",
    )

    # Departure IATA — mirrors first hop of route_legs when present (TTL / legacy consumers)
    departure_airport_iata: str | None = Field(
        None,
        description="IATA code of departure airport (e.g., 'JFK', 'LHR') for timezone conversion",
    )
    flight_trip_type: Literal["one_way", "round_trip", "multi_city"] | None = Field(
        None,
        description="one_way | round_trip | multi_city",
    )
    route_legs: list[RouteLeg] | None = Field(
        None,
        description="Structured route snapshot (legs and segment hops)",
    )
    primary_marketing_airline_name: str | None = Field(
        None,
        description="Marketing carrier display name for list cards",
    )

    # Flight carrier type: GDS or LCC (WebFare); only for FLIGHT events
    carrier_type: Literal["GDS", "LCC"] | None = Field(
        None,
        description="GDS or LCC (WebFare) for flight bookings; None for hotel or legacy events",
    )

    # Payment intent ID - stored when payment intent is created (for reuse and tracking)
    payment_intent_id: str | None = Field(
        None,
        description="Stripe payment intent ID (pi_xxx) - stored when payment intent is created",
    )

    # Date booked (UTC)
    date_booked: datetime | None = Field(
        None,
        description="When the booking was confirmed by the supplier (UTC)",
    )
    # Date paid (UTC)
    date_paid: datetime | None = Field(
        None,
        description="When payment was completed successfully (UTC)",
    )
    # Date tickets issued (UTC)
    date_tickets_issued: datetime | None = Field(
        None,
        description="When tickets/confirmation was issued (UTC)",
    )
    # Total original amount
    amount: float | None = Field(
        None,
        description="Total original amount of the booking (flight or hotel)",
    )
    # Confirmation email sent; None when not set (legacy/unknown)
    confirmation_email_sent: bool | None = Field(
        None,
        description="True if the booking/ticket confirmation email was sent successfully; None when unknown",
    )
    # PNR list from trip details (flights; array of strings)
    pnr: list[str] | None = Field(
        None,
        description="Airline PNR codes from trip details (may vary per segment)",
    )
    ticket_status: str | None = Field(
        None, description="Latest ticket status synchronized from trip details"
    )
    e_ticket_numbers: list[str] | None = Field(
        None,
        description="Passenger e-ticket numbers synchronized from trip details",
    )
    flight_leg_summaries: list[FlightLegSummary] | None = Field(
        None,
        description="Leg-level itinerary snapshot (optional at create; usually from trip_details sync)",
    )
    flight_segment_departure_dates: list[str] | None = Field(
        None,
        description="Per-segment departure dates YYYY-MM-DD (UTC); from trip_details sync",
    )
    ticket_status_history: list[TicketStatusSnapshotResponse] | None = Field(
        None,
        description="Chronological history of ticket status snapshots from trip details",
    )

    # Hotel reference number - referenceNum from hotel book API response; used for booking details API
    hotel_reference_number: str | None = Field(
        None,
        description="Reference number from hotel booking API response; required for get_booking_details",
    )

    hotel_image_url: str | None = Field(
        None,
        description="Property thumbnail URL; HOTEL events only",
    )
    hotel_name: str | None = Field(
        None,
        description="Hotel name snapshot; HOTEL events only",
    )
    hotel_city: str | None = Field(
        None,
        description="City snapshot; HOTEL events only",
    )
    hotel_address: str | None = Field(
        None,
        description="Property address snapshot; HOTEL events only",
    )
    hotel_latitude: float | None = Field(
        None,
        description="Property latitude (WGS84); HOTEL events only",
    )
    hotel_longitude: float | None = Field(
        None,
        description="Property longitude (WGS84); HOTEL events only",
    )
    hotel_check_in_date: str | None = Field(
        None,
        description="Check-in YYYY-MM-DD; HOTEL events only",
    )
    hotel_check_out_date: str | None = Field(
        None,
        description="Check-out YYYY-MM-DD; HOTEL events only",
    )
    hotel_nights: int | None = Field(
        None,
        description="Stay length in nights when known; HOTEL events only",
    )
    saved_itinerary_id: str | None = Field(
        None,
        description="Saved itinerary id when this booking is linked to an itinerary",
    )
    parent_voya_booking_reference: str | None = Field(
        None,
        description="Multicity group id when this booking is one leg of a multi-city trip",
    )
    multistay_leg_index: int | None = Field(
        None,
        description="Zero-based leg index for multi-stay when this row is one leg of a group",
    )

    voucher_redemption_id: str | None = Field(
        None,
        description="Discounts reservation id when a voucher was applied to this booking",
    )
    voucher_discount_amount: int | None = Field(
        None,
        description="Voucher discount in USD cents when a voucher was applied",
    )


class BookingEventListResponse(StrictModel):
    """Response with list of booking events."""

    events: list[BookingEventResponse]
    total: int
    limit: int
    offset: int = 0

    # Optional filters applied
    filters: dict[str, Any] | None = None


class BookingEventQueryRequest(StrictModel):
    """Request to query booking events."""

    # Date range
    date_from: datetime | None = None
    date_to: datetime | None = None

    # Filters
    event_type: Literal["FLIGHT", "HOTEL"] | None = None
    action: Literal["BOOKED", "CANCELLED", "PENDING"] | None = None

    # Pagination
    limit: int = Field(default=50, ge=1, le=200, description="Max events to return")
    offset: int = Field(default=0, ge=0, description="Skip first N events")

    # Sorting
    sort_by: Literal["timestamp"] = "timestamp"
    sort_order: Literal["asc", "desc"] = "desc"


class MulticityLegBookingSummaryItem(StrictModel):
    """One flight leg in a multi-city group (Mongo booking_events snapshot)."""

    voya_booking_reference: str = Field(..., description="VOYA reference for this leg")
    external_booking_reference: str | None = Field(
        None, description="Supplier UniqueID when known"
    )
    ticket_status: str | None = Field(
        None, description="Latest ticket status from trip-details sync"
    )
    departure_airport_iata: str | None = Field(
        None, description="Departure airport IATA when stored on the event"
    )
    flight_trip_type: Literal["one_way", "round_trip", "multi_city"] | None = Field(
        None,
        description="Trip type when stored on the event",
    )
    route_legs: list[RouteLeg] | None = Field(
        None,
        description="Structured route legs when stored on the event",
    )


class MulticityBookingGroupResponse(StrictModel):
    """All legs sharing the same multicity parent group id (or a single non-group booking)."""

    parent_voya_booking_reference: str | None = Field(
        None,
        description="Shared group id (e.g. VOYA-MC-…) when this booking is part of multi-city; null for ordinary trips",
    )
    legs: list[MulticityLegBookingSummaryItem] = Field(
        ...,
        description="Leg bookings: one entry for non-multicity; N entries when parent is set",
    )
