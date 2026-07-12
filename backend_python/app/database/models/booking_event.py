"""Booking Event model - Simplified database model for MongoDB.

This model represents booking actions (BOOKED/CANCELLED) in a user's journey.
All flight details are fetched on-demand from FlightLogic API using the booking reference.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.database.flight_route import FlightTripTypeLiteral, RouteLeg
from app.database.types import PyObjectId
from app.shared.flight_leg_summary import FlightLegSummary


class TicketStatusSnapshot(BaseModel):
    """Embedded snapshot of ticket status from a trip-details fetch."""

    status: str = Field(..., description="Ticket status returned by trip details")
    time: datetime = Field(
        ...,
        description="UTC time when trip details was successfully fetched",
    )


class BookingEventModel(BaseModel):
    """Simplified database model for booking events.

    Only stores essential information:
    - voya_booking_reference: VOYA internal booking reference (user-facing)
    - external_booking_reference: FlightLogic UniqueID (for API operations)
    - action: BOOKED or CANCELLED
    - timestamp: When the action occurred
    - user_id: Who performed the action

    All other details (flight info, dates, etc.) are fetched on-demand
    from FlightLogic API using the booking reference.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    # MongoDB _id field
    id: PyObjectId | None = Field(default=None, alias="_id")

    # Core fields (all required)
    user_id: PyObjectId = Field(..., description="User who owns this booking")

    # Optional link to a saved AI itinerary (validated at booking time)
    saved_itinerary_id: PyObjectId | None = Field(
        default=None,
        description="Saved itinerary this booking is associated with, when applicable",
    )

    # Booking references
    voya_booking_reference: str | None = Field(
        default=None,
        description="VOYA internal booking reference (format: VOYA-XXXXXXXXXX)",
    )
    external_booking_reference: str = Field(
        ...,
        description="FlightLogic UniqueID for API operations; use TEMP-REF for LCC until booking API succeeds",
    )

    # Airline PNR information (optional - may not be available immediately after booking)
    airline_pnr_code: str | None = Field(
        default=None, description="Airline PNR code (6-character code from airline)"
    )
    airline_pnr_airline_code: str | None = Field(
        default=None, description="IATA code of airline that issued the PNR"
    )
    airline_pnr_airline_name: str | None = Field(
        default=None, description="Name of airline that issued the PNR"
    )
    airline_pnr_status: str | None = Field(
        default=None,
        description="Status of the airline PNR (e.g., 'Confirmed', 'Cancelled')",
    )
    # PNR list from trip details API (one per segment; can differ per leg)
    pnr: list[str] | None = Field(
        default=None,
        description="Airline PNR codes from trip details (array; may vary per segment)",
    )
    ticket_status: str | None = Field(
        default=None,
        description="Latest ticket status synchronized from trip details",
    )
    ticket_status_history: list[TicketStatusSnapshot] | None = Field(
        default=None,
        description="Chronological history of ticket status snapshots from trip details",
    )
    e_ticket_numbers: list[str] | None = Field(
        default=None,
        description="Passenger e-ticket numbers synchronized from trip details",
    )

    action: Literal["BOOKED", "CANCELLED", "PENDING"] = Field(
        ..., description="Action performed; PENDING = GDS awaiting FlightLogic booking"
    )
    timestamp: datetime = Field(..., description="When the action occurred")

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

    # Event type: FLIGHT or HOTEL
    event_type: Literal["FLIGHT", "HOTEL"] = Field(
        default="FLIGHT", description="Type of booking"
    )

    # Flight carrier type: GDS (Global Distribution System) or LCC (Low Cost Carrier / WebFare)
    carrier_type: Literal["GDS", "LCC"] | None = Field(
        default=None,
        description="GDS or LCC (WebFare) for flight bookings; None for hotel or legacy events",
    )

    # Ticket time limit (UTC) - stored for validation before payment processing
    ticket_time_limit: datetime | None = Field(
        default=None,
        description="Ticket time limit in UTC (converted from departure city local time)",
    )

    # Departure airport IATA code - legacy TTL/Slack; mirrors first hop of route_legs[0] when set
    departure_airport_iata: str | None = Field(
        default=None,
        description="IATA code of departure airport (e.g., 'JFK', 'LHR') for timezone conversion",
    )
    flight_trip_type: FlightTripTypeLiteral | None = Field(
        default=None,
        description="one_way | round_trip | multi_city — aligned with persisted route snapshot",
    )
    route_legs: list[RouteLeg] | None = Field(
        default=None,
        description="Structured legs with per-segment IATA hops for list/detail UIs",
    )
    primary_marketing_airline_name: str | None = Field(
        default=None,
        description="Marketing carrier display name for list cards (independent of PNR issuer name)",
    )

    # Flight itinerary snapshot (FLIGHT events); updated on trip_details sync
    flight_leg_summaries: list[FlightLegSummary] | None = Field(
        default=None,
        description="Ordered leg summaries (connections collapsed); from FlightLogic trip_details",
    )
    flight_segment_departure_dates: list[str] | None = Field(
        default=None,
        description="UTC calendar departure date per segment (YYYY-MM-DD), trip_details order",
    )

    # Payment intent ID - stored when payment intent is created (for reuse and tracking)
    payment_intent_id: str | None = Field(
        default=None,
        description="Stripe payment intent ID (pi_xxx) - stored when payment intent is created",
    )

    # FlightLogic booking API payload - stored for admin retry (LCC); not exposed in list/detail
    payload: dict | None = Field(
        default=None,
        description="Exact JSON body sent to FlightLogic booking endpoint; used for LCC retry only",
    )

    # Hotel reference number - referenceNum from hotel book API response; used for booking details API
    hotel_reference_number: str | None = Field(
        default=None,
        description="Reference number from hotel booking API response; required for get_booking_details",
    )

    # Hotel list / profile (HOTEL events only; optional on legacy rows)
    hotel_image_url: str | None = Field(
        default=None,
        description="Property thumbnail URL at book time (e.g. imgproxy); HOTEL events only",
    )
    hotel_name: str | None = Field(
        default=None,
        description="Hotel display name snapshot at book time; HOTEL events only",
    )
    hotel_city: str | None = Field(
        default=None,
        description="City snapshot at book time; HOTEL events only",
    )
    hotel_address: str | None = Field(
        default=None,
        description="Street/property address snapshot at book time; HOTEL events only",
    )
    hotel_latitude: float | None = Field(
        default=None,
        description="Property latitude at book time (WGS84); HOTEL events only",
    )
    hotel_longitude: float | None = Field(
        default=None,
        description="Property longitude at book time (WGS84); HOTEL events only",
    )

    # HOTEL stay window (YYYY-MM-DD); synced from book response / get_booking_details
    hotel_check_in_date: str | None = Field(
        default=None,
        description="Check-in date (property-local); HOTEL events only",
    )
    hotel_check_out_date: str | None = Field(
        default=None,
        description="Check-out date (property-local); HOTEL events only",
    )
    hotel_nights: int | None = Field(
        default=None,
        description="Length of stay in nights when known; HOTEL events only",
    )

    # Date booked (UTC): LCC/GDS = when flight booking API succeeds; Hotel = when hotel booking API succeeds
    date_booked: datetime | None = Field(
        default=None,
        description="When the booking was confirmed by the supplier (UTC)",
    )
    # Date paid (UTC): when payment succeeds for flights or hotels
    date_paid: datetime | None = Field(
        default=None,
        description="When payment was completed successfully (UTC)",
    )
    # Date tickets issued (UTC): LCC = flight booking API success; GDS = ticket order API success; Hotel = hotel booking API success
    date_tickets_issued: datetime | None = Field(
        default=None,
        description="When tickets/confirmation was issued (UTC)",
    )
    # Total original amount of flight or hotel (e.g. USD)
    amount: float | None = Field(
        default=None,
        description="Total original amount of the booking (flight or hotel)",
    )

    # Multi-stay/multicity: same synthetic group id on each leg booking event (e.g. VOYA-MC-…)
    parent_voya_booking_reference: str | None = Field(
        default=None,
        description="Optional group reference linking multi-stay leg bookings (same value on each leg)",
    )
    multistay_leg_index: int | None = Field(
        default=None,
        description="Zero-based itinerary leg index for multi-stay/multicity legs (stable sort vs lexicographic VOYA ref)",
    )
    # True when the relevant confirmation email was sent (LCC=booking confirmation, GDS=tickets issued, Hotel=booking confirmation); None when not set (legacy/unknown)
    confirmation_email_sent: bool | None = Field(
        default=None,
        description="True if the booking/ticket confirmation email was sent successfully; None when unknown",
    )

    # GDS ticket time limit Slack alert dedupe (hourly job)
    ticket_time_limit_warning_sent_at: datetime | None = Field(
        default=None,
        description="UTC time when a GDS ticket time limit Slack warning was last sent",
    )
    ticket_time_limit_warning_for: datetime | None = Field(
        default=None,
        description="ticket_time_limit value for which the last warning was sent (dedupe per deadline)",
    )
    ticket_time_limit_warning_lease_id: str | None = Field(
        default=None,
        description="Short-lived lease id while the hourly job sends Slack (prevents duplicate alerts if runs overlap)",
    )
    ticket_time_limit_warning_lease_until: datetime | None = Field(
        default=None,
        description="UTC: lease expiry; after this another run may claim the row if Slack did not complete",
    )

    # G2A / manual discount voucher (reserved at apply; redeemed on payment webhook)
    voucher_redemption_id: str | None = Field(
        default=None,
        description="MongoDB ObjectId string of discounts row (reservation id from /vouchers/apply)",
    )
    voucher_discount_amount: int | None = Field(
        default=None,
        description="Voucher face value applied to this booking in USD cents",
    )
