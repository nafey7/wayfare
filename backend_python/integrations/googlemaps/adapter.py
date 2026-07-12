"""Adapter for converting between Google Maps Routes API DTOs and domain schemas.

This module handles the transformation between Google Maps Routes API DTOs
and the application's transit domain schemas.

IMPORTANT: No data is faked or lost during conversion. If data is not available,
the field is set to None (for Optional fields) or an appropriate error is raised.
"""

from __future__ import annotations

import logging

from app.domains.transit.schemas import (
    LatLng,
    Leg,
    LegLocalizedValues,
    LocalizedTime,
    LocalizedTimeValue,
    LocalizedValues,
    NavigationInstruction,
    Route,
    RouteLocalizedValues,
    Step,
    StepLocalizedValues,
    StopDetails,
    StopLocation,
    TransitAgency,
    TransitDetails,
    TransitLine,
    TransitRouteRequest,
    TransitRouteResponse,
    TransitVehicle,
)

from .dto import (
    LegDTO,
    LocationDTO,
    LocationLatLngDTO,
    LocationNestedDTO,
    RouteDTO,
    TransitDetailsDTO,
    TransitPreferencesDTO,
    TransitRouteRequestDTO,
    TransitRouteResponseDTO,
)
from .polyline_decode import first_last_points

logger = logging.getLogger(__name__)


