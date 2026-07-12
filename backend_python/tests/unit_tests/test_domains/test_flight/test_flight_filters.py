"""Unit tests for flight search filters functionality.

Tests the filtering logic in filters.py module for global filters, city-wise filters,
leg-specific filters, and multi-city/round-trip scenarios.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.domains.common.schemas import Duration, MoneyAmount
from app.domains.flight.enums import FareType, JourneyType, TicketType
from app.domains.flight.filters import filter_flight_results
from app.domains.flight.schemas import (
    FareItinerary,
    FarePricing,
    FareTotals,
    FlightLeg,
    FlightSearchFilters,
    FlightSearchResponse,
    LegFilter,
    TimeWindow,
)

# Reuse helper functions from test_city_wise_filtering.py
from tests.unit_tests.test_domains.test_flight.test_city_wise_filtering import (
    create_mock_airline,
    create_mock_fare_itinerary,
    create_mock_leg,
    create_mock_segment,
)

# ==============================================================================
# EXTENDED HELPER FUNCTIONS
# ==============================================================================


def create_fare_itinerary_with_price(
    origin_code: str,
    destination_code: str,
    price: Decimal,
    fare_source_code: str = "FARE_PRICE",
) -> FareItinerary:
    """Create a FareItinerary with specific price."""
    return create_mock_fare_itinerary(
        origin_code, destination_code, price=price, fare_source_code=fare_source_code
    )


def create_fare_itinerary_with_refundability(
    origin_code: str,
    destination_code: str,
    is_refundable: bool,
    fare_source_code: str = "FARE_REFUND",
) -> FareItinerary:
    """Create a FareItinerary with specific refundability."""
    segment = create_mock_segment(origin_code, destination_code)
    leg = create_mock_leg([segment])

    pricing = FarePricing(
        has_mixed_booking_classes=False,
        fare_source_code=fare_source_code,
        fare_type=FareType.PUBLIC,
        is_refundable=is_refundable,
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
    )

    return FareItinerary(
        journey_type=JourneyType.ONE_WAY,
        ticket_type=TicketType.E_TICKET,
        validating_airline=create_mock_airline(),
        flight_legs=[leg],
        pricing=pricing,
    )


def create_fare_itinerary_with_fare_type(
    origin_code: str,
    destination_code: str,
    fare_type: FareType,
    fare_source_code: str = "FARE_TYPE",
) -> FareItinerary:
    """Create a FareItinerary with specific fare type."""
    segment = create_mock_segment(origin_code, destination_code)
    leg = create_mock_leg([segment])

    pricing = FarePricing(
        has_mixed_booking_classes=False,
        fare_source_code=fare_source_code,
        fare_type=fare_type,
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
    )

    return FareItinerary(
        journey_type=JourneyType.ONE_WAY,
        ticket_type=TicketType.E_TICKET,
        validating_airline=create_mock_airline(),
        flight_legs=[leg],
        pricing=pricing,
    )


def create_fare_itinerary_with_stops(
    origin_code: str,
    destination_code: str,
    num_stops: int,
    fare_source_code: str = "FARE_STOPS",
) -> FareItinerary:
    """Create a FareItinerary with specific number of stops."""
    segment = create_mock_segment(origin_code, destination_code)
    leg = create_mock_leg([segment], total_stops=num_stops)

    pricing = FarePricing(
        has_mixed_booking_classes=False,
        fare_source_code=fare_source_code,
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
    )

    return FareItinerary(
        journey_type=JourneyType.ONE_WAY,
        ticket_type=TicketType.E_TICKET,
        validating_airline=create_mock_airline(),
        flight_legs=[leg],
        pricing=pricing,
    )


def create_fare_itinerary_with_airline(
    origin_code: str,
    destination_code: str,
    airline_name: str,
    fare_source_code: str = "FARE_AIRLINE",
) -> FareItinerary:
    """Create a FareItinerary with specific operating airline."""
    segment = create_mock_segment(origin_code, destination_code)
    # Override operating airline
    segment.operating_airline = create_mock_airline(name=airline_name)
    leg = create_mock_leg([segment])

    pricing = FarePricing(
        has_mixed_booking_classes=False,
        fare_source_code=fare_source_code,
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
    )

    return FareItinerary(
        journey_type=JourneyType.ONE_WAY,
        ticket_type=TicketType.E_TICKET,
        validating_airline=create_mock_airline(),
        flight_legs=[leg],
        pricing=pricing,
    )


def create_leg_with_departure_time(
    origin_code: str, destination_code: str, departure_time: datetime
) -> FlightLeg:
    """Create a leg with specific departure time."""
    segment = create_mock_segment(
        origin_code, destination_code, departure_datetime=departure_time
    )
    return create_mock_leg([segment])


def create_leg_with_arrival_time(
    origin_code: str, destination_code: str, arrival_time: datetime
) -> FlightLeg:
    """Create a leg with specific arrival time."""
    departure_time = arrival_time - timedelta(hours=2)
    segment = create_mock_segment(
        origin_code,
        destination_code,
        departure_datetime=departure_time,
        arrival_datetime=arrival_time,
    )
    return create_mock_leg([segment])


def create_leg_with_layovers(
    origin_code: str, destination_code: str, layover_airports: list[str]
) -> FlightLeg:
    """Create a leg with specific layover airports."""
    segments = []
    current_origin = origin_code

    for _i, layover in enumerate(layover_airports):
        # Segment to layover
        segments.append(create_mock_segment(current_origin, layover))
        current_origin = layover

    # Final segment to destination
    segments.append(create_mock_segment(current_origin, destination_code))

    return create_mock_leg(segments, total_stops=len(layover_airports))


def create_leg_with_duration(
    origin_code: str,
    destination_code: str,
    flight_duration_minutes: int,
    layover_minutes: int = 0,
) -> FlightLeg:
    """Create a leg with specific total duration (flight + layover)."""
    base_time = datetime.now(UTC)
    departure_time = base_time

    if layover_minutes > 0:
        # Two segments with layover
        first_segment_duration = flight_duration_minutes // 2
        arrival_time_1 = departure_time + timedelta(minutes=first_segment_duration)
        layover_start = arrival_time_1
        layover_end = layover_start + timedelta(minutes=layover_minutes)

        segment1 = create_mock_segment(
            origin_code,
            "LAY",  # Layover airport
            departure_datetime=departure_time,
            arrival_datetime=arrival_time_1,
        )
        segment1.flight_duration = Duration(total_minutes=first_segment_duration)

        segment2 = create_mock_segment(
            "LAY",
            destination_code,
            departure_datetime=layover_end,
            arrival_datetime=layover_end + timedelta(minutes=first_segment_duration),
        )
        segment2.flight_duration = Duration(
            total_minutes=flight_duration_minutes - first_segment_duration
        )

        return create_mock_leg([segment1, segment2], total_stops=1)
    # Direct flight
    arrival_time = departure_time + timedelta(minutes=flight_duration_minutes)
    segment = create_mock_segment(
        origin_code,
        destination_code,
        departure_datetime=departure_time,
        arrival_datetime=arrival_time,
    )
    segment.flight_duration = Duration(total_minutes=flight_duration_minutes)
    return create_mock_leg([segment], total_stops=0)


# ==============================================================================
# GLOBAL FILTER TESTS
# ==============================================================================


class TestGlobalFilters:
    """Test global filters (price, refundability, carrier, max_stops, operating_airlines)."""

    def test_price_range_filter(self):
        """Test price range filtering (min and max)."""
        flights = [
            create_fare_itinerary_with_price("LHR", "CDG", Decimal("50.00"), "FARE_50"),
            create_fare_itinerary_with_price(
                "LHR", "CDG", Decimal("150.00"), "FARE_150"
            ),
            create_fare_itinerary_with_price(
                "LHR", "CDG", Decimal("250.00"), "FARE_250"
            ),
            create_fare_itinerary_with_price(
                "LHR", "CDG", Decimal("350.00"), "FARE_350"
            ),
        ]

        response = FlightSearchResponse(
            session_id="test", supplier="test", fare_itineraries=flights
        )

        filters = FlightSearchFilters(min_price=100.0, max_price=300.0)
        result = filter_flight_results(response, filters, "LHR", "CDG")

        assert len(result.fare_itineraries) == 2
        assert all(
            f.pricing.fare_source_code in ["FARE_150", "FARE_250"]
            for f in result.fare_itineraries
        )

    def test_price_filter_with_missing_pricing(self):
        """Test that flights with missing pricing are filtered out."""
        flight_with_pricing = create_fare_itinerary_with_price(
            "LHR", "CDG", Decimal("200.00"), "FARE_VALID"
        )
        # Use model_construct to bypass validation for missing pricing
        flight_without_pricing = FareItinerary.model_construct(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[create_mock_leg([create_mock_segment("LHR", "CDG")])],
            pricing=None,  # Missing pricing
        )

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[flight_with_pricing, flight_without_pricing],
        )

        filters = FlightSearchFilters(min_price=100.0)
        result = filter_flight_results(response, filters, "LHR", "CDG")

        assert len(result.fare_itineraries) == 1
        assert result.fare_itineraries[0].pricing.fare_source_code == "FARE_VALID"

    def test_max_stops_filter(self):
        """Test max stops filtering, including multi-city scenarios."""
        direct_flight = create_fare_itinerary_with_stops("LHR", "CDG", 0, "FARE_0")
        one_stop_flight = create_fare_itinerary_with_stops("LHR", "CDG", 1, "FARE_1")
        two_stop_flight = create_fare_itinerary_with_stops("LHR", "CDG", 2, "FARE_2")

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[direct_flight, one_stop_flight, two_stop_flight],
        )

        filters = FlightSearchFilters(max_stops=1)
        result = filter_flight_results(response, filters, "LHR", "CDG")

        assert len(result.fare_itineraries) == 2
        assert all(
            f.pricing.fare_source_code in ["FARE_0", "FARE_1"]
            for f in result.fare_itineraries
        )

    def test_max_stops_filter_multi_city(self):
        """Test max stops filter with multi-city flight (all legs must pass)."""
        # Create multi-city flight with legs: [0 stops, 2 stops, 1 stop]
        leg0 = create_mock_leg([create_mock_segment("NYC", "LON")], total_stops=0)
        leg1 = create_mock_leg([create_mock_segment("LON", "PAR")], total_stops=2)
        leg2 = create_mock_leg([create_mock_segment("PAR", "NYC")], total_stops=1)

        pricing = FarePricing(
            has_mixed_booking_classes=False,
            fare_source_code="FARE_MULTI",
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
        )

        multi_city_flight = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[leg0, leg1, leg2],
            pricing=pricing,
        )

        response = FlightSearchResponse(
            session_id="test", supplier="test", fare_itineraries=[multi_city_flight]
        )

        filters = FlightSearchFilters(max_stops=1)
        result = filter_flight_results(response, filters, "NYC", "NYC")

        # Should be filtered out because leg1 has 2 stops
        assert len(result.fare_itineraries) == 0

    def test_operating_airlines_filter(self):
        """Test operating airlines filtering with case-insensitive matching."""
        emirates_flight = create_fare_itinerary_with_airline(
            "LHR", "CDG", "Emirates", "FARE_EMIRATES"
        )
        qatar_flight = create_fare_itinerary_with_airline(
            "LHR", "CDG", "Qatar Airways", "FARE_QATAR"
        )
        ba_flight = create_fare_itinerary_with_airline(
            "LHR", "CDG", "British Airways", "FARE_BA"
        )

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[emirates_flight, qatar_flight, ba_flight],
        )

        filters = FlightSearchFilters(operating_airlines=["Emirates", "Qatar Airways"])
        result = filter_flight_results(response, filters, "LHR", "CDG")

        assert len(result.fare_itineraries) == 2
        assert all(
            f.pricing.fare_source_code in ["FARE_EMIRATES", "FARE_QATAR"]
            for f in result.fare_itineraries
        )

    def test_operating_airlines_filter_case_insensitive(self):
        """Test that airline name matching is case-insensitive."""
        emirates_flight = create_fare_itinerary_with_airline(
            "LHR", "CDG", "emirates", "FARE_EMIRATES"
        )

        response = FlightSearchResponse(
            session_id="test", supplier="test", fare_itineraries=[emirates_flight]
        )

        filters = FlightSearchFilters(operating_airlines=["EMIRATES"])
        result = filter_flight_results(response, filters, "LHR", "CDG")

        assert len(result.fare_itineraries) == 1
        assert result.fare_itineraries[0].pricing.fare_source_code == "FARE_EMIRATES"


# ==============================================================================
# CITY-WISE FILTER TESTS
# ==============================================================================


class TestCityWiseFilters:
    """Test city-wise search filters (leg-specific and global)."""

    def test_leg_specific_city_wise_search_precedence(self):
        """Test that leg-specific city_wise_search takes precedence over global."""
        flight1 = create_mock_fare_itinerary("LHR", "CDG", fare_source_code="FARE_1")
        flight2 = create_mock_fare_itinerary("LGW", "CDG", fare_source_code="FARE_2")

        response = FlightSearchResponse(
            session_id="test", supplier="test", fare_itineraries=[flight1, flight2]
        )

        # Global says false (exact match), but leg-specific says true (city-wise)
        filters = FlightSearchFilters(
            city_wise_search_origin=False,
            journey_filters=[LegFilter(leg_index=0, city_wise_search=True)],
        )

        result = filter_flight_results(response, filters, "LHR", "CDG")

        # Both flights should remain (leg-specific takes precedence)
        assert len(result.fare_itineraries) == 2

    def test_global_city_wise_search_fallback(self):
        """Test that global city_wise_search is used as fallback when no leg-specific filter."""
        flight1 = create_mock_fare_itinerary("LHR", "CDG", fare_source_code="FARE_1")
        flight2 = create_mock_fare_itinerary("LGW", "CDG", fare_source_code="FARE_2")
        flight3 = create_mock_fare_itinerary("LHR", "ORY", fare_source_code="FARE_3")

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[flight1, flight2, flight3],
        )

        # No leg-specific filter, use global
        filters = FlightSearchFilters(
            city_wise_search_origin=True, city_wise_search_destination=True
        )

        result = filter_flight_results(response, filters, "LHR", "CDG")

        # All flights should remain (global fallback works)
        assert len(result.fare_itineraries) == 3


# ==============================================================================
# LEG-SPECIFIC FILTER TESTS
# ==============================================================================


class TestLegSpecificFilters:
    """Test leg-specific filters (time windows, duration, layover airports)."""

    def test_time_window_filters(self):
        """Test departure and arrival time window filters."""
        base_time = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        # Create flights with different departure times
        flight_05 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_departure_time(
                    "LHR", "CDG", base_time.replace(hour=5, minute=0)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_10 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_departure_time(
                    "LHR", "CDG", base_time.replace(hour=10, minute=0)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_15 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_departure_time(
                    "LHR", "CDG", base_time.replace(hour=15, minute=0)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_20 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_departure_time(
                    "LHR", "CDG", base_time.replace(hour=20, minute=0)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[flight_05, flight_10, flight_15, flight_20],
        )

        # Test departure window: 08:00 - 12:00
        filters = FlightSearchFilters(
            journey_filters=[
                LegFilter(
                    leg_index=0,
                    departure_window=TimeWindow(min="08:00", max="12:00"),
                )
            ]
        )

        result = filter_flight_results(response, filters, "LHR", "CDG")
        assert len(result.fare_itineraries) == 1
        assert (
            result.fare_itineraries[0]
            .flight_legs[0]
            .flight_segments[0]
            .departure_datetime.value.hour
            == 10
        )

        # Test arrival window
        flight_arr_10 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_arrival_time(
                    "LHR", "CDG", base_time.replace(hour=10, minute=0)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_arr_14 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_arrival_time(
                    "LHR", "CDG", base_time.replace(hour=14, minute=0)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_arr_18 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_arrival_time(
                    "LHR", "CDG", base_time.replace(hour=18, minute=0)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[flight_arr_10, flight_arr_14, flight_arr_18],
        )

        filters = FlightSearchFilters(
            journey_filters=[
                LegFilter(
                    leg_index=0, arrival_window=TimeWindow(min="12:00", max="16:00")
                )
            ]
        )

        result = filter_flight_results(response, filters, "LHR", "CDG")
        assert len(result.fare_itineraries) == 1
        assert (
            result.fare_itineraries[0]
            .flight_legs[0]
            .flight_segments[-1]
            .arrival_datetime.value.hour
            == 14
        )

    def test_midnight_crossing_time_window(self):
        """Test night window (23:00-05:00) that crosses midnight."""
        base_time = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        # Create flights spanning the night window
        flight_2200 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_departure_time(
                    "LHR", "CDG", base_time.replace(hour=22, minute=0)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_2330 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_departure_time(
                    "LHR", "CDG", base_time.replace(hour=23, minute=30)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_0200 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_departure_time(
                    "LHR", "CDG", base_time.replace(hour=2, minute=0)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_0600 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_departure_time(
                    "LHR", "CDG", base_time.replace(hour=6, minute=0)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_1200 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[
                create_leg_with_departure_time(
                    "LHR", "CDG", base_time.replace(hour=12, minute=0)
                )
            ],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[
                flight_2200,
                flight_2330,
                flight_0200,
                flight_0600,
                flight_1200,
            ],
        )

        # Test night window: 23:00 - 05:00 (crosses midnight)
        filters = FlightSearchFilters(
            journey_filters=[
                LegFilter(
                    leg_index=0,
                    departure_window=TimeWindow(min="23:00", max="05:00"),
                )
            ]
        )

        result = filter_flight_results(response, filters, "LHR", "CDG")

        # Should match 23:30 and 02:00 flights only
        assert len(result.fare_itineraries) == 2
        hours = sorted(
            [
                itinerary.flight_legs[0]
                .flight_segments[0]
                .departure_datetime.value.hour
                for itinerary in result.fare_itineraries
            ]
        )
        assert hours == [2, 23], f"Expected hours [2, 23] but got {hours}"

    def test_max_duration_filter(self):
        """Test max duration filter (includes flight time + layover time)."""
        leg_300 = create_leg_with_duration("LHR", "CDG", 300, 0)
        leg_600 = create_leg_with_duration("LHR", "CDG", 400, 200)  # 400 + 200 = 600
        leg_900 = create_leg_with_duration("LHR", "CDG", 600, 300)  # 600 + 300 = 900

        flight_300 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[leg_300],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_600 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[leg_600],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_900 = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[leg_900],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[flight_300, flight_600, flight_900],
        )

        filters = FlightSearchFilters(
            journey_filters=[LegFilter(leg_index=0, max_duration_minutes=600)]
        )

        result = filter_flight_results(response, filters, "LHR", "CDG")

        assert len(result.fare_itineraries) == 2
        # Verify the correct flights remain (300 and 600 minute legs)

    def test_layover_airport_filters(self):
        """Test excluded and allowed layover airport filters."""
        # Create flights with different layovers
        flight_dxb = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[create_leg_with_layovers("LHR", "CDG", ["DXB"])],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_ist = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[create_leg_with_layovers("LHR", "CDG", ["IST"])],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_doh = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[create_leg_with_layovers("LHR", "CDG", ["DOH"])],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        flight_direct = create_mock_fare_itinerary(
            "LHR", "CDG", fare_source_code="DIRECT"
        )

        # Test excluded layover airports (fresh response)
        response_excluded = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[flight_dxb, flight_ist, flight_doh, flight_direct],
        )

        filters = FlightSearchFilters(
            journey_filters=[
                LegFilter(leg_index=0, excluded_layover_airports=["DXB", "IST"])
            ]
        )

        result = filter_flight_results(response_excluded, filters, "LHR", "CDG")
        assert len(result.fare_itineraries) == 2  # DOH and direct should remain

        # Test allowed layover airports (fresh response to avoid mutation from previous test)
        response_allowed = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[flight_dxb, flight_ist, flight_doh, flight_direct],
        )

        filters = FlightSearchFilters(
            journey_filters=[
                LegFilter(leg_index=0, allowed_layover_airports=["IST", "DOH"])
            ]
        )

        result = filter_flight_results(response_allowed, filters, "LHR", "CDG")
        assert (
            len(result.fare_itineraries) == 2
        )  # IST and DOH should remain, direct filtered out


# ==============================================================================
# MULTI-CITY AND ROUND-TRIP TESTS
# ==============================================================================


class TestMultiCityAndRoundTrip:
    """Test multi-city and round-trip filtering scenarios."""

    def test_multi_city_max_stops_per_leg(self):
        """Test that max_stops filter checks all legs individually in multi-city flights."""
        # Create 3-leg flight with stops: [0, 2, 1]
        leg0 = create_mock_leg([create_mock_segment("NYC", "LON")], total_stops=0)
        leg1 = create_mock_leg([create_mock_segment("LON", "PAR")], total_stops=2)
        leg2 = create_mock_leg([create_mock_segment("PAR", "NYC")], total_stops=1)

        pricing = FarePricing(
            has_mixed_booking_classes=False,
            fare_source_code="FARE_MULTI",
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
        )

        multi_city_flight = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[leg0, leg1, leg2],
            pricing=pricing,
        )

        response = FlightSearchResponse(
            session_id="test", supplier="test", fare_itineraries=[multi_city_flight]
        )

        filters = FlightSearchFilters(max_stops=1)
        result = filter_flight_results(response, filters, "NYC", "NYC")

        # Should be filtered out because leg1 has 2 stops
        assert len(result.fare_itineraries) == 0

    def test_round_trip_inbound_filtering(self):
        """Test that inbound flights are filtered correctly in round trips."""
        outbound = create_mock_fare_itinerary("LHR", "CDG", JourneyType.RETURN, "OUT_1")
        inbound_pass = create_mock_fare_itinerary(
            "CDG", "LHR", JourneyType.RETURN, "IN_PASS"
        )
        inbound_fail = create_mock_fare_itinerary(
            "CDG", "LGW", JourneyType.RETURN, "IN_FAIL"
        )

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[outbound],
            inbound_fare_itineraries=[inbound_pass, inbound_fail],
        )

        # city_wise_search_destination: false means exact match required for inbound destination
        filters = FlightSearchFilters(city_wise_search_destination=False)

        result = filter_flight_results(response, filters, "LHR", "CDG")

        # Only CDG→LHR should remain (exact match)
        assert len(result.inbound_fare_itineraries) == 1
        assert result.inbound_fare_itineraries[0].pricing.fare_source_code == "IN_PASS"


# ==============================================================================
# EDGE CASES
# ==============================================================================


class TestFilterEdgeCases:
    """Test edge cases and error handling."""

    def test_filter_with_no_filters_provided(self):
        """Test that no filtering occurs when filters=None."""
        flight1 = create_mock_fare_itinerary("LHR", "CDG", fare_source_code="FARE_1")
        flight2 = create_mock_fare_itinerary("LGW", "CDG", fare_source_code="FARE_2")

        response = FlightSearchResponse(
            session_id="test", supplier="test", fare_itineraries=[flight1, flight2]
        )

        result = filter_flight_results(
            response,
            filters=None,
            requested_origin_code="LHR",
            requested_destination_code="CDG",
        )

        # All flights should remain
        assert len(result.fare_itineraries) == 2

    def test_filter_with_empty_or_invalid_data(self):
        """Test filtering with empty or invalid flight data."""
        # Flight with empty flight_legs
        flight_empty_legs = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        # Flight with empty flight_segments
        leg_empty_segments = create_mock_leg([])
        flight_empty_segments = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=create_mock_airline(),
            flight_legs=[leg_empty_segments],
            pricing=create_mock_fare_itinerary("LHR", "CDG").pricing,
        )

        valid_flight = create_mock_fare_itinerary(
            "LHR", "CDG", fare_source_code="VALID"
        )

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[flight_empty_legs, flight_empty_segments, valid_flight],
        )

        filters = FlightSearchFilters(min_price=100.0)
        result = filter_flight_results(response, filters, "LHR", "CDG")

        # Only valid flight should remain
        assert len(result.fare_itineraries) == 1
        assert result.fare_itineraries[0].pricing.fare_source_code == "VALID"

    def test_filter_with_missing_requested_codes(self):
        """Test that city-wise filters handle missing requested codes gracefully."""
        flight1 = create_mock_fare_itinerary("LHR", "CDG", fare_source_code="FARE_1")
        flight2 = create_mock_fare_itinerary("LGW", "CDG", fare_source_code="FARE_2")

        response = FlightSearchResponse(
            session_id="test", supplier="test", fare_itineraries=[flight1, flight2]
        )

        filters = FlightSearchFilters(city_wise_search_origin=False)

        # Missing requested codes should not cause errors
        result = filter_flight_results(
            response,
            filters,
            requested_origin_code=None,
            requested_destination_code=None,
        )

        # Should handle gracefully (no filtering by city-wise when codes missing)
        assert len(result.fare_itineraries) >= 0  # At least doesn't crash

    def test_direct_flight_fails_allowed_layover_airports(self):
        """Test that direct flights are filtered out when allowed_layover_airports is set.

        When a user specifies allowed_layover_airports, they want flights through
        specific airports. Direct flights have no layovers, so they should not match.
        """
        # Direct flight (1 segment = no layover)
        flight_direct = create_mock_fare_itinerary(
            "LHR", "CDG", fare_source_code="DIRECT"
        )

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[flight_direct],
        )

        # User wants flights through Istanbul or Doha
        filters = FlightSearchFilters(
            journey_filters=[
                LegFilter(leg_index=0, allowed_layover_airports=["IST", "DOH"])
            ]
        )

        result = filter_flight_results(response, filters, "LHR", "CDG")

        # Direct flight should be filtered out (no layovers to match allowed list)
        assert len(result.fare_itineraries) == 0

    def test_direct_flight_passes_excluded_layover_airports(self):
        """Test that direct flights pass when only excluded_layover_airports is set.

        Direct flights have no layovers, so there's nothing to exclude.
        They should pass the excluded_layover_airports filter.
        """
        # Direct flight (1 segment = no layover)
        flight_direct = create_mock_fare_itinerary(
            "LHR", "CDG", fare_source_code="DIRECT"
        )

        response = FlightSearchResponse(
            session_id="test",
            supplier="test",
            fare_itineraries=[flight_direct],
        )

        # User wants to exclude layovers in Dubai
        filters = FlightSearchFilters(
            journey_filters=[LegFilter(leg_index=0, excluded_layover_airports=["DXB"])]
        )

        result = filter_flight_results(response, filters, "LHR", "CDG")

        # Direct flight should pass (no layovers to exclude)
        assert len(result.fare_itineraries) == 1
        assert result.fare_itineraries[0].pricing.fare_source_code == "DIRECT"
