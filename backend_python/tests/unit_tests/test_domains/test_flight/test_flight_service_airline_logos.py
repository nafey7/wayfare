"""Unit tests for airline logo enrichment in FlightService.

Tests _enrich_airline_logos and related behavior for marketing_airline,
operating_airline, and codeshare scenarios.
"""

from decimal import Decimal

from app.domains.common.schemas import DateTime, Duration, MoneyAmount
from app.domains.flight.enums import CabinClass, FareType, JourneyType, TicketType
from app.domains.flight.schemas import (
    AirlineInfo,
    AirportInfo,
    FareItinerary,
    FarePricing,
    FareTotals,
    FlightLeg,
    FlightNumber,
    FlightSearchResponse,
    FlightSegment,
    SeatAvailability,
)
from app.domains.flight.service import FlightService


def _create_airport(iata: str) -> AirportInfo:
    return AirportInfo(iata_code=iata)


def _create_airline(iata: str, name: str, logo_url: str | None = None) -> AirlineInfo:
    return AirlineInfo(
        iata_code=iata,
        airline_name=name,
        logo_url=logo_url,
    )


def _create_segment(
    origin: str,
    dest: str,
    marketing: AirlineInfo,
    operating: AirlineInfo | None = None,
) -> FlightSegment:
    from datetime import UTC, datetime, timedelta

    dep = datetime.now(UTC)
    arr = dep + timedelta(hours=2)
    op = operating or marketing
    return FlightSegment(
        arrival_airport=_create_airport(dest),
        arrival_datetime=DateTime(value=arr),
        departure_airport=_create_airport(origin),
        departure_datetime=DateTime(value=dep),
        cabin_class=CabinClass.ECONOMY,
        e_ticket=True,
        flight_duration=Duration(total_minutes=120),
        marketing_flight_number=FlightNumber(
            airline_prefix=marketing.iata_code,
            flight_number="123",
            formatted_number="123",
        ),
        marketing_airline=marketing,
        operating_airline=op,
        operating_flight_number=FlightNumber(
            airline_prefix=op.iata_code, flight_number="123", formatted_number="123"
        ),
        segment_stops=0,
        seat_availability=SeatAvailability(available_seats=9, is_limited=False),
    )