class GoogleMapsSchemaAdapter:
    """Adapter for converting between Google Maps DTOs and domain schemas."""

    # ===================================================================
    # REQUEST CONVERSIONS (Domain → DTO)
    # ===================================================================

    def route_request_to_dto(
        self, request: TransitRouteRequest
    ) -> TransitRouteRequestDTO:
        """Convert domain TransitRouteRequest to Google Maps DTO.

        Args:
            request: Domain model transit route request

        Returns:
            Google Maps API DTO with camelCase fields
        """
        # Convert origin
        origin_dto = LocationDTO(
            address=request.origin.address,
            location=(
                LocationNestedDTO(
                    lat_lng=LocationLatLngDTO(
                        latitude=request.origin.lat_lng.latitude,
                        longitude=request.origin.lat_lng.longitude,
                    )
                )
                if request.origin.lat_lng
                else None
            ),
        )

        # Convert destination
        destination_dto = LocationDTO(
            address=request.destination.address,
            location=(
                LocationNestedDTO(
                    lat_lng=LocationLatLngDTO(
                        latitude=request.destination.lat_lng.latitude,
                        longitude=request.destination.lat_lng.longitude,
                    )
                )
                if request.destination.lat_lng
                else None
            ),
        )

        # Transit preferences only apply when travel mode is TRANSIT
        transit_preferences_dto = None
        if request.travel_mode == "TRANSIT" and request.transit_preferences:
            transit_preferences_dto = TransitPreferencesDTO(
                routing_preference=request.transit_preferences.routing_preference,
                allowed_travel_modes=request.transit_preferences.allowed_travel_modes,
            )

        return TransitRouteRequestDTO(
            origin=origin_dto,
            destination=destination_dto,
            travel_mode=request.travel_mode or "TRANSIT",
            compute_alternative_routes=request.compute_alternative_routes,
            transit_preferences=transit_preferences_dto,
        )

    # ===================================================================
    # RESPONSE CONVERSIONS (DTO → Domain)
    # ===================================================================

    def route_response_from_dto(
        self, dto: TransitRouteResponseDTO
    ) -> TransitRouteResponse:
        """Convert Google Maps route response DTO to domain model.

        Args:
            dto: Google Maps API response DTO

        Returns:
            Domain model with transit route information
        """
        routes = []
        for route_dto in dto.routes:
            legs = []
            legs_to_process = route_dto.legs or []
            for leg_dto in legs_to_process:
                steps = []
                for step_dto in leg_dto.steps:
                    transit_details = None
                    if step_dto.transit_details:
                        transit_details = self._transit_details_from_dto(
                            step_dto.transit_details
                        )

                    # Map driving/walking step fields
                    step_localized = None
                    if step_dto.localized_values:
                        step_localized = StepLocalizedValues(
                            distance_text=step_dto.localized_values.distance.get("text")
                            if step_dto.localized_values.distance
                            else None,
                            duration_text=(
                                step_dto.localized_values.static_duration.get("text")
                                if step_dto.localized_values.static_duration
                                else None
                            ),
                        )

                    nav_instruction = None
                    if step_dto.navigation_instruction:
                        nav_instruction = NavigationInstruction(
                            maneuver=step_dto.navigation_instruction.maneuver,
                            instructions=step_dto.navigation_instruction.instructions,
                        )

                    polyline_str = None
                    if step_dto.polyline:
                        polyline_str = step_dto.polyline.encoded_polyline

                    steps.append(
                        Step(
                            transit_details=transit_details,
                            distance_meters=step_dto.distance_meters,
                            polyline=polyline_str,
                            navigation_instruction=nav_instruction,
                            localized_values=step_localized,
                            travel_mode=step_dto.travel_mode,
                        )
                    )

                leg_localized = self._leg_localized_from_dto(leg_dto)
                leg_polyline = (
                    leg_dto.polyline.encoded_polyline if leg_dto.polyline else None
                )
                legs.append(
                    Leg(
                        steps=steps,
                        distance_meters=leg_dto.distance_meters,
                        polyline=leg_polyline,
                        localized_values=leg_localized,
                    )
                )

            # When API omits legs (e.g. simple DRIVE routes), synthesize one from route-level data
            if not legs and (route_dto.distance_meters or route_dto.polyline):
                route_polyline_str = (
                    route_dto.polyline.encoded_polyline if route_dto.polyline else None
                )
                leg_localized = self._route_localized_from_dto(route_dto)
                if leg_localized:
                    leg_localized = LegLocalizedValues(
                        distance_text=leg_localized.distance_text,
                        duration_text=leg_localized.duration_text,
                    )
                legs = [
                    Leg(
                        steps=[
                            Step(
                                polyline=route_polyline_str,
                                distance_meters=route_dto.distance_meters,
                            )
                        ],
                        distance_meters=route_dto.distance_meters,
                        polyline=route_polyline_str,
                        localized_values=leg_localized,
                    )
                ]

            route_localized = self._route_localized_from_dto(route_dto)
            route_polyline = (
                route_dto.polyline.encoded_polyline if route_dto.polyline else None
            )

            # Resolve origin/destination coordinates from leg locations
            origin_lat_lng = None
            destination_lat_lng = None
            legs_raw = route_dto.legs or []
            if legs_raw:
                first_leg = legs_raw[0]
                last_leg = legs_raw[-1]
                if first_leg.start_location and first_leg.start_location.lat_lng:
                    ll = first_leg.start_location.lat_lng
                    origin_lat_lng = LatLng(
                        latitude=ll.latitude, longitude=ll.longitude
                    )
                if last_leg.end_location and last_leg.end_location.lat_lng:
                    ll = last_leg.end_location.lat_lng
                    destination_lat_lng = LatLng(
                        latitude=ll.latitude, longitude=ll.longitude
                    )

            # Fallback: decode route polyline to get first/last points
            if (
                origin_lat_lng is None or destination_lat_lng is None
            ) and route_polyline:
                first_pt, last_pt = first_last_points(route_polyline)
                if origin_lat_lng is None and first_pt is not None:
                    origin_lat_lng = LatLng(latitude=first_pt[0], longitude=first_pt[1])
                if destination_lat_lng is None and last_pt is not None:
                    destination_lat_lng = LatLng(
                        latitude=last_pt[0], longitude=last_pt[1]
                    )

            routes.append(
                Route(
                    legs=legs,
                    distance_meters=route_dto.distance_meters,
                    polyline=route_polyline,
                    description=route_dto.description,
                    warnings=route_dto.warnings,
                    localized_values=route_localized,
                    origin_lat_lng=origin_lat_lng,
                    destination_lat_lng=destination_lat_lng,
                )
            )

        return TransitRouteResponse(routes=routes)

    def _leg_localized_from_dto(self, leg_dto: LegDTO) -> LegLocalizedValues | None:
        """Extract leg localized values from DTO."""
        if not leg_dto.localized_values:
            return None
        lv = leg_dto.localized_values
        return LegLocalizedValues(
            distance_text=lv.distance.get("text") if lv.distance else None,
            duration_text=(
                (lv.duration or lv.static_duration or {}).get("text")
                if (lv.duration or lv.static_duration)
                else None
            ),
        )

    def _route_localized_from_dto(
        self, route_dto: RouteDTO
    ) -> RouteLocalizedValues | None:
        """Extract route localized values from DTO."""
        if not route_dto.localized_values:
            return None
        lv = route_dto.localized_values
        return RouteLocalizedValues(
            distance_text=lv.distance.get("text") if lv.distance else None,
            duration_text=(
                (lv.duration or lv.static_duration or {}).get("text")
                if (lv.duration or lv.static_duration)
                else None
            ),
        )

    def _transit_details_from_dto(self, dto: TransitDetailsDTO) -> TransitDetails:
        """Convert TransitDetailsDTO to domain TransitDetails.

        Args:
            dto: Google Maps API TransitDetails DTO

        Returns:
            Domain TransitDetails model
        """
        # Convert stop details
        stop_details = StopDetails(
            arrival_stop=StopLocation(
                name=dto.stop_details.arrival_stop.name,
                location=LatLng(
                    latitude=dto.stop_details.arrival_stop.location.lat_lng.latitude,
                    longitude=dto.stop_details.arrival_stop.location.lat_lng.longitude,
                ),
            ),
            arrival_time=dto.stop_details.arrival_time,
            departure_stop=StopLocation(
                name=dto.stop_details.departure_stop.name,
                location=LatLng(
                    latitude=dto.stop_details.departure_stop.location.lat_lng.latitude,
                    longitude=dto.stop_details.departure_stop.location.lat_lng.longitude,
                ),
            ),
            departure_time=dto.stop_details.departure_time,
        )

        # Convert localized values
        localized_values = LocalizedValues(
            arrival_time=LocalizedTimeValue(
                time=LocalizedTime(
                    text=dto.localized_values.arrival_time.time.text,
                    time_zone=dto.localized_values.arrival_time.time.time_zone,
                )
            ),
            departure_time=LocalizedTimeValue(
                time=LocalizedTime(
                    text=dto.localized_values.departure_time.time.text,
                    time_zone=dto.localized_values.departure_time.time.time_zone,
                )
            ),
        )

        # Convert transit line
        transit_line = TransitLine(
            agencies=[
                TransitAgency(
                    name=agency.name,
                    phone_number=agency.phone_number,
                    uri=agency.uri,
                )
                for agency in dto.transit_line.agencies
            ],
            name=dto.transit_line.name,
            color=dto.transit_line.color,
            name_short=dto.transit_line.name_short,
            text_color=dto.transit_line.text_color,
            vehicle=TransitVehicle(
                name=dto.transit_line.vehicle.name,
                type=dto.transit_line.vehicle.type,
                icon_uri=dto.transit_line.vehicle.icon_uri,
            ),
        )

        return TransitDetails(
            stop_details=stop_details,
            localized_values=localized_values,
            headsign=dto.headsign,
            transit_line=transit_line,
            stop_count=dto.stop_count,
        )
