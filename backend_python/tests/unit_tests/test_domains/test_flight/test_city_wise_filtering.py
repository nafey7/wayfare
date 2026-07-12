"""Unit tests for city-wise flight filtering functionality (PR #209).

Tests the filtering logic for outbound and inbound flights based on
city_wise_search_origin and city_wise_search_destination flags.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.domains.common.schemas import DateTime, Duration, MoneyAmount
from app.domains.flight.enums import CabinClass, FareType, JourneyType, TicketType
from app.domains.flight.schemas import (
    AirlineInfo,
    AirlineListResponse,
    AirportInfo,
    FareItinerary,
    FarePricing,
    FareTotals,
    FlightLeg,
    FlightNumber,
    FlightSearchFilters,
    FlightSearchRequest,
    FlightSearchResponse,
    FlightSegment,
    OriginDestinationSegment,
    SeatAvailability,
)
from app.domains.flight.service import FlightService

# ==============================================================================
# TEST FIXTURES
# ==============================================================================


def create_mock_airport(iata_code: str) -> AirportInfo:
    """Create a mock AirportInfo object."""
    return AirportInfo(iata_code=iata_code)


def create_mock_airline(
    iata_code: str = "BA", name: str = "British Airways"
) -> AirlineInfo:
    """Create a mock AirlineInfo object."""
    return AirlineInfo(iata_code=iata_code, airline_name=name)


def create_mock_segment(
    origin_code: str,
    destination_code: str,
    departure_datetime: datetime | None = None,
    arrival_datetime: datetime | None = None,
) -> FlightSegment:
    """Create a mock FlightSegment."""
    if departure_datetime is None:
        departure_datetime = datetime.now(UTC)
    if arrival_datetime is None:
        arrival_datetime = departure_datetime + timedelta(hours=2)

    return FlightSegment(
        arrival_airport=create_mock_airport(destination_code),
        arrival_datetime=DateTime(value=arrival_datetime),
        departure_airport=create_mock_airport(origin_code),
        departure_datetime=DateTime(value=departure_datetime),
        cabin_class=CabinClass.ECONOMY,
        e_ticket=True,
        flight_duration=Duration(total_minutes=120),
        marketing_flight_number=FlightNumber(
            airline_prefix="BA", flight_number="123", formatted_number="BA123"
        ),
        marketing_airline=create_mock_airline(),
        operating_airline=create_mock_airline(),
        operating_flight_number=FlightNumber(
            airline_prefix="BA", flight_number="123", formatted_number="BA123"
        ),
        segment_stops=0,
        seat_availability=SeatAvailability(available_seats=9, is_limited=False),
    )


def create_mock_leg(
    segments: list[FlightSegment],
    total_stops: int = 0,
) -> FlightLeg:
    """Create a mock FlightLeg."""
    return FlightLeg(
        total_stops=total_stops,
        flight_segments=segments,
    )


def create_mock_fare_itinerary(
    origin_code: str,
    destination_code: str,
    journey_type: JourneyType = JourneyType.ONE_WAY,
    fare_source_code: str = "FARE_123",
    price: Decimal = Decimal("200.00"),
) -> FareItinerary:
    """Create a mock FareItinerary with a single leg."""
    segment = create_mock_segment(origin_code, destination_code)
    leg = create_mock_leg([segment])

    pricing = FarePricing(
        has_mixed_booking_classes=False,
        fare_source_code=fare_source_code,
        fare_type=FareType.PUBLIC,
        is_refundable=True,
        fare_totals=FareTotals(
            base_fare=MoneyAmount(
                amount=price * Decimal("0.8"), currency="USD", decimal_places=2
            ),
            equivalent_fare=MoneyAmount(
                amount=price * Decimal("0.8"), currency="USD", decimal_places=2
            ),
            service_tax=MoneyAmount(
                amount=Decimal("0.00"), currency="USD", decimal_places=2
            ),
            total_tax=MoneyAmount(
                amount=price * Decimal("0.2"), currency="USD", decimal_places=2
            ),
            total_fare=MoneyAmount(amount=price, currency="USD", decimal_places=2),
        ),
        passenger_fare_breakdown=[],
    )

    return FareItinerary(
        journey_type=journey_type,
        ticket_type=TicketType.E_TICKET,
        validating_airline=create_mock_airline(),
        flight_legs=[leg],
        pricing=pricing,
    )


def create_roundtrip_fare_itinerary(
    outbound_origin: str,
    outbound_destination: str,
    inbound_origin: str,
    inbound_destination: str,
    fare_source_code: str = "FARE_123",
    price: Decimal = Decimal("400.00"),
) -> tuple[FareItinerary, FareItinerary]:
    """Create outbound and inbound FareItinerary objects for round trip."""
    outbound = create_mock_fare_itinerary(
        outbound_origin,
        outbound_destination,
        JourneyType.RETURN,
        f"{fare_source_code}_OUT",
        price,
    )

    inbound = create_mock_fare_itinerary(
        inbound_origin,
        inbound_destination,
        JourneyType.RETURN,
        f"{fare_source_code}_IN",
        price,
    )

    return outbound, inbound


@pytest.fixture
def flight_service():
    """Create a FlightService instance for testing."""
    return FlightService(current_user=None)


@pytest.fixture
def base_search_request():
    """Create a base FlightSearchRequest for testing."""
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
    )


# ==============================================================================
# OUTBOUND FLIGHT FILTERING TESTS
# ==============================================================================


class TestOutboundFlightFiltering:
    """Test outbound flight filtering based on city_wise_search flags."""

    @pytest.mark.asyncio
    async def test_city_wise_origin_true_keeps_all_origins(
        self, flight_service: FlightService, base_search_request: FlightSearchRequest
    ):
        """Test that city_wise_search_origin=True doesn't filter by origin airport code."""
        # Request: LHR -> CDG with city_wise_search_origin=True
        request = base_search_request.model_copy(
            update={"city_wise_search_origin": True}
        )

        # Create flights with different origins (LHR, LGW, STN - all London airports)
        flights = [
            create_mock_fare_itinerary("LHR", "CDG", fare_source_code="FARE_1"),
            create_mock_fare_itinerary("LGW", "CDG", fare_source_code="FARE_2"),
            create_mock_fare_itinerary("STN", "CDG", fare_source_code="FARE_3"),
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # All flights should be kept (no origin filtering)
            assert len(result.fare_itineraries) == 3
            assert all(
                f.pricing.fare_source_code in ["FARE_1", "FARE_2", "FARE_3"]
                for f in result.fare_itineraries
            )

    @pytest.mark.asyncio
    async def test_airport_code_origin_false_filters_to_exact_match(
        self, flight_service: FlightService, base_search_request: FlightSearchRequest
    ):
        """Test that city_wise_search_origin=False filters to exact origin airport code."""
        # Request: LHR -> CDG with city_wise_search_origin=False
        request = base_search_request.model_copy(
            update={"city_wise_search_origin": False}
        )

        # Create flights with different origins
        flights = [
            create_mock_fare_itinerary(
                "LHR", "CDG", fare_source_code="FARE_1"
            ),  # Match
            create_mock_fare_itinerary(
                "LGW", "CDG", fare_source_code="FARE_2"
            ),  # Filtered out
            create_mock_fare_itinerary(
                "STN", "CDG", fare_source_code="FARE_3"
            ),  # Filtered out
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only LHR -> CDG should be kept
            assert len(result.fare_itineraries) == 1
            assert result.fare_itineraries[0].pricing.fare_source_code == "FARE_1"

    @pytest.mark.asyncio
    async def test_airport_code_origin_none_filters_to_exact_match(
        self, flight_service: FlightService, base_search_request: FlightSearchRequest
    ):
        """Test that city_wise_search_origin=None filters to exact origin airport code."""
        # Request: LHR -> CDG with city_wise_search_origin=None (default)
        request = base_search_request.model_copy(
            update={"city_wise_search_origin": None}
        )

        flights = [
            create_mock_fare_itinerary(
                "LHR", "CDG", fare_source_code="FARE_1"
            ),  # Match
            create_mock_fare_itinerary(
                "LGW", "CDG", fare_source_code="FARE_2"
            ),  # Filtered out
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only LHR -> CDG should be kept
            assert len(result.fare_itineraries) == 1
            assert result.fare_itineraries[0].pricing.fare_source_code == "FARE_1"

    @pytest.mark.asyncio
    async def test_city_wise_destination_true_keeps_all_destinations(
        self, flight_service: FlightService, base_search_request: FlightSearchRequest
    ):
        """Test that city_wise_search_destination=True doesn't filter by destination airport code."""
        # Request: LHR -> CDG with city_wise_search_destination=True
        request = base_search_request.model_copy(
            update={"city_wise_search_destination": True}
        )

        # Create flights with different destinations (CDG, ORY - both Paris airports)
        flights = [
            create_mock_fare_itinerary("LHR", "CDG", fare_source_code="FARE_1"),
            create_mock_fare_itinerary("LHR", "ORY", fare_source_code="FARE_2"),
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # All flights should be kept (no destination filtering)
            assert len(result.fare_itineraries) == 2

    @pytest.mark.asyncio
    async def test_airport_code_destination_false_filters_to_exact_match(
        self, flight_service: FlightService, base_search_request: FlightSearchRequest
    ):
        """Test that city_wise_search_destination=False filters to exact destination airport code."""
        # Request: LHR -> CDG with city_wise_search_destination=False
        request = base_search_request.model_copy(
            update={"city_wise_search_destination": False}
        )

        flights = [
            create_mock_fare_itinerary(
                "LHR", "CDG", fare_source_code="FARE_1"
            ),  # Match
            create_mock_fare_itinerary(
                "LHR", "ORY", fare_source_code="FARE_2"
            ),  # Filtered out
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only LHR -> CDG should be kept
            assert len(result.fare_itineraries) == 1
            assert result.fare_itineraries[0].pricing.fare_source_code == "FARE_1"

    @pytest.mark.asyncio
    async def test_airport_code_destination_none_filters_to_exact_match(
        self, flight_service: FlightService, base_search_request: FlightSearchRequest
    ):
        """Test that city_wise_search_destination=None filters to exact destination airport code."""
        request = base_search_request.model_copy(
            update={"city_wise_search_destination": None}
        )

        flights = [
            create_mock_fare_itinerary(
                "LHR", "CDG", fare_source_code="FARE_1"
            ),  # Match
            create_mock_fare_itinerary(
                "LHR", "ORY", fare_source_code="FARE_2"
            ),  # Filtered out
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            assert len(result.fare_itineraries) == 1
            assert result.fare_itineraries[0].pricing.fare_source_code == "FARE_1"

    @pytest.mark.asyncio
    async def test_both_city_wise_keeps_all_flights(
        self, flight_service: FlightService, base_search_request: FlightSearchRequest
    ):
        """Test that both flags=True keeps all flights regardless of origin/destination."""
        request = base_search_request.model_copy(
            update={
                "city_wise_search_origin": True,
                "city_wise_search_destination": True,
            }
        )

        # Create flights with various origins and destinations
        flights = [
            create_mock_fare_itinerary("LHR", "CDG", fare_source_code="FARE_1"),
            create_mock_fare_itinerary("LGW", "CDG", fare_source_code="FARE_2"),
            create_mock_fare_itinerary("LHR", "ORY", fare_source_code="FARE_3"),
            create_mock_fare_itinerary("STN", "ORY", fare_source_code="FARE_4"),
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # All flights should be kept
            assert len(result.fare_itineraries) == 4

    @pytest.mark.asyncio
    async def test_both_airport_code_filters_both_origin_and_destination(
        self, flight_service: FlightService, base_search_request: FlightSearchRequest
    ):
        """Test that both flags=False filters both origin and destination."""
        request = base_search_request.model_copy(
            update={
                "city_wise_search_origin": False,
                "city_wise_search_destination": False,
            }
        )

        flights = [
            create_mock_fare_itinerary(
                "LHR", "CDG", fare_source_code="FARE_1"
            ),  # Match both
            create_mock_fare_itinerary(
                "LGW", "CDG", fare_source_code="FARE_2"
            ),  # Wrong origin
            create_mock_fare_itinerary(
                "LHR", "ORY", fare_source_code="FARE_3"
            ),  # Wrong destination
            create_mock_fare_itinerary(
                "STN", "ORY", fare_source_code="FARE_4"
            ),  # Wrong both
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only LHR -> CDG should be kept
            assert len(result.fare_itineraries) == 1
            assert result.fare_itineraries[0].pricing.fare_source_code == "FARE_1"

    @pytest.mark.asyncio
    async def test_mixed_city_origin_airport_destination(
        self, flight_service: FlightService, base_search_request: FlightSearchRequest
    ):
        """Test mixed flags: city-wise origin + airport code destination."""
        request = base_search_request.model_copy(
            update={
                "city_wise_search_origin": True,
                "city_wise_search_destination": False,
            }
        )

        flights = [
            create_mock_fare_itinerary(
                "LHR", "CDG", fare_source_code="FARE_1"
            ),  # Match destination
            create_mock_fare_itinerary(
                "LGW", "CDG", fare_source_code="FARE_2"
            ),  # Match destination
            create_mock_fare_itinerary(
                "LHR", "ORY", fare_source_code="FARE_3"
            ),  # Wrong destination
            create_mock_fare_itinerary(
                "STN", "ORY", fare_source_code="FARE_4"
            ),  # Wrong destination
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only flights with destination=CDG should be kept (origin can be any)
            assert len(result.fare_itineraries) == 2
            assert all(
                f.flight_legs[0].flight_segments[-1].arrival_airport.iata_code == "CDG"
                for f in result.fare_itineraries
            )

    @pytest.mark.asyncio
    async def test_mixed_airport_origin_city_destination(
        self, flight_service: FlightService, base_search_request: FlightSearchRequest
    ):
        """Test mixed flags: airport code origin + city-wise destination."""
        request = base_search_request.model_copy(
            update={
                "city_wise_search_origin": False,
                "city_wise_search_destination": True,
            }
        )

        flights = [
            create_mock_fare_itinerary(
                "LHR", "CDG", fare_source_code="FARE_1"
            ),  # Match origin
            create_mock_fare_itinerary(
                "LHR", "ORY", fare_source_code="FARE_2"
            ),  # Match origin
            create_mock_fare_itinerary(
                "LGW", "CDG", fare_source_code="FARE_3"
            ),  # Wrong origin
            create_mock_fare_itinerary(
                "STN", "ORY", fare_source_code="FARE_4"
            ),  # Wrong origin
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only flights with origin=LHR should be kept (destination can be any)
            assert len(result.fare_itineraries) == 2
            assert all(
                f.flight_legs[0].flight_segments[0].departure_airport.iata_code == "LHR"
                for f in result.fare_itineraries
            )


# ==============================================================================
# INBOUND FLIGHT FILTERING TESTS (ROUND TRIP)
# ==============================================================================


class TestInboundFlightFiltering:
    """Test inbound flight filtering for round trips."""

    @pytest.fixture
    def roundtrip_request(self, base_search_request):
        """Create a round trip request (two O&D rows per Return contract)."""
        out_date = base_search_request.origin_destination_info[0].departure_date
        inbound_date = out_date + timedelta(days=7)
        return base_search_request.model_copy(
            update={
                "journey_type": JourneyType.RETURN,
                "origin_destination_info": [
                    OriginDestinationSegment(
                        departure_date=out_date,
                        origin_airport=create_mock_airport("LHR"),
                        destination_airport=create_mock_airport("CDG"),
                    ),
                    OriginDestinationSegment(
                        departure_date=inbound_date,
                        origin_airport=create_mock_airport("CDG"),
                        destination_airport=create_mock_airport("LHR"),
                    ),
                ],
            }
        )

    @pytest.mark.asyncio
    async def test_city_wise_origin_true_allows_any_inbound_destination(
        self, flight_service: FlightService, roundtrip_request: FlightSearchRequest
    ):
        """Test that city_wise_search_origin=True doesn't filter inbound destination (original origin)."""
        # Request: LHR -> CDG round trip with city_wise_search_origin=True
        request = roundtrip_request.model_copy(update={"city_wise_search_origin": True})

        # Outbound: LHR -> CDG
        outbound_flights = [
            create_mock_fare_itinerary("LHR", "CDG", JourneyType.RETURN, "OUT_1"),
        ]

        # Inbound: CDG -> LHR, CDG -> LGW, CDG -> STN (all should be kept)
        inbound_flights = [
            create_mock_fare_itinerary("CDG", "LHR", JourneyType.RETURN, "IN_1"),
            create_mock_fare_itinerary("CDG", "LGW", JourneyType.RETURN, "IN_2"),
            create_mock_fare_itinerary("CDG", "STN", JourneyType.RETURN, "IN_3"),
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=outbound_flights,
            inbound_fare_itineraries=inbound_flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # All inbound flights should be kept (no filtering on inbound destination)
            assert len(result.inbound_fare_itineraries) == 3

    @pytest.mark.asyncio
    async def test_airport_code_origin_false_filters_inbound_destination(
        self, flight_service: FlightService, roundtrip_request: FlightSearchRequest
    ):
        """Test that city_wise_search_origin=False filters inbound destination to exact original origin code."""
        # Request: LHR -> CDG round trip with city_wise_search_origin=False
        request = roundtrip_request.model_copy(
            update={"city_wise_search_origin": False}
        )

        outbound_flights = [
            create_mock_fare_itinerary("LHR", "CDG", JourneyType.RETURN, "OUT_1"),
        ]

        # Inbound: CDG -> LHR (match), CDG -> LGW (filtered), CDG -> STN (filtered)
        inbound_flights = [
            create_mock_fare_itinerary("CDG", "LHR", JourneyType.RETURN, "IN_1"),
            create_mock_fare_itinerary("CDG", "LGW", JourneyType.RETURN, "IN_2"),
            create_mock_fare_itinerary("CDG", "STN", JourneyType.RETURN, "IN_3"),
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=outbound_flights,
            inbound_fare_itineraries=inbound_flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only CDG -> LHR should be kept
            assert len(result.inbound_fare_itineraries) == 1
            assert result.inbound_fare_itineraries[0].pricing.fare_source_code == "IN_1"

    @pytest.mark.asyncio
    async def test_city_wise_destination_true_allows_any_inbound_origin(
        self, flight_service: FlightService, roundtrip_request: FlightSearchRequest
    ):
        """Test that city_wise_search_destination=True doesn't filter inbound origin (original destination)."""
        # Request: LHR -> CDG round trip with city_wise_search_destination=True
        request = roundtrip_request.model_copy(
            update={"city_wise_search_destination": True}
        )

        outbound_flights = [
            create_mock_fare_itinerary("LHR", "CDG", JourneyType.RETURN, "OUT_1"),
        ]

        # Inbound: CDG -> LHR, ORY -> LHR (both should be kept)
        inbound_flights = [
            create_mock_fare_itinerary("CDG", "LHR", JourneyType.RETURN, "IN_1"),
            create_mock_fare_itinerary("ORY", "LHR", JourneyType.RETURN, "IN_2"),
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=outbound_flights,
            inbound_fare_itineraries=inbound_flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # All inbound flights should be kept (no filtering on inbound origin)
            assert len(result.inbound_fare_itineraries) == 2

    @pytest.mark.asyncio
    async def test_airport_code_destination_false_filters_inbound_origin(
        self, flight_service: FlightService, roundtrip_request: FlightSearchRequest
    ):
        """Test that city_wise_search_destination=False filters inbound origin to exact original destination code."""
        # Request: LHR -> CDG round trip with city_wise_search_destination=False
        request = roundtrip_request.model_copy(
            update={"city_wise_search_destination": False}
        )

        outbound_flights = [
            create_mock_fare_itinerary("LHR", "CDG", JourneyType.RETURN, "OUT_1"),
        ]

        # Inbound: CDG -> LHR (match), ORY -> LHR (filtered)
        inbound_flights = [
            create_mock_fare_itinerary("CDG", "LHR", JourneyType.RETURN, "IN_1"),
            create_mock_fare_itinerary("ORY", "LHR", JourneyType.RETURN, "IN_2"),
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=outbound_flights,
            inbound_fare_itineraries=inbound_flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only CDG -> LHR should be kept
            assert len(result.inbound_fare_itineraries) == 1
            assert result.inbound_fare_itineraries[0].pricing.fare_source_code == "IN_1"

    @pytest.mark.asyncio
    async def test_both_city_wise_round_trip_keeps_all_inbound(
        self, flight_service: FlightService, roundtrip_request: FlightSearchRequest
    ):
        """Test that both flags=True keeps all inbound flights."""
        request = roundtrip_request.model_copy(
            update={
                "city_wise_search_origin": True,
                "city_wise_search_destination": True,
            }
        )

        outbound_flights = [
            create_mock_fare_itinerary("LHR", "CDG", JourneyType.RETURN, "OUT_1"),
        ]

        # Various inbound flights - all should be kept
        inbound_flights = [
            create_mock_fare_itinerary("CDG", "LHR", JourneyType.RETURN, "IN_1"),
            create_mock_fare_itinerary("CDG", "LGW", JourneyType.RETURN, "IN_2"),
            create_mock_fare_itinerary("ORY", "LHR", JourneyType.RETURN, "IN_3"),
            create_mock_fare_itinerary("ORY", "STN", JourneyType.RETURN, "IN_4"),
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=outbound_flights,
            inbound_fare_itineraries=inbound_flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # All inbound flights should be kept
            assert len(result.inbound_fare_itineraries) == 4

    @pytest.mark.asyncio
    async def test_both_airport_code_round_trip_filters_both_inbound(
        self, flight_service: FlightService, roundtrip_request: FlightSearchRequest
    ):
        """Test that both flags=False filters both inbound origin and destination."""
        request = roundtrip_request.model_copy(
            update={
                "city_wise_search_origin": False,
                "city_wise_search_destination": False,
            }
        )

        outbound_flights = [
            create_mock_fare_itinerary("LHR", "CDG", JourneyType.RETURN, "OUT_1"),
        ]

        # Inbound: CDG -> LHR (match both), others filtered
        inbound_flights = [
            create_mock_fare_itinerary(
                "CDG", "LHR", JourneyType.RETURN, "IN_1"
            ),  # Match
            create_mock_fare_itinerary(
                "CDG", "LGW", JourneyType.RETURN, "IN_2"
            ),  # Wrong destination
            create_mock_fare_itinerary(
                "ORY", "LHR", JourneyType.RETURN, "IN_3"
            ),  # Wrong origin
            create_mock_fare_itinerary(
                "ORY", "STN", JourneyType.RETURN, "IN_4"
            ),  # Wrong both
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=outbound_flights,
            inbound_fare_itineraries=inbound_flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only CDG -> LHR should be kept
            assert len(result.inbound_fare_itineraries) == 1
            assert result.inbound_fare_itineraries[0].pricing.fare_source_code == "IN_1"

    @pytest.mark.asyncio
    async def test_mixed_city_origin_airport_destination_round_trip(
        self, flight_service: FlightService, roundtrip_request: FlightSearchRequest
    ):
        """Test mixed flags for round trip: city-wise origin + airport code destination."""
        request = roundtrip_request.model_copy(
            update={
                "city_wise_search_origin": True,
                "city_wise_search_destination": False,
            }
        )

        outbound_flights = [
            create_mock_fare_itinerary("LHR", "CDG", JourneyType.RETURN, "OUT_1"),
        ]

        # Inbound: destination must be LHR (original origin), origin can be any (CDG or ORY)
        inbound_flights = [
            create_mock_fare_itinerary(
                "CDG", "LHR", JourneyType.RETURN, "IN_1"
            ),  # Match
            create_mock_fare_itinerary(
                "CDG", "LGW", JourneyType.RETURN, "IN_2"
            ),  # Wrong destination
            create_mock_fare_itinerary(
                "ORY", "LHR", JourneyType.RETURN, "IN_3"
            ),  # Match
            create_mock_fare_itinerary(
                "ORY", "STN", JourneyType.RETURN, "IN_4"
            ),  # Wrong destination
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=outbound_flights,
            inbound_fare_itineraries=inbound_flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only flights with origin=CDG should be kept (destination can be any since city_wise_search_origin=True)
            assert len(result.inbound_fare_itineraries) == 2
            # Service uses flight_legs[0] for inbound origin (first leg's first segment)
            # With city_wise_search_destination=False, origin must be CDG
            # With city_wise_search_origin=True, destination can be any (LHR or LGW)
            for f in result.inbound_fare_itineraries:
                first_leg = f.flight_legs[0]
                origin_code = first_leg.flight_segments[0].departure_airport.iata_code
                assert origin_code == "CDG", f"Expected CDG, got {origin_code}"

    @pytest.mark.asyncio
    async def test_mixed_airport_origin_city_destination_round_trip(
        self, flight_service: FlightService, roundtrip_request: FlightSearchRequest
    ):
        """Test mixed flags for round trip: airport code origin + city-wise destination."""
        request = roundtrip_request.model_copy(
            update={
                "city_wise_search_origin": False,
                "city_wise_search_destination": True,
            }
        )

        outbound_flights = [
            create_mock_fare_itinerary("LHR", "CDG", JourneyType.RETURN, "OUT_1"),
        ]

        # Inbound: origin must be CDG (original destination), destination can be any (LHR, LGW, STN)
        inbound_flights = [
            create_mock_fare_itinerary(
                "CDG", "LHR", JourneyType.RETURN, "IN_1"
            ),  # Match
            create_mock_fare_itinerary(
                "CDG", "LGW", JourneyType.RETURN, "IN_2"
            ),  # Match
            create_mock_fare_itinerary(
                "ORY", "LHR", JourneyType.RETURN, "IN_3"
            ),  # Wrong origin
            create_mock_fare_itinerary(
                "ORY", "STN", JourneyType.RETURN, "IN_4"
            ),  # Wrong origin
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=outbound_flights,
            inbound_fare_itineraries=inbound_flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only flights with destination=LHR should be kept (origin can be any since city_wise_search_destination=True)
            assert len(result.inbound_fare_itineraries) == 2
            # Service uses flight_legs[-1] for inbound destination (last leg's last segment)
            # With city_wise_search_origin=False, destination must be LHR
            # With city_wise_search_destination=True, origin can be any (CDG or ORY)
            for f in result.inbound_fare_itineraries:
                last_leg = f.flight_legs[-1]
                destination_code = last_leg.flight_segments[
                    -1
                ].arrival_airport.iata_code
                assert destination_code == "LHR", (
                    f"Expected LHR, got {destination_code}"
                )


# ==============================================================================
# EDGE CASE TESTS
# ==============================================================================


class TestEdgeCases:
    """Test edge cases for flight filtering."""

    @pytest.mark.asyncio
    async def test_empty_flight_legs_filtered_out(self, flight_service: FlightService):
        """Test that flights with empty flight_legs are filtered out."""
        request = FlightSearchRequest(
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
            city_wise_search_origin=False,
            city_wise_search_destination=False,
        )

        # Create a flight with empty flight_legs
        flight_with_empty_legs = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[],  # Empty!
            pricing=FarePricing(
                has_mixed_booking_classes=False,
                fare_source_code="FARE_EMPTY",
                fare_type=FareType.PUBLIC,
                is_refundable=True,
                fare_totals=FareTotals(
                    base_fare=MoneyAmount(
                        amount=Decimal("100.00"), currency="USD", decimal_places=2
                    ),
                    equivalent_fare=MoneyAmount(
                        amount=Decimal("100.00"), currency="USD", decimal_places=2
                    ),
                    service_tax=MoneyAmount(
                        amount=Decimal("0.00"), currency="USD", decimal_places=2
                    ),
                    total_tax=MoneyAmount(
                        amount=Decimal("20.00"), currency="USD", decimal_places=2
                    ),
                    total_fare=MoneyAmount(
                        amount=Decimal("200.00"), currency="USD", decimal_places=2
                    ),
                ),
                passenger_fare_breakdown=[],
            ),
        )

        valid_flight = create_mock_fare_itinerary(
            "LHR", "CDG", fare_source_code="FARE_VALID"
        )

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=[flight_with_empty_legs, valid_flight],
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only valid flight should be kept
            assert len(result.fare_itineraries) == 1
            assert result.fare_itineraries[0].pricing.fare_source_code == "FARE_VALID"

    @pytest.mark.asyncio
    async def test_empty_flight_segments_filtered_out(
        self, flight_service: FlightService
    ):
        """Test that flights with empty flight_segments are filtered out."""
        request = FlightSearchRequest(
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
            city_wise_search_origin=False,
            city_wise_search_destination=False,
        )

        # Create a flight with empty flight_segments
        leg_with_empty_segments = create_mock_leg([])  # Empty segments
        flight_with_empty_segments = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[leg_with_empty_segments],
            pricing=FarePricing(
                has_mixed_booking_classes=False,
                fare_source_code="FARE_EMPTY_SEG",
                fare_type=FareType.PUBLIC,
                is_refundable=True,
                fare_totals=FareTotals(
                    base_fare=MoneyAmount(
                        amount=Decimal("100.00"), currency="USD", decimal_places=2
                    ),
                    equivalent_fare=MoneyAmount(
                        amount=Decimal("100.00"), currency="USD", decimal_places=2
                    ),
                    service_tax=MoneyAmount(
                        amount=Decimal("0.00"), currency="USD", decimal_places=2
                    ),
                    total_tax=MoneyAmount(
                        amount=Decimal("20.00"), currency="USD", decimal_places=2
                    ),
                    total_fare=MoneyAmount(
                        amount=Decimal("200.00"), currency="USD", decimal_places=2
                    ),
                ),
                passenger_fare_breakdown=[],
            ),
        )

        valid_flight = create_mock_fare_itinerary(
            "LHR", "CDG", fare_source_code="FARE_VALID"
        )

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=[flight_with_empty_segments, valid_flight],
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only valid flight should be kept
            assert len(result.fare_itineraries) == 1
            assert result.fare_itineraries[0].pricing.fare_source_code == "FARE_VALID"

    @pytest.mark.asyncio
    async def test_missing_origin_destination_info_skips_filtering(
        self, flight_service: FlightService
    ):
        """Empty O&D is invalid for normal validation; model_construct exercises the service guard."""
        request = FlightSearchRequest.model_construct(
            journey_type=JourneyType.ONE_WAY,
            origin_destination_info=[],
            cabin_class=CabinClass.ECONOMY,
            adults=1,
            children=0,
            infants=0,
            required_currency_code="USD",
            city_wise_search_origin=False,
            city_wise_search_destination=False,
            filters=FlightSearchFilters(
                city_wise_search_origin=False,
                city_wise_search_destination=False,
            ),
        )

        flights = [
            create_mock_fare_itinerary("LHR", "CDG", fare_source_code="FARE_1"),
            create_mock_fare_itinerary("LGW", "ORY", fare_source_code="FARE_2"),
        ]

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=flights,
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # All flights should be kept (no filtering when origin_destination_info is empty)
            assert len(result.fare_itineraries) == 2

    @pytest.mark.asyncio
    async def test_round_trip_empty_inbound_legs_filtered_out(
        self, flight_service: FlightService
    ):
        """Test that inbound flights with empty flight_legs are filtered out."""
        out_date = datetime.now(UTC).date()
        request = FlightSearchRequest(
            journey_type=JourneyType.RETURN,
            origin_destination_info=[
                OriginDestinationSegment(
                    departure_date=out_date,
                    origin_airport=create_mock_airport("LHR"),
                    destination_airport=create_mock_airport("CDG"),
                ),
                OriginDestinationSegment(
                    departure_date=out_date,
                    origin_airport=create_mock_airport("CDG"),
                    destination_airport=create_mock_airport("LHR"),
                ),
            ],
            cabin_class=CabinClass.ECONOMY,
            adults=1,
            children=0,
            infants=0,
            required_currency_code="USD",
            city_wise_search_origin=False,
            city_wise_search_destination=False,
        )

        outbound_flights = [
            create_mock_fare_itinerary("LHR", "CDG", JourneyType.RETURN, "OUT_1"),
        ]

        # Create inbound flight with empty flight_legs
        inbound_with_empty_legs = FareItinerary(
            journey_type=JourneyType.RETURN,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[],  # Empty!
            pricing=FarePricing(
                has_mixed_booking_classes=False,
                fare_source_code="IN_EMPTY",
                fare_type=FareType.PUBLIC,
                is_refundable=True,
                fare_totals=FareTotals(
                    base_fare=MoneyAmount(
                        amount=Decimal("100.00"), currency="USD", decimal_places=2
                    ),
                    equivalent_fare=MoneyAmount(
                        amount=Decimal("100.00"), currency="USD", decimal_places=2
                    ),
                    service_tax=MoneyAmount(
                        amount=Decimal("0.00"), currency="USD", decimal_places=2
                    ),
                    total_tax=MoneyAmount(
                        amount=Decimal("20.00"), currency="USD", decimal_places=2
                    ),
                    total_fare=MoneyAmount(
                        amount=Decimal("200.00"), currency="USD", decimal_places=2
                    ),
                ),
                passenger_fare_breakdown=[],
            ),
        )

        valid_inbound = create_mock_fare_itinerary(
            "CDG", "LHR", JourneyType.RETURN, "IN_VALID"
        )

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=outbound_flights,
            inbound_fare_itineraries=[inbound_with_empty_legs, valid_inbound],
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only valid inbound flight should be kept
            assert len(result.inbound_fare_itineraries) == 1
            assert (
                result.inbound_fare_itineraries[0].pricing.fare_source_code
                == "IN_VALID"
            )

    @pytest.mark.asyncio
    async def test_round_trip_empty_inbound_segments_filtered_out(
        self, flight_service: FlightService
    ):
        """Test that inbound flights with empty flight_segments are filtered out."""
        out_date = datetime.now(UTC).date()
        request = FlightSearchRequest(
            journey_type=JourneyType.RETURN,
            origin_destination_info=[
                OriginDestinationSegment(
                    departure_date=out_date,
                    origin_airport=create_mock_airport("LHR"),
                    destination_airport=create_mock_airport("CDG"),
                ),
                OriginDestinationSegment(
                    departure_date=out_date,
                    origin_airport=create_mock_airport("CDG"),
                    destination_airport=create_mock_airport("LHR"),
                ),
            ],
            cabin_class=CabinClass.ECONOMY,
            adults=1,
            children=0,
            infants=0,
            required_currency_code="USD",
            city_wise_search_origin=False,
            city_wise_search_destination=False,
        )

        outbound_flights = [
            create_mock_fare_itinerary("LHR", "CDG", JourneyType.RETURN, "OUT_1"),
        ]

        # Create inbound flight with empty flight_segments
        leg_with_empty_segments = create_mock_leg([])
        inbound_with_empty_segments = FareItinerary(
            journey_type=JourneyType.RETURN,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[leg_with_empty_segments],
            pricing=FarePricing(
                has_mixed_booking_classes=False,
                fare_source_code="IN_EMPTY_SEG",
                fare_type=FareType.PUBLIC,
                is_refundable=True,
                fare_totals=FareTotals(
                    base_fare=MoneyAmount(
                        amount=Decimal("100.00"), currency="USD", decimal_places=2
                    ),
                    equivalent_fare=MoneyAmount(
                        amount=Decimal("100.00"), currency="USD", decimal_places=2
                    ),
                    service_tax=MoneyAmount(
                        amount=Decimal("0.00"), currency="USD", decimal_places=2
                    ),
                    total_tax=MoneyAmount(
                        amount=Decimal("20.00"), currency="USD", decimal_places=2
                    ),
                    total_fare=MoneyAmount(
                        amount=Decimal("200.00"), currency="USD", decimal_places=2
                    ),
                ),
                passenger_fare_breakdown=[],
            ),
        )

        valid_inbound = create_mock_fare_itinerary(
            "CDG", "LHR", JourneyType.RETURN, "IN_VALID"
        )

        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=outbound_flights,
            inbound_fare_itineraries=[inbound_with_empty_segments, valid_inbound],
        )

        with (
            patch.object(
                flight_service.client, "search_flights", new_callable=AsyncMock
            ) as mock_search,
            patch.object(
                flight_service,
                "get_airline_list",
                new_callable=AsyncMock,
                return_value=AirlineListResponse(airlines=[]),
            ),
        ):
            mock_search.return_value = response

            result = await flight_service.search_flights(request)

            # Only valid inbound flight should be kept
            assert len(result.inbound_fare_itineraries) == 1
            assert (
                result.inbound_fare_itineraries[0].pricing.fare_source_code
                == "IN_VALID"
            )