class TestEnrichAirlineLogos:
    """Tests for _enrich_airline_logos."""

    def test_logo_applied_to_marketing_airline_when_in_list(self) -> None:
        """Logo is set on marketing_airline when airline code is in code_to_logo."""
        ba = _create_airline("BA", "British Airways", logo_url=None)
        seg = _create_segment("LHR", "JFK", marketing=ba)
        leg = FlightLeg(total_stops=0, flight_segments=[seg])
        pricing = FarePricing(
            has_mixed_booking_classes=False,
            fare_source_code="X",
            fare_type=FareType.PUBLIC,
            is_refundable=True,
            fare_totals=FareTotals(
                base_fare=MoneyAmount(
                    amount=Decimal("100"), currency="USD", decimal_places=2
                ),
                equivalent_fare=MoneyAmount(
                    amount=Decimal("100"), currency="USD", decimal_places=2
                ),
                service_tax=MoneyAmount(
                    amount=Decimal("0"), currency="USD", decimal_places=2
                ),
                total_tax=MoneyAmount(
                    amount=Decimal("20"), currency="USD", decimal_places=2
                ),
                total_fare=MoneyAmount(
                    amount=Decimal("150"), currency="USD", decimal_places=2
                ),
            ),
            passenger_fare_breakdown=[],
        )
        itinerary = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=ba,
            flight_legs=[leg],
            pricing=pricing,
        )
        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=[itinerary],
        )

        code_to_logo = {"BA": "https://example.com/ba.gif"}
        svc = FlightService(current_user=None)
        svc._enrich_airline_logos(response, code_to_logo)

        assert (
            response.fare_itineraries[0]
            .flight_legs[0]
            .flight_segments[0]
            .marketing_airline
        )
        assert (
            response.fare_itineraries[0]
            .flight_legs[0]
            .flight_segments[0]
            .marketing_airline.logo_url
            == "https://example.com/ba.gif"
        )

    def test_logo_applied_to_operating_airline_when_in_list(self) -> None:
        """Logo is set on operating_airline when airline code is in code_to_logo."""
        kl = _create_airline("KL", "KLM", logo_url=None)
        seg = _create_segment("AMS", "BCN", marketing=kl)
        leg = FlightLeg(total_stops=0, flight_segments=[seg])
        pricing = FarePricing(
            has_mixed_booking_classes=False,
            fare_source_code="X",
            fare_type=FareType.PUBLIC,
            is_refundable=True,
            fare_totals=FareTotals(
                base_fare=MoneyAmount(
                    amount=Decimal("100"), currency="USD", decimal_places=2
                ),
                equivalent_fare=MoneyAmount(
                    amount=Decimal("100"), currency="USD", decimal_places=2
                ),
                service_tax=MoneyAmount(
                    amount=Decimal("0"), currency="USD", decimal_places=2
                ),
                total_tax=MoneyAmount(
                    amount=Decimal("20"), currency="USD", decimal_places=2
                ),
                total_fare=MoneyAmount(
                    amount=Decimal("150"), currency="USD", decimal_places=2
                ),
            ),
            passenger_fare_breakdown=[],
        )
        itinerary = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=kl,
            flight_legs=[leg],
            pricing=pricing,
        )
        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=[itinerary],
        )

        code_to_logo = {"KL": "https://example.com/kl.gif"}
        svc = FlightService(current_user=None)
        svc._enrich_airline_logos(response, code_to_logo)

        assert (
            response.fare_itineraries[0]
            .flight_legs[0]
            .flight_segments[0]
            .operating_airline
        )
        assert (
            response.fare_itineraries[0]
            .flight_legs[0]
            .flight_segments[0]
            .operating_airline.logo_url
            == "https://example.com/kl.gif"
        )

    def test_codeshare_marketing_and_operating_both_enriched_when_different(
        self,
    ) -> None:
        """When marketing and operating differ (codeshare), both get logos."""
        ba = _create_airline("BA", "British Airways", logo_url=None)
        aa = _create_airline("AA", "American Airlines", logo_url=None)
        seg = _create_segment("LHR", "JFK", marketing=ba, operating=aa)
        leg = FlightLeg(total_stops=0, flight_segments=[seg])
        pricing = FarePricing(
            has_mixed_booking_classes=False,
            fare_source_code="X",
            fare_type=FareType.PUBLIC,
            is_refundable=True,
            fare_totals=FareTotals(
                base_fare=MoneyAmount(
                    amount=Decimal("100"), currency="USD", decimal_places=2
                ),
                equivalent_fare=MoneyAmount(
                    amount=Decimal("100"), currency="USD", decimal_places=2
                ),
                service_tax=MoneyAmount(
                    amount=Decimal("0"), currency="USD", decimal_places=2
                ),
                total_tax=MoneyAmount(
                    amount=Decimal("20"), currency="USD", decimal_places=2
                ),
                total_fare=MoneyAmount(
                    amount=Decimal("150"), currency="USD", decimal_places=2
                ),
            ),
            passenger_fare_breakdown=[],
        )
        itinerary = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=ba,
            flight_legs=[leg],
            pricing=pricing,
        )
        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=[itinerary],
        )

        code_to_logo = {
            "BA": "https://example.com/ba.gif",
            "AA": "https://example.com/aa.gif",
        }
        svc = FlightService(current_user=None)
        svc._enrich_airline_logos(response, code_to_logo)

        seg0 = response.fare_itineraries[0].flight_legs[0].flight_segments[0]
        assert seg0.marketing_airline is not None
        assert seg0.marketing_airline.logo_url == "https://example.com/ba.gif"
        assert seg0.operating_airline is not None
        assert seg0.operating_airline.logo_url == "https://example.com/aa.gif"

    def test_airline_not_in_list_segment_unchanged(self) -> None:
        """When airline not in list, segment is unchanged (no error)."""
        ba = _create_airline("BA", "British Airways", logo_url=None)
        seg = _create_segment("LHR", "JFK", marketing=ba)
        leg = FlightLeg(total_stops=0, flight_segments=[seg])
        pricing = FarePricing(
            has_mixed_booking_classes=False,
            fare_source_code="X",
            fare_type=FareType.PUBLIC,
            is_refundable=True,
            fare_totals=FareTotals(
                base_fare=MoneyAmount(
                    amount=Decimal("100"), currency="USD", decimal_places=2
                ),
                equivalent_fare=MoneyAmount(
                    amount=Decimal("100"), currency="USD", decimal_places=2
                ),
                service_tax=MoneyAmount(
                    amount=Decimal("0"), currency="USD", decimal_places=2
                ),
                total_tax=MoneyAmount(
                    amount=Decimal("20"), currency="USD", decimal_places=2
                ),
                total_fare=MoneyAmount(
                    amount=Decimal("150"), currency="USD", decimal_places=2
                ),
            ),
            passenger_fare_breakdown=[],
        )
        itinerary = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=ba,
            flight_legs=[leg],
            pricing=pricing,
        )
        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=[itinerary],
        )

        code_to_logo = {"XX": "https://example.com/xx.gif"}
        svc = FlightService(current_user=None)
        svc._enrich_airline_logos(response, code_to_logo)

        assert (
            response.fare_itineraries[0]
            .flight_legs[0]
            .flight_segments[0]
            .marketing_airline
        )
        assert (
            response.fare_itineraries[0]
            .flight_legs[0]
            .flight_segments[0]
            .marketing_airline.logo_url
            is None
        )

    def test_empty_airline_list_no_logos_applied(self) -> None:
        """When code_to_logo is empty, no logos are applied."""
        ba = _create_airline("BA", "British Airways", logo_url=None)
        seg = _create_segment("LHR", "JFK", marketing=ba)
        leg = FlightLeg(total_stops=0, flight_segments=[seg])
        pricing = FarePricing(
            has_mixed_booking_classes=False,
            fare_source_code="X",
            fare_type=FareType.PUBLIC,
            is_refundable=True,
            fare_totals=FareTotals(
                base_fare=MoneyAmount(
                    amount=Decimal("100"), currency="USD", decimal_places=2
                ),
                equivalent_fare=MoneyAmount(
                    amount=Decimal("100"), currency="USD", decimal_places=2
                ),
                service_tax=MoneyAmount(
                    amount=Decimal("0"), currency="USD", decimal_places=2
                ),
                total_tax=MoneyAmount(
                    amount=Decimal("20"), currency="USD", decimal_places=2
                ),
                total_fare=MoneyAmount(
                    amount=Decimal("150"), currency="USD", decimal_places=2
                ),
            ),
            passenger_fare_breakdown=[],
        )
        itinerary = FareItinerary(
            journey_type=JourneyType.ONE_WAY,
            ticket_type=TicketType.E_TICKET,
            validating_airline=ba,
            flight_legs=[leg],
            pricing=pricing,
        )
        response = FlightSearchResponse(
            session_id="test_session",
            supplier="test",
            fare_itineraries=[itinerary],
        )

        svc = FlightService(current_user=None)
        svc._enrich_airline_logos(response, {})

        assert (
            response.fare_itineraries[0]
            .flight_legs[0]
            .flight_segments[0]
            .marketing_airline
        )
        assert (
            response.fare_itineraries[0]
            .flight_legs[0]
            .flight_segments[0]
            .marketing_airline.logo_url
            is None
        )
