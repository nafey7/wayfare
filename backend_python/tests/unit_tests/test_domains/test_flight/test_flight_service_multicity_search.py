"""Multicity (Circle) parallel OneWay search orchestration in FlightService."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.common import ErrorDetails
from app.domains.flight.enums import CabinClass, JourneyType
from app.domains.flight.schemas import (
    AirportInfo,
    FlightSearchRequest,
    MulticityLegSearchResult,
    OriginDestinationSegment,
)
from app.domains.flight.service import (
    FlightService,
    _build_multicity_leg_search_request,
    _filters_for_multicity_leg,
)


def _segment(
    origin: str, dest: str, dep: date, ret: date | None = None
) -> OriginDestinationSegment:
    return OriginDestinationSegment(
        departure_date=dep,
        return_date=ret,
        origin_airport=AirportInfo(iata_code=origin),
        destination_airport=AirportInfo(iata_code=dest),
    )


def _circle_request() -> FlightSearchRequest:
    return FlightSearchRequest(
        journey_type=JourneyType.CIRCLE,
        origin_destination_info=[
            _segment("LHR", "CDG", date(2026, 6, 1)),
            _segment("CDG", "FCO", date(2026, 6, 8)),
            _segment("FCO", "LHR", date(2026, 6, 15)),
        ],
        cabin_class=CabinClass.ECONOMY,
        adults=1,
        children=0,
        infants=0,
    )


class TestMulticityHelpers:
    def test_filters_for_multicity_leg_slices_journey_filters(self) -> None:
        from app.domains.flight.schemas import FlightSearchFilters, LegFilter

        req = _circle_request()
        req.filters = FlightSearchFilters(
            journey_filters=[
                LegFilter(leg_index=0, description="a"),
                LegFilter(leg_index=1, description="b"),
                LegFilter(leg_index=2, description="c"),
            ]
        )
        f0 = _filters_for_multicity_leg(req, 0)
        assert f0 is not None
        assert f0.journey_filters is not None
        assert len(f0.journey_filters) == 1
        assert f0.journey_filters[0].leg_index == 0

        f2 = _filters_for_multicity_leg(req, 2)
        assert f2 is not None
        assert f2.journey_filters is not None
        assert f2.journey_filters[0].description == "c"

    def test_build_multicity_leg_search_request_is_one_way_single_segment(self) -> None:
        req = _circle_request()
        leg0 = _build_multicity_leg_search_request(req, 0)
        assert leg0.journey_type == JourneyType.ONE_WAY
        assert len(leg0.origin_destination_info) == 1
        assert leg0.origin_destination_info[0].origin_airport.iata_code == "LHR"
        assert leg0.origin_destination_info[0].destination_airport.iata_code == "CDG"


@pytest.mark.asyncio
class TestMulticityParallelSearch:
    async def test_circle_runs_parallel_one_way_searches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        svc = FlightService(current_user=None)
        calls: list[int] = []

        async def fake_search(req: FlightSearchRequest):
            calls.append(len(req.origin_destination_info))
            r = MagicMock()
            r.session_id = f"s-{len(calls)}"
            r.supplier = "TestSupplier"
            r.fare_itineraries = []
            r.inbound_fare_itineraries = None
            return r

        svc.client.search_flights = AsyncMock(side_effect=fake_search)
        svc.get_airline_list = AsyncMock(
            return_value=MagicMock(airlines=[MagicMock(iata_code="BA", logo_url=None)])
        )
        svc._finalize_search_response_after_client = AsyncMock(
            side_effect=lambda req, resp, route, code_to_logo=None: resp
        )

        req = _circle_request()
        out = await svc._search_multicity_parallel(req, MagicMock())

        assert svc.client.search_flights.await_count == 3
        assert calls == [1, 1, 1]
        assert out.multicity_legs is not None
        assert len(out.multicity_legs) == 3
        assert out.session_id == ""
        assert out.fare_itineraries == []
        assert out.multicity_legs[0].session_id == "s-1"


class TestMulticityLegSearchResultSchema:
    def test_round_trip(self) -> None:
        m = MulticityLegSearchResult(
            leg_index=0,
            origin="LHR",
            destination="JFK",
            departure_date=date(2026, 7, 1),
            session_id="abc",
            supplier="X",
            fare_itineraries=[],
            errors=[ErrorDetails(code="E", message="m")],
        )
        d = m.model_dump()
        assert d["leg_index"] == 0
        assert d["errors"][0]["code"] == "E"
