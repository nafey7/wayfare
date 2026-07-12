"""Google Maps Platform Routes API DTOs.

Data Transfer Objects that match the Google Maps Routes API format exactly.
These DTOs use snake_case field names in Python with camelCase aliases for API serialization.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Request DTOs
# =============================================================================


class LocationLatLngDTO(BaseModel):
    """Location specified by coordinates (API format)."""

    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")


class LocationNestedDTO(BaseModel):
    """Nested location structure for coordinates (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    lat_lng: LocationLatLngDTO = Field(
        ..., alias="latLng", description="Latitude/longitude coordinates"
    )


class LocationDTO(BaseModel):
    """Location for origin or destination (API format).

    Can be specified either by address or by location.latLng coordinates.
    Uses camelCase to match Google Maps API.
    """

    address: str | None = Field(None, description="Address string")
    location: LocationNestedDTO | None = Field(
        None, description="Location with latLng coordinates"
    )


class TransitPreferencesDTO(BaseModel):
    """Transit routing preferences (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    routing_preference: Literal["LESS_WALKING", "LESS_TRANSFERS"] | None = Field(
        None,
        alias="routingPreference",
        description="Routing preference: LESS_WALKING or LESS_TRANSFERS",
    )
    allowed_travel_modes: (
        list[Literal["BUS", "SUBWAY", "TRAIN", "LIGHT_RAIL", "RAIL"]] | None
    ) = Field(
        None, alias="allowedTravelModes", description="Allowed transit travel modes"
    )


# Google Maps Routes API RouteTravelMode values
RouteTravelModeDTO = Literal[
    "DRIVE",
    "BICYCLE",
    "WALK",
    "TWO_WHEELER",
    "TRANSIT",
]


class TransitRouteRequestDTO(BaseModel):
    """Request for route planning (API format).

    Matches Google Maps Routes API request format exactly.
    """

    model_config = ConfigDict(populate_by_name=True)

    origin: LocationDTO = Field(..., description="Origin location")
    destination: LocationDTO = Field(..., description="Destination location")
    travel_mode: RouteTravelModeDTO = Field(
        default="TRANSIT",
        alias="travelMode",
        description="Travel mode: DRIVE, BICYCLE, WALK, TWO_WHEELER, or TRANSIT",
    )
    compute_alternative_routes: bool = Field(
        default=False,
        alias="computeAlternativeRoutes",
        description="Whether to compute alternative routes",
    )
    transit_preferences: TransitPreferencesDTO | None = Field(
        None, alias="transitPreferences", description="Transit routing preferences"
    )


# =============================================================================
# Response DTOs
# =============================================================================


class LatLngDTO(BaseModel):
    """Latitude/longitude coordinates (API format)."""

    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")


class StopLocationNestedDTO(BaseModel):
    """Nested location structure in stop location (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    lat_lng: LatLngDTO = Field(
        ..., alias="latLng", description="Latitude/longitude coordinates"
    )


class StopLocationDTO(BaseModel):
    """Transit stop location (API format)."""

    name: str = Field(..., description="Stop name")
    location: StopLocationNestedDTO = Field(
        ..., description="Stop location with nested latLng"
    )


class StopDetailsDTO(BaseModel):
    """Transit stop details with arrival/departure information (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    arrival_stop: StopLocationDTO = Field(
        ..., alias="arrivalStop", description="Arrival stop"
    )
    arrival_time: str = Field(
        ..., alias="arrivalTime", description="Arrival time (ISO 8601)"
    )
    departure_stop: StopLocationDTO = Field(
        ..., alias="departureStop", description="Departure stop"
    )
    departure_time: str = Field(
        ..., alias="departureTime", description="Departure time (ISO 8601)"
    )


class LocalizedTimeDTO(BaseModel):
    """Localized time representation (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(..., description="Time as text (e.g., '11:49')")
    time_zone: str | None = Field(
        None, alias="timeZone", description="Time zone (e.g., 'Europe/Lisbon')"
    )


class LocalizedTimeValueDTO(BaseModel):
    """Localized time value (API format)."""

    time: LocalizedTimeDTO = Field(..., description="Time information")


class LocalizedValuesDTO(BaseModel):
    """Localized time values for arrival and departure (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    arrival_time: LocalizedTimeValueDTO = Field(
        ..., alias="arrivalTime", description="Arrival time"
    )
    departure_time: LocalizedTimeValueDTO = Field(
        ..., alias="departureTime", description="Departure time"
    )


class TransitAgencyDTO(BaseModel):
    """Transit agency information (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Agency name")
    phone_number: str | None = Field(
        None, alias="phoneNumber", description="Phone number"
    )
    uri: str | None = Field(None, description="Agency website URI")


class TransitVehicleDTO(BaseModel):
    """Transit vehicle information (API format)."""

    model_config = ConfigDict(populate_by_name=True)

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
    icon_uri: str | None = Field(None, alias="iconUri", description="Vehicle icon URI")


class TransitLineDTO(BaseModel):
    """Transit line information (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    agencies: list[TransitAgencyDTO] = Field(..., description="Transit agencies")
    name: str = Field(..., description="Line name")
    color: str = Field(..., description="Line color (hex)")
    name_short: str = Field(..., alias="nameShort", description="Short line name")
    text_color: str = Field(..., alias="textColor", description="Text color (hex)")
    vehicle: TransitVehicleDTO = Field(..., description="Vehicle information")


class TransitDetailsDTO(BaseModel):
    """Transit step details (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    stop_details: StopDetailsDTO = Field(
        ..., alias="stopDetails", description="Stop details"
    )
    localized_values: LocalizedValuesDTO = Field(
        ..., alias="localizedValues", description="Localized time values"
    )
    headsign: str = Field(..., description="Direction/headsign")
    transit_line: TransitLineDTO = Field(
        ..., alias="transitLine", description="Transit line information"
    )
    stop_count: int = Field(..., alias="stopCount", description="Number of stops")


class LocationLatLngNestedDTO(BaseModel):
    """Nested latLng in start/end location (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    lat_lng: LatLngDTO = Field(..., alias="latLng", description="Coordinates")


class PolylineDTO(BaseModel):
    """Encoded polyline for map display (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    encoded_polyline: str = Field(
        ...,
        alias="encodedPolyline",
        description="Encoded polyline string",
    )


class NavigationInstructionDTO(BaseModel):
    """Navigation maneuver and instruction text (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    maneuver: str | None = Field(None, description="Maneuver type (e.g. TURN_LEFT)")
    instructions: str | None = Field(None, description="Human-readable instruction")


class StepLocalizedValuesDTO(BaseModel):
    """Localized distance and duration for a step (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    distance: dict[str, str] | None = Field(
        None,
        description="e.g. {'text': '1.2 km'}",
    )
    static_duration: dict[str, str] | None = Field(
        None,
        alias="staticDuration",
        description="e.g. {'text': '5 mins'}",
    )


class StepDTO(BaseModel):
    """Route step (can be walking, driving, or transit) (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    transit_details: TransitDetailsDTO | None = Field(
        None,
        alias="transitDetails",
        description="Transit details (only for transit steps)",
    )
    distance_meters: int | None = Field(
        None,
        alias="distanceMeters",
        description="Step distance in meters",
    )
    duration: str | None = Field(None, description="Step duration (e.g. '280s')")
    static_duration: str | None = Field(
        None,
        alias="staticDuration",
        description="Step duration (e.g. '280s')",
    )
    polyline: PolylineDTO | None = Field(
        None,
        description="Encoded polyline for this step",
    )
    start_location: LocationLatLngNestedDTO | None = Field(
        None,
        alias="startLocation",
        description="Step start coordinates",
    )
    end_location: LocationLatLngNestedDTO | None = Field(
        None,
        alias="endLocation",
        description="Step end coordinates",
    )
    navigation_instruction: NavigationInstructionDTO | None = Field(
        None,
        alias="navigationInstruction",
        description="Turn-by-turn instruction",
    )
    localized_values: StepLocalizedValuesDTO | None = Field(
        None,
        alias="localizedValues",
        description="Localized distance and duration text",
    )
    travel_mode: str | None = Field(
        None,
        alias="travelMode",
        description="DRIVE, WALK, BICYCLE, TRANSIT, etc.",
    )


class LegLocalizedValuesDTO(BaseModel):
    """Localized distance and duration for a leg (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    distance: dict[str, str] | None = Field(None, description="e.g. {'text': '340 km'}")
    duration: dict[str, str] | None = Field(
        None, description="e.g. {'text': '4 hours 3 mins'}"
    )
    static_duration: dict[str, str] | None = Field(
        None,
        alias="staticDuration",
        description="e.g. {'text': '4 hours 3 mins'}",
    )


class LegDTO(BaseModel):
    """Route leg containing steps (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    steps: list[StepDTO] = Field(default_factory=list, description="Route steps")
    distance_meters: int | None = Field(
        None,
        alias="distanceMeters",
        description="Leg distance in meters",
    )
    duration: str | None = Field(None, description="Leg duration (e.g. '14588s')")
    static_duration: str | None = Field(
        None,
        alias="staticDuration",
        description="Leg duration (e.g. '14588s')",
    )
    polyline: PolylineDTO | None = Field(
        None,
        description="Encoded polyline for entire leg",
    )
    start_location: LocationLatLngNestedDTO | None = Field(
        None,
        alias="startLocation",
        description="Leg start coordinates",
    )
    end_location: LocationLatLngNestedDTO | None = Field(
        None,
        alias="endLocation",
        description="Leg end coordinates",
    )
    localized_values: LegLocalizedValuesDTO | None = Field(
        None,
        alias="localizedValues",
        description="Localized distance and duration text",
    )


class RouteLocalizedValuesDTO(BaseModel):
    """Localized distance and duration for a route (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    distance: dict[str, str] | None = Field(None, description="e.g. {'text': '340 km'}")
    duration: dict[str, str] | None = Field(
        None, description="e.g. {'text': '4 hours 3 mins'}"
    )
    static_duration: dict[str, str] | None = Field(
        None,
        alias="staticDuration",
        description="e.g. {'text': '4 hours 3 mins'}",
    )


class RouteDTO(BaseModel):
    """Transit/driving route (API format)."""

    model_config = ConfigDict(populate_by_name=True)

    legs: list[LegDTO] | None = Field(
        None, description="Route legs (may be absent for simple routes)"
    )
    distance_meters: int | None = Field(
        None,
        alias="distanceMeters",
        description="Total route distance in meters",
    )
    duration: str | None = Field(None, description="Total duration (e.g. '14588s')")
    static_duration: str | None = Field(
        None,
        alias="staticDuration",
        description="Total duration (e.g. '14588s')",
    )
    polyline: PolylineDTO | None = Field(
        None,
        description="Encoded polyline for entire route",
    )
    description: str | None = Field(None, description="Route description (e.g. 'M40')")
    warnings: list[str] | None = Field(None, description="Route warnings")
    localized_values: RouteLocalizedValuesDTO | None = Field(
        None,
        alias="localizedValues",
        description="Localized distance and duration text",
    )


class TransitRouteResponseDTO(BaseModel):
    """Response from transit route planning (API format).

    Matches Google Maps Routes API response format exactly.
    """

    routes: list[RouteDTO] = Field(..., description="Available routes")
