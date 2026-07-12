"""Unit tests for flight route / airline snapshot helpers (lightweight mocks).

Loads ``route_snapshot`` by file path so tests run without importing ``app.domains.flight``
package ``__init__`` (heavy optional deps in some dev shells).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

_BACKEND_ROOT = Path(__file__).resolve().parents[4]
_RS_PATH = _BACKEND_ROOT / "app/domains/flight/route_snapshot.py"
_MOD_NAME = "flight_route_snapshot_testonly"
_spec = importlib.util.spec_from_file_location(_MOD_NAME, _RS_PATH)
assert _spec is not None
assert _spec.loader is not None
_rs = importlib.util.module_from_spec(_spec)
sys.modules[_MOD_NAME] = _rs
_spec.loader.exec_module(_rs)
build_route_legs_from_revalidate = _rs.build_route_legs_from_revalidate
extract_route_and_airline_snapshot = _rs.extract_route_and_airline_snapshot
extract_route_fields_from_trip_details = _rs.extract_route_fields_from_trip_details


def _ap(code: str) -> SimpleNamespace:
    return SimpleNamespace(iata_code=code)


def _seg(dep: str, arr: str, *, airline: str = "Test Air") -> SimpleNamespace:
    return SimpleNamespace(
        departure_airport=_ap(dep),
        arrival_airport=_ap(arr),
        marketing_airline=SimpleNamespace(airline_name=airline),
    )


def _leg(segments: list[SimpleNamespace]) -> SimpleNamespace:
    return SimpleNamespace(flight_segments=segments)


def _revalidate(
    journey_type: str,
    legs: list[SimpleNamespace],
) -> SimpleNamespace:
    itin = SimpleNamespace(journey_type=journey_type, flight_legs=legs)
    return SimpleNamespace(validated_fare_itineraries=[itin])


def test_extract_route_one_way_from_revalidate() -> None:
    seg = _seg("JFK", "LHR")
    rev = _revalidate("OneWay", [_leg([seg])])
    snap = extract_route_and_airline_snapshot(rev, pnr_airline_name=None)
    assert snap.flight_trip_type == "one_way"
    assert len(snap.route_legs) == 1
    assert snap.route_legs[0].departure_iata == "JFK"
    assert snap.route_legs[0].arrival_iata == "LHR"
    assert snap.primary_marketing_airline_name == "Test Air"


def test_extract_route_return_four_vendor_legs_connecting() -> None:
    """Return with one API leg per segment: outbound LHR–LIS–JFK, return JFK–LIS–LHR."""
    legs = [
        _leg([_seg("LHR", "LIS")]),
        _leg([_seg("LIS", "JFK")]),
        _leg([_seg("JFK", "LIS")]),
        _leg([_seg("LIS", "LHR")]),
    ]
    rev = _revalidate("Return", legs)
    snap = extract_route_and_airline_snapshot(rev)
    assert snap.flight_trip_type == "round_trip"
    assert len(snap.route_legs) == 2
    assert snap.route_legs[0].departure_iata == "LHR"
    assert snap.route_legs[0].arrival_iata == "JFK"
    assert snap.route_legs[0].segment_count == 2
    assert snap.route_legs[1].departure_iata == "JFK"
    assert snap.route_legs[1].arrival_iata == "LHR"
    assert snap.route_legs[1].segment_count == 2


def test_build_route_revalidate_return_four_legs_flatten_multi_segment_halves() -> None:
    """4 Return legs: flatten first two vendor legs to outbound, last two to return (3 segs each)."""
    legs = [
        _leg([_seg("LHR", "LIS"), _seg("LIS", "CDG")]),
        _leg([_seg("CDG", "JFK")]),
        _leg([_seg("JFK", "CDG"), _seg("CDG", "LIS")]),
        _leg([_seg("LIS", "LHR")]),
    ]
    rev = _revalidate("Return", legs)
    route_legs, trip_type = build_route_legs_from_revalidate(rev)
    assert trip_type == "round_trip"
    assert len(route_legs) == 2
    assert route_legs[0].departure_iata == "LHR"
    assert route_legs[0].arrival_iata == "JFK"
    assert route_legs[0].segment_count == 3
    assert route_legs[1].departure_iata == "JFK"
    assert route_legs[1].arrival_iata == "LHR"
    assert route_legs[1].segment_count == 3


def test_extract_route_return_two_legs_from_revalidate() -> None:
    out = _seg("JFK", "LHR", airline="Out")
    ret = _seg("LHR", "JFK", airline="Ret")
    rev = _revalidate(
        "Return",
        [
            _leg([out]),
            _leg([ret]),
        ],
    )
    snap = extract_route_and_airline_snapshot(rev)
    assert snap.flight_trip_type == "round_trip"
    assert len(snap.route_legs) == 2
    assert snap.route_legs[0].arrival_iata == "LHR"
    assert snap.route_legs[1].departure_iata == "LHR"
    assert snap.route_legs[1].arrival_iata == "JFK"


def test_extract_route_return_single_leg_one_segment_is_one_way() -> None:
    """Return journey with a single physical segment cannot be split into two legs."""
    seg = _seg("JFK", "LHR")
    rev = _revalidate("Return", [_leg([seg])])
    snap = extract_route_and_airline_snapshot(rev)
    assert snap.flight_trip_type == "one_way"
    assert len(snap.route_legs) == 1
    assert snap.route_legs[0].departure_iata == "JFK"
    assert snap.route_legs[0].arrival_iata == "LHR"


def test_extract_route_return_single_leg_two_segments() -> None:
    s0 = _seg("JFK", "LHR")
    s1 = _seg("LHR", "JFK")
    rev = _revalidate("Return", [_leg([s0, s1])])
    snap = extract_route_and_airline_snapshot(rev)
    assert snap.flight_trip_type == "round_trip"
    assert len(snap.route_legs) == 2


def test_extract_route_multistay_leg_index() -> None:
    leg0 = _leg([_seg("AAA", "BBB")])
    leg1 = _leg([_seg("BBB", "CCC")])
    rev = _revalidate("Circle", [leg0, leg1])
    snap = extract_route_and_airline_snapshot(rev, multistay_leg_index=1)
    assert snap.flight_trip_type == "multi_city"
    assert len(snap.route_legs) == 1
    assert snap.route_legs[0].arrival_iata == "CCC"


def test_pnr_only_sets_marketing_name() -> None:
    snap = extract_route_and_airline_snapshot(None, pnr_airline_name="  Delta  ")
    assert snap.primary_marketing_airline_name == "Delta"
    assert not snap.route_legs


def test_extract_route_fields_from_trip_details_simple_rt() -> None:
    """Trip-details shape: origin/destination + two segments (JFK→LHR, LHR→JFK)."""
    jfk, lhr = _ap("JFK"), _ap("LHR")
    s1 = SimpleNamespace(
        departure_airport=jfk,
        arrival_airport=lhr,
        marketing_airline=SimpleNamespace(airline_name="British Airways"),
        airline_pnr=SimpleNamespace(
            airline=SimpleNamespace(airline_name="British Airways")
        ),
    )
    s2 = SimpleNamespace(
        departure_airport=lhr,
        arrival_airport=jfk,
        marketing_airline=SimpleNamespace(airline_name="British Airways"),
        airline_pnr=SimpleNamespace(
            airline=SimpleNamespace(airline_name="British Airways")
        ),
    )
    td = SimpleNamespace(
        origin=jfk,
        destination=lhr,
        segments=[s1, s2],
    )
    fields = extract_route_fields_from_trip_details(td)  # type: ignore[arg-type]
    assert fields["departure_airport_iata"] == "JFK"
    assert fields["flight_trip_type"] == "round_trip"
    assert fields["primary_marketing_airline_name"] == "British Airways"
    assert "route_legs" in fields
    rl = fields["route_legs"]
    assert isinstance(rl, list)
    assert len(rl) == 2


def test_extract_route_fields_from_trip_details_four_segment_connecting_rt() -> None:
    """Trip-details: LHR–LIS–JFK outbound, JFK–LIS–LHR return (flat segments)."""
    lhr, lis, jfk = _ap("LHR"), _ap("LIS"), _ap("JFK")
    ba = SimpleNamespace(airline_name="TAP Air Portugal")

    def mk_seg(dep: SimpleNamespace, arr: SimpleNamespace) -> SimpleNamespace:
        return SimpleNamespace(
            departure_airport=dep,
            arrival_airport=arr,
            marketing_airline=ba,
            airline_pnr=SimpleNamespace(airline=ba),
        )

    segments = [
        mk_seg(lhr, lis),
        mk_seg(lis, jfk),
        mk_seg(jfk, lis),
        mk_seg(lis, lhr),
    ]
    td = SimpleNamespace(
        origin=lhr,
        destination=jfk,
        segments=segments,
    )
    fields = extract_route_fields_from_trip_details(td)  # type: ignore[arg-type]
    assert fields["flight_trip_type"] == "round_trip"
    rl = fields["route_legs"]
    assert isinstance(rl, list)
    assert len(rl) == 2
    assert rl[0]["departure_iata"] == "LHR"
    assert rl[0]["arrival_iata"] == "JFK"
    assert rl[0]["segment_count"] == 2
    assert rl[1]["departure_iata"] == "JFK"
    assert rl[1]["arrival_iata"] == "LHR"
    assert rl[1]["segment_count"] == 2


def test_extract_route_fields_empty_segments_missing_origin_no_crash() -> None:
    """Vendor may omit origin when there are no segments; do not access None.origin."""
    td = SimpleNamespace(segments=[], origin=None)
    fields = extract_route_fields_from_trip_details(td)  # type: ignore[arg-type]
    assert fields == {}
