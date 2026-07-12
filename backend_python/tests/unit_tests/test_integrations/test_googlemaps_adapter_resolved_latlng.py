"""Unit tests for resolved lat/lng fields on Route returned by GoogleMapsSchemaAdapter."""

from integrations.googlemaps.adapter import GoogleMapsSchemaAdapter
from integrations.googlemaps.dto import (
    LatLngDTO,
    LegDTO,
    LocationLatLngNestedDTO,
    RouteDTO,
    TransitRouteResponseDTO,
)


def _make_latlng_nested(lat: float, lng: float) -> LocationLatLngNestedDTO:
    return LocationLatLngNestedDTO(latLng=LatLngDTO(latitude=lat, longitude=lng))


def _make_route_dto(
    *,
    legs: list[LegDTO] | None = None,
    encoded_polyline: str | None = None,
) -> RouteDTO:
    from integrations.googlemaps.dto import PolylineDTO

    polyline = (
        PolylineDTO(encodedPolyline=encoded_polyline) if encoded_polyline else None
    )
    return RouteDTO(legs=legs, polyline=polyline)


def _make_leg(
    start_lat: float | None = None,
    start_lng: float | None = None,
    end_lat: float | None = None,
    end_lng: float | None = None,
) -> LegDTO:
    start = (
        _make_latlng_nested(start_lat, start_lng)
        if start_lat is not None and start_lng is not None
        else None
    )
    end = (
        _make_latlng_nested(end_lat, end_lng)
        if end_lat is not None and end_lng is not None
        else None
    )
    return LegDTO(steps=[], startLocation=start, endLocation=end)


class TestAdapterResolvedLatLng:
    def setup_method(self) -> None:
        self.adapter = GoogleMapsSchemaAdapter()

    def _convert(self, route_dto: RouteDTO):
        dto_response = TransitRouteResponseDTO(routes=[route_dto])
        response = self.adapter.route_response_from_dto(dto_response)
        assert response.routes
        return response.routes[0]

    def test_leg_locations_used_when_present(self) -> None:
        legs = [
            _make_leg(31.5497, 74.3436, 31.5204, 74.3587),
            _make_leg(31.5204, 74.3587, 31.5016, 74.4036),
        ]
        route = self._convert(_make_route_dto(legs=legs))

        assert route.origin_lat_lng is not None
        assert abs(route.origin_lat_lng.latitude - 31.5497) < 1e-4
        assert abs(route.origin_lat_lng.longitude - 74.3436) < 1e-4

        assert route.destination_lat_lng is not None
        assert abs(route.destination_lat_lng.latitude - 31.5016) < 1e-4
        assert abs(route.destination_lat_lng.longitude - 74.4036) < 1e-4

    def test_polyline_fallback_when_no_leg_locations(self) -> None:
        # Google canonical polyline: (38.5,-120.2)…(43.252,-126.453)
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        legs = [_make_leg()]  # no start/end coords on leg
        route = self._convert(_make_route_dto(legs=legs, encoded_polyline=encoded))

        assert route.origin_lat_lng is not None
        assert abs(route.origin_lat_lng.latitude - 38.5) < 1e-4
        assert abs(route.origin_lat_lng.longitude - (-120.2)) < 1e-4

        assert route.destination_lat_lng is not None
        assert abs(route.destination_lat_lng.latitude - 43.252) < 1e-4
        assert abs(route.destination_lat_lng.longitude - (-126.453)) < 1e-4

    def test_polyline_fallback_when_no_legs_at_all(self) -> None:
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        route = self._convert(_make_route_dto(legs=None, encoded_polyline=encoded))

        assert route.origin_lat_lng is not None
        assert route.destination_lat_lng is not None

    def test_none_when_no_legs_and_no_polyline(self) -> None:
        route = self._convert(_make_route_dto())
        assert route.origin_lat_lng is None
        assert route.destination_lat_lng is None

    def test_leg_location_takes_precedence_over_polyline(self) -> None:
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        # Leg locations differ from polyline endpoints
        legs = [_make_leg(10.0, 20.0, 11.0, 21.0)]
        route = self._convert(_make_route_dto(legs=legs, encoded_polyline=encoded))

        # Should use leg values, not polyline
        assert route.origin_lat_lng is not None
        assert abs(route.origin_lat_lng.latitude - 10.0) < 1e-4
        assert route.destination_lat_lng is not None
        assert abs(route.destination_lat_lng.latitude - 11.0) < 1e-4

    def test_partial_fallback_origin_from_leg_destination_from_polyline(self) -> None:
        """Leg has start_location but no end_location → destination falls back to polyline."""
        # Polyline: (38.5, -120.2) … (43.252, -126.453)
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        legs = [_make_leg(10.0, 20.0)]  # start set, end omitted
        route = self._convert(_make_route_dto(legs=legs, encoded_polyline=encoded))

        # Origin comes from leg data
        assert route.origin_lat_lng is not None
        assert abs(route.origin_lat_lng.latitude - 10.0) < 1e-4
        assert abs(route.origin_lat_lng.longitude - 20.0) < 1e-4

        # Destination falls back to last point of polyline
        assert route.destination_lat_lng is not None
        assert abs(route.destination_lat_lng.latitude - 43.252) < 1e-4
        assert abs(route.destination_lat_lng.longitude - (-126.453)) < 1e-4

    def test_partial_fallback_destination_from_leg_origin_from_polyline(self) -> None:
        """Leg has end_location but no start_location → origin falls back to polyline."""
        # Polyline: (38.5, -120.2) … (43.252, -126.453)
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        legs = [_make_leg(end_lat=11.0, end_lng=21.0)]  # end set, start omitted
        route = self._convert(_make_route_dto(legs=legs, encoded_polyline=encoded))

        # Origin falls back to first point of polyline
        assert route.origin_lat_lng is not None
        assert abs(route.origin_lat_lng.latitude - 38.5) < 1e-4
        assert abs(route.origin_lat_lng.longitude - (-120.2)) < 1e-4

        # Destination comes from leg data
        assert route.destination_lat_lng is not None
        assert abs(route.destination_lat_lng.latitude - 11.0) < 1e-4
        assert abs(route.destination_lat_lng.longitude - 21.0) < 1e-4
