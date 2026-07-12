"""Unit tests for transit routes API endpoints.

Follows the same strategy as other API unit tests:
- Call the endpoint function directly
- Inject a mocked domain service
- Assert HTTPException mapping + response contracts
"""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.domains.transit.exceptions import TransitRouteError, TransitValidationError
from app.domains.transit.schemas import (
    Leg,
    Location,
    Route,
    Step,
    TransitRouteRequest,
    TransitRouteResponse,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def sample_transit_request() -> TransitRouteRequest:
    """Sample transit route request."""
    return TransitRouteRequest(
        origin=Location(address="Lisbon Airport"),
        destination=Location(address="Rossio Station"),
        compute_alternative_routes=True,
        # travel_mode defaults to TRANSIT
    )


@pytest.fixture
def sample_transit_response() -> TransitRouteResponse:
    """Sample transit route response (minimal valid shape)."""
    return TransitRouteResponse(
        routes=[
            Route(
                legs=[
                    Leg(
                        steps=[
                            # Step schema currently only includes optional transit_details
                            Step(transit_details=None)
                        ]
                    )
                ]
            )
        ]
    )


# ==============================================================================
# COMPUTE ROUTES ENDPOINT TESTS
# ==============================================================================


class TestComputeTransitRoutesEndpoint:
    """Test POST /transit/routes endpoint handler."""

    @pytest.mark.asyncio
    async def test_compute_routes_success(
        self,
        sample_transit_request: TransitRouteRequest,
        sample_transit_response: TransitRouteResponse,
    ):
        """Endpoint returns service response on success."""
        mock_service = AsyncMock()
        mock_service.compute_routes = AsyncMock(return_value=sample_transit_response)

        from app.api.transit import compute_routes

        result = await compute_routes(sample_transit_request, mock_service)

        mock_service.compute_routes.assert_called_once_with(sample_transit_request)
        assert result == sample_transit_response
        assert len(result.routes) == 1

    @pytest.mark.asyncio
    async def test_compute_routes_validation_error_returns_400(
        self,
        sample_transit_request: TransitRouteRequest,
    ):
        """TransitValidationError is mapped to HTTP 400."""
        mock_service = AsyncMock()
        mock_service.compute_routes = AsyncMock(
            side_effect=TransitValidationError(field="origin", reason="required")
        )

        from app.api.transit import compute_routes

        with pytest.raises(HTTPException) as exc_info:
            await compute_routes(sample_transit_request, mock_service)

        assert exc_info.value.status_code == 400
        assert "Validation failed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_compute_routes_route_error_returns_503(
        self,
        sample_transit_request: TransitRouteRequest,
    ):
        """TransitRouteError is mapped to HTTP 503."""
        mock_service = AsyncMock()
        mock_service.compute_routes = AsyncMock(
            side_effect=TransitRouteError(reason="Google Maps unavailable")
        )

        from app.api.transit import compute_routes

        with pytest.raises(HTTPException) as exc_info:
            await compute_routes(sample_transit_request, mock_service)

        assert exc_info.value.status_code == 503
        assert "Transit route failed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_compute_routes_value_error_returns_400(
        self,
        sample_transit_request: TransitRouteRequest,
    ):
        """ValueError is mapped to HTTP 400."""
        mock_service = AsyncMock()
        mock_service.compute_routes = AsyncMock(side_effect=ValueError("Bad input"))

        from app.api.transit import compute_routes

        with pytest.raises(HTTPException) as exc_info:
            await compute_routes(sample_transit_request, mock_service)

        assert exc_info.value.status_code == 400
        assert "Bad input" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_compute_routes_unexpected_error_returns_500(
        self,
        sample_transit_request: TransitRouteRequest,
    ):
        """Unexpected errors are mapped to HTTP 500 with a safe message."""
        mock_service = AsyncMock()
        mock_service.compute_routes = AsyncMock(side_effect=RuntimeError("Boom"))

        from app.api.transit import compute_routes

        with pytest.raises(HTTPException) as exc_info:
            await compute_routes(sample_transit_request, mock_service)

        assert exc_info.value.status_code == 500
        assert "Internal server error" in str(exc_info.value.detail)
