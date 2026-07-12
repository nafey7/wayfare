"""Unit tests for journey type normalization and booking search_params helpers."""

import pytest

from app.domains.flight.enums import JourneyType
from app.domains.flight.journey_params import (
    build_booking_search_route_params_from_flight_dict,
    coerce_legacy_flight_search_request_dict,
    infer_journey_type_when_missing,
    is_return_two_leg_topology,
    normalize_fl_api_journey_type,
    normalize_search_redirect_journey_type,
)


def test_normalize_fl_api_journey_type_round_trip_alias() -> None:
    assert normalize_fl_api_journey_type("RoundTrip") == JourneyType.RETURN.value
    assert normalize_fl_api_journey_type(JourneyType.CIRCLE) == JourneyType.CIRCLE.value
    assert normalize_fl_api_journey_type(None) == ""


def test_normalize_search_redirect_journey_type() -> None:
    assert (
        normalize_search_redirect_journey_type("RoundTrip", has_return_date=False)
        == JourneyType.RETURN.value
    )
    assert (
        normalize_search_redirect_journey_type("Circle", has_return_date=False)
        == JourneyType.CIRCLE.value
    )
    assert (
        normalize_search_redirect_journey_type("unknown", has_return_date=True)
        == JourneyType.RETURN.value
    )
    assert (
        normalize_search_redirect_journey_type("unknown", has_return_date=False)
        == JourneyType.ONE_WAY.value
    )


def test_normalize_search_redirect_journey_type_strips_whitespace() -> None:
    """Unknown-looking values with spaces must match known labels after strip."""
    assert (
        normalize_search_redirect_journey_type(" Return ", has_return_date=False)
        == JourneyType.RETURN.value
    )
    assert (
        normalize_search_redirect_journey_type("  OneWay  ", has_return_date=True)
        == JourneyType.ONE_WAY.value
    )
    assert (
        normalize_search_redirect_journey_type("\tCircle\n", has_return_date=False)
        == JourneyType.CIRCLE.value
    )
    assert (
        normalize_search_redirect_journey_type(" RoundTrip ", has_return_date=False)
        == JourneyType.RETURN.value
    )


def test_is_return_two_leg_topology() -> None:
    legs = [
        {
            "flight_segments": [
                {
                    "departure_airport": {"iata_code": "lhr"},
                    "arrival_airport": {"iata_code": "cdg"},
                }
            ]
        },
        {
            "flight_segments": [
                {
                    "departure_airport": {"iata_code": "cdg"},
                    "arrival_airport": {"iata_code": "lhr"},
                }
            ]
        },
    ]
    assert is_return_two_leg_topology(legs) is True
    assert infer_journey_type_when_missing(legs) == JourneyType.RETURN.value


def test_infer_circle_multi_leg_non_return() -> None:
    legs = [
        {
            "flight_segments": [
                {
                    "departure_airport": {"iata_code": "DEL"},
                    "arrival_airport": {"iata_code": "BOM"},
                }
            ]
        },
        {
            "flight_segments": [
                {
                    "departure_airport": {"iata_code": "BOM"},
                    "arrival_airport": {"iata_code": "DXB"},
                }
            ]
        },
    ]
    assert is_return_two_leg_topology(legs) is False
    assert infer_journey_type_when_missing(legs) == JourneyType.CIRCLE.value


def test_is_return_two_leg_topology_multi_segment_outbound() -> None:
    """First leg can have multiple segments; topology uses first dep and last arr per leg."""
    legs = [
        {
            "flight_segments": [
                {
                    "departure_airport": {"iata_code": "LHR"},
                    "arrival_airport": {"iata_code": "MAN"},
                },
                {
                    "departure_airport": {"iata_code": "MAN"},
                    "arrival_airport": {"iata_code": "CDG"},
                },
            ]
        },
        {
            "flight_segments": [
                {
                    "departure_airport": {"iata_code": "CDG"},
                    "arrival_airport": {"iata_code": "LHR"},
                }
            ]
        },
    ]
    assert is_return_two_leg_topology(legs) is True
    assert infer_journey_type_when_missing(legs) == JourneyType.RETURN.value


def test_is_return_two_leg_topology_different_return_airport_not_round_trip() -> None:
    """Open-jaw style return (e.g. into different metro airport) is not A→B / B→A topology."""
    legs = [
        {
            "flight_segments": [
                {
                    "departure_airport": {"iata_code": "LHR"},
                    "arrival_airport": {"iata_code": "CDG"},
                }
            ]
        },
        {
            "flight_segments": [
                {
                    "departure_airport": {"iata_code": "CDG"},
                    "arrival_airport": {"iata_code": "LGW"},
                }
            ]
        },
    ]
    assert is_return_two_leg_topology(legs) is False
    assert infer_journey_type_when_missing(legs) == JourneyType.CIRCLE.value


