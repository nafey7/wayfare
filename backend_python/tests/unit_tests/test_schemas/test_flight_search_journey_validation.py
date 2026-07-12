"""Tests for FlightSearchRequest journey_type vs origin_destination_info rules."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.domains.flight.enums import CabinClass, FlightAPIEnvironment, JourneyType
from app.domains.flight.schemas import (
    AirportInfo,
    FlightSearchRequest,
    OriginDestinationSegment,
)


def _base(**kwargs):
    d = datetime.now(UTC).date()
    defaults = {
        "user_id": "test_user",
        "user_password": "test_pass",  # pragma: allowlist secret
        "access": FlightAPIEnvironment.TEST,
        "journey_type": JourneyType.ONE_WAY,
        "origin_destination_info": [
            OriginDestinationSegment(
                departure_date=d,
                origin_airport=AirportInfo(iata_code="LHR"),
                destination_airport=AirportInfo(iata_code="CDG"),
            )
        ],
        "cabin_class": CabinClass.ECONOMY,
        "adults": 1,
        "children": 0,
        "infants": 0,
    }
    defaults.update(kwargs)
    return FlightSearchRequest(**defaults)


def test_one_way_requires_single_segment():
    d = datetime.now(UTC).date()
    with pytest.raises(ValidationError) as exc:
        FlightSearchRequest(
            user_id="test_user",
            user_password="test_pass",  # pragma: allowlist secret
            access=FlightAPIEnvironment.TEST,
            journey_type=JourneyType.ONE_WAY,
            origin_destination_info=[
                OriginDestinationSegment(
                    departure_date=d,
                    origin_airport=AirportInfo(iata_code="LHR"),
                    destination_airport=AirportInfo(iata_code="CDG"),
                ),
                OriginDestinationSegment(
                    departure_date=d + timedelta(days=7),
                    origin_airport=AirportInfo(iata_code="CDG"),
                    destination_airport=AirportInfo(iata_code="LHR"),
                ),
            ],
            cabin_class=CabinClass.ECONOMY,
            adults=1,
            children=0,
            infants=0,
        )
    assert "exactly one" in exc.value.errors()[0]["msg"].lower()


def test_return_requires_two_segments_round_trip_routing():
    d0 = datetime.now(UTC).date()
    d1 = d0 + timedelta(days=5)
    req = _base(
        journey_type=JourneyType.RETURN,
        origin_destination_info=[
            OriginDestinationSegment(
                departure_date=d0,
                origin_airport=AirportInfo(iata_code="LHR"),
                destination_airport=AirportInfo(iata_code="CDG"),
            ),
            OriginDestinationSegment(
                departure_date=d1,
                origin_airport=AirportInfo(iata_code="CDG"),
                destination_airport=AirportInfo(iata_code="LHR"),
            ),
        ],
    )
    assert len(req.origin_destination_info) == 2


def test_return_rejects_mismatched_second_leg():
    d0 = datetime.now(UTC).date()
    with pytest.raises(ValidationError) as exc:
        FlightSearchRequest(
            user_id="test_user",
            user_password="test_pass",  # pragma: allowlist secret
            access=FlightAPIEnvironment.TEST,
            journey_type=JourneyType.RETURN,
            origin_destination_info=[
                OriginDestinationSegment(
                    departure_date=d0,
                    origin_airport=AirportInfo(iata_code="LHR"),
                    destination_airport=AirportInfo(iata_code="CDG"),
                ),
                OriginDestinationSegment(
                    departure_date=d0,
                    origin_airport=AirportInfo(iata_code="ORY"),
                    destination_airport=AirportInfo(iata_code="LHR"),
                ),
            ],
            cabin_class=CabinClass.ECONOMY,
            adults=1,
            children=0,
            infants=0,
        )
    assert "round trip" in exc.value.errors()[0]["msg"].lower()


def test_circle_requires_two_plus_connecting_legs():
    d0 = datetime.now(UTC).date()
    req = _base(
        journey_type=JourneyType.CIRCLE,
        origin_destination_info=[
            OriginDestinationSegment(
                departure_date=d0,
                origin_airport=AirportInfo(iata_code="DEL"),
                destination_airport=AirportInfo(iata_code="BOM"),
            ),
            OriginDestinationSegment(
                departure_date=d0 + timedelta(days=2),
                origin_airport=AirportInfo(iata_code="BOM"),
                destination_airport=AirportInfo(iata_code="DXB"),
            ),
            OriginDestinationSegment(
                departure_date=d0 + timedelta(days=5),
                origin_airport=AirportInfo(iata_code="DXB"),
                destination_airport=AirportInfo(iata_code="DEL"),
            ),
        ],
    )
    assert len(req.origin_destination_info) == 3


def test_legacy_return_single_row_with_return_date_is_split():
    """Deprecated shape: one O&D row + return_date is coerced to two rows."""
    d0 = datetime.now(UTC).date()
    d1 = d0 + timedelta(days=7)
    req = FlightSearchRequest(
        user_id="test_user",
        user_password="test_pass",  # pragma: allowlist secret
        access=FlightAPIEnvironment.TEST,
        journey_type="Return",
        origin_destination_info=[
            OriginDestinationSegment(
                departure_date=d0,
                return_date=d1,
                origin_airport=AirportInfo(iata_code="LHR"),
                destination_airport=AirportInfo(iata_code="CDG"),
            )
        ],
        cabin_class=CabinClass.ECONOMY,
        adults=1,
        children=0,
        infants=0,
    )
    assert len(req.origin_destination_info) == 2
    assert req.origin_destination_info[0].return_date is None
    assert req.origin_destination_info[1].departure_date == d1
    assert req.origin_destination_info[1].origin_airport.iata_code.upper() == "CDG"
    assert req.origin_destination_info[1].destination_airport.iata_code.upper() == "LHR"


def test_roundtrip_alias_normalized_to_return():
    d0 = datetime.now(UTC).date()
    d1 = d0 + timedelta(days=5)
    req = FlightSearchRequest(
        user_id="test_user",
        user_password="test_pass",  # pragma: allowlist secret
        access=FlightAPIEnvironment.TEST,
        journey_type="RoundTrip",
        origin_destination_info=[
            OriginDestinationSegment(
                departure_date=d0,
                return_date=d1,
                origin_airport=AirportInfo(iata_code="LHR"),
                destination_airport=AirportInfo(iata_code="CDG"),
            )
        ],
        cabin_class=CabinClass.ECONOMY,
        adults=1,
        children=0,
        infants=0,
    )
    assert req.journey_type == JourneyType.RETURN
    assert len(req.origin_destination_info) == 2


def test_circle_rejects_broken_chain_legacy_mode(monkeypatch):
    """Connectivity rule applies only when parallel multicity is OFF (legacy
    Circle mode sends one request to FlightLogic, so legs must connect).
    """
    from app.core.config import settings

    monkeypatch.setattr(settings, "MULTICITY_PARALLEL_SEARCH", False)
    d0 = datetime.now(UTC).date()
    with pytest.raises(ValidationError) as exc:
        FlightSearchRequest(
            user_id="test_user",
            user_password="test_pass",  # pragma: allowlist secret
            access=FlightAPIEnvironment.TEST,
            journey_type=JourneyType.CIRCLE,
            origin_destination_info=[
                OriginDestinationSegment(
                    departure_date=d0,
                    origin_airport=AirportInfo(iata_code="DEL"),
                    destination_airport=AirportInfo(iata_code="BOM"),
                ),
                OriginDestinationSegment(
                    departure_date=d0 + timedelta(days=2),
                    origin_airport=AirportInfo(iata_code="DXB"),
                    destination_airport=AirportInfo(iata_code="DEL"),
                ),
            ],
            cabin_class=CabinClass.ECONOMY,
            adults=1,
            children=0,
            infants=0,
        )
    assert "connect" in exc.value.errors()[0]["msg"].lower()


def test_circle_allows_open_jaw_in_parallel_mode():
    """Open-jaw multi-city (e.g. fly into Palermo, fly out from Catania) is a
    legitimate itinerary and must NOT be rejected when MULTICITY_PARALLEL_SEARCH
    is on (default). Each leg runs as an independent OneWay search.
    """
    from app.core.config import settings

    assert settings.MULTICITY_PARALLEL_SEARCH is True, (
        "default expected — adjust test if default changes"
    )
    d0 = datetime.now(UTC).date()
    # DFW → PMO, CTA → VCE, VCE → DFW (PMO ≠ CTA — legitimate open-jaw)
    req = FlightSearchRequest(
        user_id="test_user",
        user_password="test_pass",  # pragma: allowlist secret
        access=FlightAPIEnvironment.TEST,
        journey_type=JourneyType.CIRCLE,
        origin_destination_info=[
            OriginDestinationSegment(
                departure_date=d0,
                origin_airport=AirportInfo(iata_code="DFW"),
                destination_airport=AirportInfo(iata_code="PMO"),
            ),
            OriginDestinationSegment(
                departure_date=d0 + timedelta(days=8),
                origin_airport=AirportInfo(iata_code="CTA"),
                destination_airport=AirportInfo(iata_code="VCE"),
            ),
            OriginDestinationSegment(
                departure_date=d0 + timedelta(days=11),
                origin_airport=AirportInfo(iata_code="VCE"),
                destination_airport=AirportInfo(iata_code="DFW"),
            ),
        ],
        cabin_class=CabinClass.ECONOMY,
        adults=1,
        children=0,
        infants=0,
    )
    assert req.journey_type == JourneyType.CIRCLE
    assert len(req.origin_destination_info) == 3
