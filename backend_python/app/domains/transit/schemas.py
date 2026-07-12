"""Transit routes domain schemas.

Pydantic v2 models for transit route planning using Google Maps Routes API.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator  # noqa: N806

# Google Maps Routes API RouteTravelMode values
RouteTravelMode = Literal[
    "DRIVE",
    "BICYCLE",
    "WALK",
    "TWO_WHEELER",
    "TRANSIT",
]

# =============================================================================
# Request Models
# =============================================================================


class LocationAddress(BaseModel):
    """Location specified by address."""

    address: str = Field(
        ..., description="Address string (e.g., 'Humberto Delgado Airport, Portugal')"
    )


class LocationLatLng(BaseModel):
    """Location specified by coordinates."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")


class Location(BaseModel):
    """Location for origin or destination.

    Can be specified either by address or by lat/lng coordinates.
    """

    address: str | None = Field(None, description="Address string")
    lat_lng: LocationLatLng | None = Field(
        None, alias="latLng", description="Latitude/longitude coordinates"
    )

    @model_validator(mode="after")
    def validate_location(self) -> Location:
        """Ensure either address or lat_lng is provided."""
        if not self.address and not self.lat_lng:
            msg = "Either 'address' or 'latLng' must be provided for Location"
            raise ValueError(msg)
        return self


class TransitPreferences(BaseModel):
    """Transit routing preferences."""

    routing_preference: Literal["LESS_WALKING", "LESS_TRANSFERS"] | None = Field(
        None,
        alias="routingPreference",
        description="Routing preference: LESS_WALKING or LESS_TRANSFERS",
    )
    allowed_travel_modes: (
        list[Literal["BUS", "SUBWAY", "TRAIN", "LIGHT_RAIL", "RAIL"]] | None
    ) = Field(
        None,
        alias="allowedTravelModes",
        description="Allowed transit travel modes",
    )


class TransitRouteRequest(BaseModel):
    """Request for route planning."""

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both field names and aliases
    )

    origin: Location = Field(..., description="Origin location")
    destination: Location = Field(..., description="Destination location")
    travel_mode: RouteTravelMode | None = Field(
        default="TRANSIT",
        alias="travelMode",
        description="Travel mode: DRIVE, BICYCLE, WALK, TWO_WHEELER, or TRANSIT",
    )
    compute_alternative_routes: bool | None = Field(
        default=False,
        alias="computeAlternativeRoutes",
        description="Whether to compute alternative routes",
    )
    transit_preferences: TransitPreferences | None = Field(
        None,
        alias="transitPreferences",
        description="Transit routing preferences",
    )


# =============================================================================
# Response Models
# =============================================================================


