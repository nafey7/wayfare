"""Unit tests for GoogleMapsRoutesClient.resolve_drive_summary coordinate extraction."""

from unittest.mock import AsyncMock, patch

import pytest

from app.domains.transit.schemas import (
    LatLng,
    Leg,
    Route,
    RouteLocalizedValues,
    TransitRouteResponse,
)
from integrations.googlemaps.client import GoogleMapsRoutesClient


def _make_response(
    origin_lat_lng: LatLng | None = None,
    destination_lat_lng: LatLng | None = None,
    duration_text: str | None = "15 mins",
    distance_meters: int | None = 5000,
) -> TransitRouteResponse:
    route = Route(
        legs=[Leg(steps=[], distance_meters=distance_meters)],
        distance_meters=distance_meters,
        localized_values=RouteLocalizedValues(
            duration_text=duration_text, distance_text="5 km"
        ),
        origin_lat_lng=origin_lat_lng,
        destination_lat_lng=destination_lat_lng,
    )
    return TransitRouteResponse(routes=[route])


class TestResolveDriveSummaryCoordinates:
    """Tests for coordinate extraction in resolve_drive_summary."""

    @pytest.mark.asyncio
    async def test_resolve_drive_summary_returns_leg_coordinates(self) -> None:
        """Returns origin_lat_lng and destination_lat_lng when route has both coords."""
        origin = LatLng(latitude=48.8584, longitude=2.2945)
        dest = LatLng(latitude=48.8606, longitude=2.3376)
        response = _make_response(origin_lat_lng=origin, destination_lat_lng=dest)

        client = GoogleMapsRoutesClient(api_key="test-key")
        with patch.object(client, "compute_routes", new_callable=AsyncMock) as mock:
            mock.return_value = response
            result = await client.resolve_drive_summary(
                "Eiffel Tower Paris", "Louvre Museum Paris"
            )

        assert result is not None
        assert result["origin_lat_lng"] == {"lat": 48.8584, "lng": 2.2945}
        assert result["destination_lat_lng"] == {"lat": 48.8606, "lng": 2.3376}

    @pytest.mark.asyncio
    async def test_resolve_drive_summary_no_coords_returns_none(self) -> None:
        """Returns None for both coord keys when route has no geocoded coordinates."""
        response = _make_response(origin_lat_lng=None, destination_lat_lng=None)

        client = GoogleMapsRoutesClient(api_key="test-key")
        with patch.object(client, "compute_routes", new_callable=AsyncMock) as mock:
            mock.return_value = response
            result = await client.resolve_drive_summary("A", "B")

        assert result is not None
        assert result["origin_lat_lng"] is None
        assert result["destination_lat_lng"] is None

    @pytest.mark.asyncio
    async def test_resolve_drive_summary_empty_routes_returns_none(self) -> None:
        """Returns None when the API response contains no routes."""
        empty_response = TransitRouteResponse(routes=[])

        client = GoogleMapsRoutesClient(api_key="test-key")
        with patch.object(client, "compute_routes", new_callable=AsyncMock) as mock:
            mock.return_value = empty_response
            result = await client.resolve_drive_summary("A", "B")

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_drive_summary_missing_destination_coords_returns_none(
        self,
    ) -> None:
        """Returns None for destination when only origin coordinate is present."""
        origin = LatLng(latitude=48.8584, longitude=2.2945)
        response = _make_response(origin_lat_lng=origin, destination_lat_lng=None)

        client = GoogleMapsRoutesClient(api_key="test-key")
        with patch.object(client, "compute_routes", new_callable=AsyncMock) as mock:
            mock.return_value = response
            result = await client.resolve_drive_summary("A", "B")

        assert result is not None
        assert result["origin_lat_lng"] == {"lat": 48.8584, "lng": 2.2945}
        assert result["destination_lat_lng"] is None