def test_build_route_params_explicit_circle() -> None:
    fd = {
        "journey_type": JourneyType.CIRCLE,
        "flight_legs": [
            {
                "flight_segments": [
                    {
                        "departure_airport": {"iata_code": "A"},
                        "arrival_airport": {"iata_code": "B"},
                        "departure_datetime": "2025-06-01T10:00:00",
                    },
                    {
                        "departure_airport": {"iata_code": "B"},
                        "arrival_airport": {"iata_code": "C"},
                        "departure_datetime": "2025-06-02T10:00:00",
                    },
                ]
            }
        ],
    }
    out = build_booking_search_route_params_from_flight_dict(fd)
    assert out["journey_type"] == JourneyType.CIRCLE.value
    assert out["airport_codes_chain"] == ["A", "B", "C"]
    assert out["origin"] == "A"
    assert out["destination"] == "C"


def test_build_route_params_unknown_journey_type_uses_topology_not_false_return() -> (
    None
):
    """Garbage journey_type must not set Return+return_date on open-jaw two-leg itineraries."""
    fd = {
        "journey_type": "Unknown",
        "flight_legs": [
            {
                "flight_segments": [
                    {
                        "departure_airport": {"iata_code": "DEL"},
                        "arrival_airport": {"iata_code": "BOM"},
                        "departure_datetime": "2025-06-01T10:00:00",
                    }
                ]
            },
            {
                "flight_segments": [
                    {
                        "departure_airport": {"iata_code": "BOM"},
                        "arrival_airport": {"iata_code": "DXB"},
                        "departure_datetime": "2025-06-10T10:00:00",
                    }
                ]
            },
        ],
    }
    out = build_booking_search_route_params_from_flight_dict(fd)
    assert out["journey_type"] == JourneyType.CIRCLE.value
    assert out["airport_codes_chain"] == ["DEL", "BOM", "DXB"]
    assert "return_date" not in out


def test_build_route_params_unknown_journey_type_return_topology() -> None:
    """Unknown type with A→B / B→A legs still infers Return via topology."""
    fd = {
        "journey_type": "VendorTypo",
        "flight_legs": [
            {
                "flight_segments": [
                    {
                        "departure_airport": {"iata_code": "LHR"},
                        "arrival_airport": {"iata_code": "CDG"},
                        "departure_datetime": "2025-06-01T10:00:00",
                    }
                ]
            },
            {
                "flight_segments": [
                    {
                        "departure_airport": {"iata_code": "CDG"},
                        "arrival_airport": {"iata_code": "LHR"},
                        "departure_datetime": "2025-06-15T10:00:00",
                    }
                ]
            },
        ],
    }
    out = build_booking_search_route_params_from_flight_dict(fd)
    assert out["journey_type"] == JourneyType.RETURN.value
    assert out["return_date"] == "2025-06-15"


def test_build_route_params_inferred_return_two_legs() -> None:
    fd = {
        "flight_legs": [
            {
                "flight_segments": [
                    {
                        "departure_airport": {"iata_code": "LHR"},
                        "arrival_airport": {"iata_code": "CDG"},
                        "departure_datetime": "2025-06-01T10:00:00",
                    }
                ]
            },
            {
                "flight_segments": [
                    {
                        "departure_airport": {"iata_code": "CDG"},
                        "arrival_airport": {"iata_code": "LHR"},
                        "departure_datetime": "2025-06-15T10:00:00",
                    }
                ]
            },
        ]
    }
    out = build_booking_search_route_params_from_flight_dict(fd)
    assert out["journey_type"] == JourneyType.RETURN.value
    assert out["return_date"] == "2025-06-15"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("OneWay", JourneyType.ONE_WAY.value),
        ("Return", JourneyType.RETURN.value),
        ("Circle", JourneyType.CIRCLE.value),
    ],
)
def test_normalize_search_redirect_known(raw: str, expected: str) -> None:
    assert (
        normalize_search_redirect_journey_type(raw, has_return_date=False) == expected
    )


def test_coerce_legacy_return_missing_airports_raises_clear_error() -> None:
    """Single-row Return+return_date without airports must not raise KeyError from coerce."""
    payload = {
        "journey_type": "Return",
        "origin_destination_info": [
            {"departure_date": "2025-06-01", "return_date": "2025-06-15"}
        ],
    }
    with pytest.raises(
        ValueError,
        match="origin_airport and destination_airport",
    ):
        coerce_legacy_flight_search_request_dict(payload)