class LatLng(BaseModel):
    """Latitude/longitude coordinates."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")


class StopLocation(BaseModel):
    """Transit stop location."""

    name: str = Field(..., description="Stop name")
    location: LatLng = Field(..., description="Stop coordinates")


class StopDetails(BaseModel):
    """Transit stop details with arrival/departure information."""

    arrival_stop: StopLocation = Field(..., description="Arrival stop")
    arrival_time: str = Field(..., description="Arrival time (ISO 8601)")
    departure_stop: StopLocation = Field(..., description="Departure stop")
    departure_time: str = Field(..., description="Departure time (ISO 8601)")


class LocalizedTime(BaseModel):
    """Localized time representation."""

    text: str = Field(..., description="Time as text (e.g., '11:49')")
    time_zone: str | None = Field(None, description="Time zone (e.g., 'Europe/Lisbon')")


class LocalizedTimeValue(BaseModel):
    """Localized time value."""

    time: LocalizedTime = Field(..., description="Time information")


class LocalizedValues(BaseModel):
    """Localized time values for arrival and departure."""

    arrival_time: LocalizedTimeValue = Field(..., description="Arrival time")
    departure_time: LocalizedTimeValue = Field(..., description="Departure time")


class TransitAgency(BaseModel):
    """Transit agency information."""

    name: str = Field(..., description="Agency name")
    phone_number: str | None = Field(None, description="Phone number")
    uri: str | None = Field(None, description="Agency website URI")


class TransitVehicle(BaseModel):
    """Transit vehicle information."""

    name: dict[str, str] = Field(..., description="Vehicle name (localized)")
    type: Literal[
        "BUS",
        "SUBWAY",
        "TRAIN",
        "LIGHT_RAIL",
        "RAIL",
        "COMMUTER_TRAIN",
        "HEAVY_RAIL",
    ] = Field(..., description="Vehicle type")
    icon_uri: str | None = Field(None, description="Vehicle icon URI")


class TransitLine(BaseModel):
    """Transit line information."""

    agencies: list[TransitAgency] = Field(..., description="Transit agencies")
    name: str = Field(..., description="Line name")
    color: str = Field(..., description="Line color (hex)")
    name_short: str = Field(..., description="Short line name")
    text_color: str = Field(..., description="Text color (hex)")
    vehicle: TransitVehicle = Field(..., description="Vehicle information")


class TransitDetails(BaseModel):
    """Transit step details."""

    stop_details: StopDetails = Field(..., description="Stop details")
    localized_values: LocalizedValues = Field(..., description="Localized time values")
    headsign: str = Field(..., description="Direction/headsign")
    transit_line: TransitLine = Field(..., description="Transit line information")
    stop_count: int = Field(..., description="Number of stops")


class NavigationInstruction(BaseModel):
    """Turn-by-turn navigation instruction."""

    maneuver: str | None = Field(None, description="Maneuver type (e.g. TURN_LEFT)")
    instructions: str | None = Field(None, description="Human-readable instruction")


class StepLocalizedValues(BaseModel):
    """Localized distance and duration for a step."""

    distance_text: str | None = Field(None, description="e.g. '1.2 km'")
    duration_text: str | None = Field(None, description="e.g. '5 mins'")


class Step(BaseModel):
    """Route step (walking, driving, transit)."""

    transit_details: TransitDetails | None = Field(
        None,
        description="Transit details (only for transit steps)",
    )
    distance_meters: int | None = Field(
        None,
        description="Step distance in meters",
    )
    polyline: str | None = Field(
        None,
        description="Encoded polyline for map display",
    )
    navigation_instruction: NavigationInstruction | None = Field(
        None,
        description="Turn-by-turn instruction (DRIVE/WALK/BICYCLE)",
    )
    localized_values: StepLocalizedValues | None = Field(
        None,
        description="Localized distance and duration text",
    )
    travel_mode: str | None = Field(
        None,
        description="DRIVE, WALK, BICYCLE, TRANSIT, etc.",
    )


class LegLocalizedValues(BaseModel):
    """Localized distance and duration for a leg."""

    distance_text: str | None = Field(None, description="e.g. '340 km'")
    duration_text: str | None = Field(None, description="e.g. '4 hours 3 mins'")


class Leg(BaseModel):
    """Route leg containing steps."""

    steps: list[Step] = Field(..., description="Route steps")
    distance_meters: int | None = Field(None, description="Leg distance in meters")
    polyline: str | None = Field(None, description="Encoded polyline for entire leg")
    localized_values: LegLocalizedValues | None = Field(
        None,
        description="Localized distance and duration text",
    )


class RouteLocalizedValues(BaseModel):
    """Localized distance and duration for a route."""

    distance_text: str | None = Field(None, description="e.g. '340 km'")
    duration_text: str | None = Field(None, description="e.g. '4 hours 3 mins'")


class Route(BaseModel):
    """Transit or driving route."""

    legs: list[Leg] = Field(..., description="Route legs")
    distance_meters: int | None = Field(None, description="Total distance in meters")
    polyline: str | None = Field(None, description="Encoded polyline for entire route")
    description: str | None = Field(None, description="Route description (e.g. 'M40')")
    warnings: list[str] | None = Field(None, description="Route warnings")
    localized_values: RouteLocalizedValues | None = Field(
        None,
        description="Localized distance and duration text",
    )
    origin_lat_lng: LatLng | None = Field(
        None,
        description="Resolved origin coordinates (first leg start, or polyline first point)",
    )
    destination_lat_lng: LatLng | None = Field(
        None,
        description="Resolved destination coordinates (last leg end, or polyline last point)",
    )


class TransitRouteResponse(BaseModel):
    """Response from transit route planning."""

    routes: list[Route] = Field(..., description="Available routes")
