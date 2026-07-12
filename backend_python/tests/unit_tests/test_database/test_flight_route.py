"""Tests for app.database.flight_route (IATA normalization and route leg parsing)."""

import pytest
from pydantic import ValidationError

from app.database.flight_route import RouteSegment, parse_route_legs_from_document


def test_route_segment_validation_error_mentions_iata_length() -> None:
    with pytest.raises(ValidationError) as exc:
        RouteSegment(departure_iata="ABCD", arrival_iata="LHR")
    err = str(exc.value)
    assert "IATA" in err or "3 letters" in err


def test_route_segment_validation_error_when_not_alpha() -> None:
    with pytest.raises(ValidationError) as exc:
        RouteSegment(departure_iata="12A", arrival_iata="LHR")
    assert "3 letters" in str(exc.value) or "A-Z" in str(exc.value)


def test_parse_route_legs_from_document_returns_none_when_leg_invalid() -> None:
    raw = [
        {
            "leg_index": 0,
            "departure_iata": "XX",  # invalid length
            "arrival_iata": "LHR",
            "segment_count": 1,
            "segments": [{"departure_iata": "XX", "arrival_iata": "LHR"}],
        }
    ]
    assert parse_route_legs_from_document(raw, booking_id="bid-1") is None
