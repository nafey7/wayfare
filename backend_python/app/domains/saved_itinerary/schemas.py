"""Saved itinerary schemas."""

import json
from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.database.flight_route import RouteLeg

# POST /api/itineraries — guard against oversized payloads (MongoDB + serialization).
_MAX_STRUCTURED_ITINERARY_JSON_BYTES = 512 * 1024
_MAX_TRIP_META_JSON_BYTES = 128 * 1024
_MAX_JSON_NESTING_DEPTH = 32


def _json_utf8_byte_length(obj: Any) -> int:
    return len(
        json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"),
    )


def _max_json_nesting_depth(obj: Any, depth: int = 0) -> int:
    if isinstance(obj, dict):
        if not obj:
            return depth
        return max(_max_json_nesting_depth(v, depth + 1) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return depth
        return max(_max_json_nesting_depth(v, depth + 1) for v in obj)
    return depth


class LinkedBookingEventSummary(BaseModel):
    """Minimal row for itinerary linked-bookings UI (from booking_events)."""

    voya_booking_reference: str = Field(
        ...,
        description="VOYA booking reference shown to the user",
    )
    event_type: Literal["FLIGHT", "HOTEL"] = Field(
        ...,
        description="Flight or hotel booking",
    )
    timestamp: datetime = Field(
        ...,
        description="When the booking event was recorded (UTC)",
    )
    amount: float | None = Field(
        default=None,
        description="Total amount when stored on the event",
    )
    ticket_status: str | None = Field(
        default=None,
        description="Latest ticket / confirmation status when available",
    )
    airline_pnr_code: str | None = Field(
        default=None,
        description="Airline PNR (flights)",
    )
    airline_pnr_airline_name: str | None = Field(
        default=None,
        description="Issuing airline name (flights)",
    )
    primary_marketing_airline_name: str | None = Field(
        default=None,
        description="Marketing carrier display name when stored (list cards; may differ from PNR issuer)",
    )
    flight_trip_type: Literal["one_way", "round_trip", "multi_city"] | None = Field(
        default=None,
        description="Trip type when stored on the flight booking event",
    )
    route_legs: list[RouteLeg] | None = Field(
        default=None,
        description="Structured route snapshot (flights)",
    )
    departure_airport_iata: str | None = Field(
        default=None,
        description="First-hop departure IATA (flights; legacy TTL field)",
    )
    hotel_reference_number: str | None = Field(
        default=None,
        description="Supplier reference (hotels)",
    )
    date_booked: datetime | None = Field(
        default=None,
        description="When the booking was confirmed (UTC), when stored",
    )


class LinkedBookings(BaseModel):
    """VOYA booking references linked to this saved itinerary (from booking_events)."""

    flight_voya_references: list[str] = Field(
        default_factory=list,
        description="Up to 5 most recent flight booking refs for this itinerary",
    )
    hotel_voya_references: list[str] = Field(
        default_factory=list,
        description="Up to 5 most recent hotel booking refs for this itinerary",
    )
    flight_events: list[LinkedBookingEventSummary] = Field(
        default_factory=list,
        description="Display fields aligned in order with flight_voya_references",
    )
    hotel_events: list[LinkedBookingEventSummary] = Field(
        default_factory=list,
        description="Display fields aligned in order with hotel_voya_references",
    )


class SavedItineraryCreate(BaseModel):
    """Schema for creating a saved itinerary."""

    structured_itinerary: dict[str, Any] = Field(
        ...,
        description="Full itinerary payload (itineraryItems, budgetSnapshot, localExperiences, etc.)",
    )
    trip_meta: dict[str, Any] | None = Field(
        None,
        description="Trip metadata (origin, destination, dates, etc.)",
    )

    @model_validator(mode="after")
    def validate_payload_size_and_depth(self) -> Self:
        if _max_json_nesting_depth(self.structured_itinerary) > _MAX_JSON_NESTING_DEPTH:
            raise ValueError(
                f"structured_itinerary exceeds maximum nesting depth ({_MAX_JSON_NESTING_DEPTH})",
            )
        if (
            _json_utf8_byte_length(self.structured_itinerary)
            > _MAX_STRUCTURED_ITINERARY_JSON_BYTES
        ):
            raise ValueError(
                f"structured_itinerary JSON size exceeds {_MAX_STRUCTURED_ITINERARY_JSON_BYTES} bytes",
            )
        if self.trip_meta is not None:
            if _max_json_nesting_depth(self.trip_meta) > _MAX_JSON_NESTING_DEPTH:
                raise ValueError(
                    f"trip_meta exceeds maximum nesting depth ({_MAX_JSON_NESTING_DEPTH})",
                )
            if _json_utf8_byte_length(self.trip_meta) > _MAX_TRIP_META_JSON_BYTES:
                raise ValueError(
                    f"trip_meta JSON size exceeds {_MAX_TRIP_META_JSON_BYTES} bytes",
                )
        return self


class SavedItineraryResponse(BaseModel):
    """Response schema for a saved itinerary."""

    id: str
    structured_itinerary: dict[str, Any]
    trip_meta: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime = Field(
        ...,
        description="Last time the itinerary document was written (create or upsert)",
    )
    linked_bookings: LinkedBookings = Field(
        default_factory=LinkedBookings,
        description="Flight/hotel VOYA refs associated via successful bookings",
    )
