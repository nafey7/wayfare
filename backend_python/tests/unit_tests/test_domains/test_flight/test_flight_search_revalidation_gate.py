"""Flight search post-search revalidation is gated by FLIGHT_SEARCH_CONCURRENT_REVALIDATION."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.domains.flight.enums import CabinClass, JourneyType
from app.domains.flight.schemas import (
    AirlineListResponse,
    FlightRevalidateRequest,
    FlightRevalidateResponse,
    FlightSearchRequest,
    FlightSearchResponse,
    OriginDestinationSegment,
)
from app.domains.flight.service import FlightService
from tests.unit_tests.test_domains.test_flight.test_city_wise_filtering import (
    create_mock_airport,
    create_mock_fare_itinerary,
)


@pytest.fixture
def flight_service() -> FlightService:
    return FlightService(current_user=None)


@pytest.fixture
def base_search_request() -> FlightSearchRequest:
    return FlightSearchRequest(
        journey_type=JourneyType.ONE_WAY,
        origin_destination_info=[
            OriginDestinationSegment(
                departure_date=datetime.now(UTC).date(),
                origin_airport=create_mock_airport("LHR"),
                destination_airport=create_mock_airport("CDG"),
            )
        ],
        cabin_class=CabinClass.ECONOMY,
        adults=1,
        children=0,
        infants=0,
        required_currency_code="USD",
        revalidate_flights_count=2,
    )


@pytest.mark.asyncio
async def test_search_does_not_call_revalidate_when_flag_disabled(
    flight_service: FlightService,
    base_search_request: FlightSearchRequest,
) -> None:
    flights = [
        create_mock_fare_itinerary(
            "LHR", "CDG", fare_source_code="F1", price=Decimal("100.00")
        ),
        create_mock_fare_itinerary(
            "LHR", "CDG", fare_source_code="F2", price=Decimal("200.00")
        ),
    ]
    response = FlightSearchResponse(
        session_id="sess_gate_off", supplier="test", fare_itineraries=flights
    )

    with (
        patch.object(settings, "FLIGHT_SEARCH_CONCURRENT_REVALIDATION", False),
        patch.object(
            flight_service.client, "search_flights", new_callable=AsyncMock
        ) as mock_search,
        patch.object(
            flight_service,
            "get_airline_list",
            new_callable=AsyncMock,
            return_value=AirlineListResponse(airlines=[]),
        ),
        patch.object(flight_service, "revalidate_fare", new_callable=AsyncMock) as rev,
    ):
        mock_search.return_value = response
        result = await flight_service.search_flights(base_search_request)

    rev.assert_not_called()
    assert len(result.fare_itineraries) == 2
    assert {fi.pricing.fare_source_code for fi in result.fare_itineraries} == {
        "F1",
        "F2",
    }


@pytest.mark.asyncio
async def test_search_revalidates_and_filters_when_flag_enabled(
    flight_service: FlightService,
    base_search_request: FlightSearchRequest,
) -> None:
    flights = [
        create_mock_fare_itinerary(
            "LHR", "CDG", fare_source_code="F1", price=Decimal("100.00")
        ),
    ]
    response = FlightSearchResponse(
        session_id="sess_gate_on", supplier="test", fare_itineraries=flights
    )

    async def revalidate_impl(req: FlightRevalidateRequest) -> FlightRevalidateResponse:
        return FlightRevalidateResponse(
            session_id=req.session_id,
            fare_source_code=req.fare_source_code,
            return_fare_source_code=None,
            is_fare_available=False,
            validated_fare_itineraries=[],
        )

    with (
        patch.object(settings, "FLIGHT_SEARCH_CONCURRENT_REVALIDATION", True),
        patch.object(
            flight_service.client, "search_flights", new_callable=AsyncMock
        ) as mock_search,
        patch.object(
            flight_service,
            "get_airline_list",
            new_callable=AsyncMock,
            return_value=AirlineListResponse(airlines=[]),
        ),
        patch.object(flight_service, "revalidate_fare", side_effect=revalidate_impl),
    ):
        mock_search.return_value = response
        result = await flight_service.search_flights(
            base_search_request.model_copy(update={"revalidate_flights_count": 1})
        )

    assert result.fare_itineraries == []
