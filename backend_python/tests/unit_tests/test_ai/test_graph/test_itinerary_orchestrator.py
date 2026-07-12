"""Unit tests for the personalized-itinerary orchestrator (#1038).

Covers:
- ``kick_off_side_searches`` gates each search on its own required fields
  (flight needs origin_iata + destination_iata + departure_date; hotel needs
  destination + departure_date + return_date).
- ``await_side_searches`` surfaces empty lists on no_results / error /
  exception (graceful degradation).
- ``attach_search_results_to_response`` writes top-level ``flights``/``hotels``
  AND invokes the stitcher when ``structured_itinerary`` is present.

The two ``_safe_*_search`` wrappers in the orchestrator import the
``_do_*_search`` helpers lazily, so we patch via ``sys.modules`` to keep the
LangGraph module graph out of the test process.
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.graph.itinerary_orchestrator import (
    _PENDING_SIDE_SEARCHES,
    _resolve_destination_for_hotel,
    _safe_hotel_search,
    attach_search_results_to_response,
    await_side_searches,
    clear_pending_side_searches,
    kick_off_side_searches,
    pop_pending_side_searches,
    stash_pending_side_searches,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _trip_ctx_full() -> dict[str, Any]:
    """A trip_ctx with every field both searches need."""
    return {
        "origin_iata": "LHR",
        "destination_iata": "NRT",
        "destination": "Tokyo",
        "destination_country": "Japan",
        "departure_date": "2026-06-01",
        "return_date": "2026-06-08",
        "adults": 2,
        "children": 0,
        "infants": 0,
        "rooms": 1,
    }


def _patch_helpers(
    flight_result: dict | None = None,
    hotel_result: dict | None = None,
    *,
    flight_raises: BaseException | None = None,
    hotel_raises: BaseException | None = None,
) -> dict[str, MagicMock]:
    """Build sys.modules patches for the two helper imports done lazily inside
    the orchestrator's safe-wrappers.

    Returns a dict of MagicMock modules — caller uses with
    ``patch.dict(sys.modules, ...)``.
    """
    flights_module = MagicMock()
    if flight_raises is not None:
        flights_module._do_flight_search = AsyncMock(side_effect=flight_raises)
    else:
        flights_module._do_flight_search = AsyncMock(return_value=flight_result)

    hotels_module = MagicMock()
    if hotel_raises is not None:
        hotels_module._do_hotel_search = AsyncMock(side_effect=hotel_raises)
    else:
        hotels_module._do_hotel_search = AsyncMock(return_value=hotel_result)

    # The orchestrator imports as `app.ai.graph.tools.flights` /
    # `app.ai.graph.tools.hotels`. These modules ARE real in the test image —
    # we replace just the helpers via attribute patch, scoped per test.
    return {
        "_flights_real": sys.modules.get("app.ai.graph.tools.flights"),
        "_hotels_real": sys.modules.get("app.ai.graph.tools.hotels"),
        "_flights_mock_helper": flights_module._do_flight_search,
        "_hotels_mock_helper": hotels_module._do_hotel_search,
    }


# ---------------------------------------------------------------------------
# kick_off_side_searches
# ---------------------------------------------------------------------------


class TestKickOffSideSearches:
    def test_returns_none_none_when_trip_ctx_empty(self) -> None:
        """Cold first turn: nothing to fire on."""
        flight_task, hotel_task, _ = kick_off_side_searches({}, user_id="u1")
        assert flight_task is None
        assert hotel_task is None

    def test_returns_none_none_when_trip_ctx_is_none(self) -> None:
        flight_task, hotel_task, _ = kick_off_side_searches(None, user_id="u1")
        assert flight_task is None
        assert hotel_task is None

    @pytest.mark.asyncio
    async def test_skips_flight_when_origin_missing(self) -> None:
        """Doc: 'If origin is missing, flight search is skipped silently.'"""
        ctx = _trip_ctx_full()
        del ctx["origin_iata"]
        with patch(
            "app.ai.graph.tools.hotels._do_hotel_search",
            new=AsyncMock(return_value={"status": "no_results"}),
        ):
            flight_task, hotel_task, _ = kick_off_side_searches(ctx, user_id="u1")
            assert flight_task is None
            assert hotel_task is not None  # hotel doesn't need origin
            await hotel_task  # drain so the test cleans up

    @pytest.mark.asyncio
    async def test_skips_hotel_when_return_date_missing(self) -> None:
        """Hotel search needs check-out (return_date) — one-way trips skip hotel."""
        ctx = _trip_ctx_full()
        del ctx["return_date"]
        with patch(
            "app.ai.graph.tools.flights._do_flight_search",
            new=AsyncMock(return_value={"status": "no_results"}),
        ):
            flight_task, hotel_task, _ = kick_off_side_searches(ctx, user_id="u1")
            assert flight_task is not None
            assert hotel_task is None
            await flight_task

    @pytest.mark.asyncio
    async def test_fires_both_when_trip_ctx_full(self) -> None:
        ctx = _trip_ctx_full()
        with (
            patch(
                "app.ai.graph.tools.flights._do_flight_search",
                new=AsyncMock(return_value={"status": "no_results"}),
            ),
            patch(
                "app.ai.graph.tools.hotels._do_hotel_search",
                new=AsyncMock(return_value={"status": "no_results"}),
            ),
        ):
            flight_task, hotel_task, _ = kick_off_side_searches(ctx, user_id="u1")
            assert flight_task is not None
            assert hotel_task is not None
            await flight_task
            await hotel_task

    @pytest.mark.asyncio
    async def test_returns_new_hotel_key_when_hotel_fired(self) -> None:
        """#1127: kick_off_side_searches returns the hotel dedup key so the
        caller can persist it on trip_ctx and skip the duplicate FlightLogic
        call on the next pre_resolve_trip entry."""
        ctx = _trip_ctx_full()
        with (
            patch(
                "app.ai.graph.tools.flights._do_flight_search",
                new=AsyncMock(return_value={"status": "no_results"}),
            ),
            patch(
                "app.ai.graph.tools.hotels._do_hotel_search",
                new=AsyncMock(return_value={"status": "no_results"}),
            ),
        ):
            flight_task, hotel_task, new_hotel_key = kick_off_side_searches(
                ctx, user_id="u1"
            )
            assert hotel_task is not None
            assert new_hotel_key is not None
            # Key is stable across calls with the same trip_ctx (round-trip).
            from app.ai.graph.itinerary_orchestrator import compute_hotel_search_key

            assert new_hotel_key == compute_hotel_search_key(ctx)
            if flight_task:
                await flight_task
            await hotel_task

    @pytest.mark.asyncio
    async def test_skips_hotel_when_key_matches_previous(self) -> None:
        """#1127: when ``trip_ctx.last_hotel_search_key`` already matches the
        current params, the hotel side-search must NOT fire — duplicate
        FlightLogic calls waste quota when origin lands on a follow-up turn
        but hotel inputs are unchanged."""
        from app.ai.graph.itinerary_orchestrator import compute_hotel_search_key

        ctx = _trip_ctx_full()
        # Pre-set the dedup key so it matches the current params exactly.
        ctx["last_hotel_search_key"] = compute_hotel_search_key(ctx)

        hotel_helper = AsyncMock(return_value={"status": "no_results"})
        with (
            patch(
                "app.ai.graph.tools.flights._do_flight_search",
                new=AsyncMock(return_value={"status": "no_results"}),
            ),
            patch(
                "app.ai.graph.tools.hotels._do_hotel_search",
                new=hotel_helper,
            ),
        ):
            flight_task, hotel_task, new_hotel_key = kick_off_side_searches(
                ctx, user_id="u1"
            )
            # Flight still fires; hotel does not, and no new key is returned.
            assert hotel_task is None
            assert new_hotel_key is None
            # FlightLogic hotel helper must NOT have been called.
            hotel_helper.assert_not_called()
            if flight_task:
                await flight_task

    @pytest.mark.asyncio
    async def test_fires_hotel_when_key_changes(self) -> None:
        """#1127: when the user changes destination / dates / party, the
        hotel dedup key changes and the search re-fires."""
        ctx = _trip_ctx_full()
        ctx["last_hotel_search_key"] = "stale-key-from-different-trip"

        with (
            patch(
                "app.ai.graph.tools.flights._do_flight_search",
                new=AsyncMock(return_value={"status": "no_results"}),
            ),
            patch(
                "app.ai.graph.tools.hotels._do_hotel_search",
                new=AsyncMock(return_value={"status": "no_results"}),
            ),
        ):
            _, hotel_task, new_hotel_key = kick_off_side_searches(ctx, user_id="u1")
            # Stale key → fresh hotel fire, new key returned.
            assert hotel_task is not None
            assert new_hotel_key is not None
            assert new_hotel_key != "stale-key-from-different-trip"
            await hotel_task

    def test_hotel_search_key_includes_search_city_for_country_destinations(
        self,
    ) -> None:
        """#1127: the dedup key uses ``destination_search_city`` (Kotor) when
        present so that country-resolved trips don't collide with a regular
        Kotor-as-city destination keyed on bare ``destination``."""
        from app.ai.graph.itinerary_orchestrator import compute_hotel_search_key

        country_trip = {
            "destination": "Montenegro",
            "destination_search_city": "Kotor",
            "departure_date": "2026-07-20",
            "return_date": "2026-08-02",
            "adults": 2,
            "children": 2,
            "rooms": 1,
        }
        city_trip = {
            "destination": "Kotor",
            "departure_date": "2026-07-20",
            "return_date": "2026-08-02",
            "adults": 2,
            "children": 2,
            "rooms": 1,
        }
        # Different keys even though both end up searching hotels in Kotor —
        # the country path carries the "Montenegro" label too, which makes the
        # cache cleanly separated and avoids cross-flow accidents.
        assert compute_hotel_search_key(country_trip) != compute_hotel_search_key(
            city_trip
        )


# ---------------------------------------------------------------------------
# await_side_searches
# ---------------------------------------------------------------------------


class TestAwaitSideSearches:
    @pytest.mark.asyncio
    async def test_both_none_returns_empty_lists(self) -> None:
        result = await await_side_searches(None, None)
        assert result["flights"] == []
        assert result["hotels"] == []
        assert result["flight_session_id"] is None
        assert result["hotel_session_id"] is None
        assert result["flight_search_params"] is None
        assert result["hotel_search_params"] is None

    @pytest.mark.asyncio
    async def test_surfaces_success_results(self) -> None:
        ctx = _trip_ctx_full()
        flight_payload = {
            "status": "success",
            "session_id": "fs1",
            "search_params": {"origin": "LHR", "destination": "CDG"},
            "flights": [{"id": "f1"}, {"id": "f2"}],
        }
        hotel_payload = {
            "status": "success",
            "session_id": "hs1",
            "search_params": {"destination_city": "Tokyo"},
            "hotels": [{"hotel_id": "h1"}],
        }

        with (
            patch(
                "app.ai.graph.tools.flights._do_flight_search",
                new=AsyncMock(return_value=flight_payload),
            ),
            patch(
                "app.ai.graph.tools.hotels._do_hotel_search",
                new=AsyncMock(return_value=hotel_payload),
            ),
        ):
            f_task, h_task, _ = kick_off_side_searches(ctx, user_id="u1")
            result = await await_side_searches(f_task, h_task)

        assert len(result["flights"]) == 2
        assert result["flights"][0]["id"] == "f1"
        assert len(result["hotels"]) == 1
        assert result["hotels"][0]["hotel_id"] == "h1"
        # Session IDs + search_params now surface for FE hydration.
        assert result["flight_session_id"] == "fs1"
        assert result["hotel_session_id"] == "hs1"
        assert result["flight_search_params"] == {"origin": "LHR", "destination": "CDG"}
        assert result["hotel_search_params"] == {"destination_city": "Tokyo"}

    @pytest.mark.asyncio
    async def test_no_results_status_returns_empty_list(self) -> None:
        """Doc: 'Graceful degradation — itinerary still ships with whatever succeeded.'"""
        ctx = _trip_ctx_full()
        with (
            patch(
                "app.ai.graph.tools.flights._do_flight_search",
                new=AsyncMock(
                    return_value={"status": "no_results", "message": "no flights"}
                ),
            ),
            patch(
                "app.ai.graph.tools.hotels._do_hotel_search",
                new=AsyncMock(
                    return_value={
                        "status": "success",
                        "session_id": "hs1",
                        "search_params": {"destination_city": "Tokyo"},
                        "hotels": [{"hotel_id": "h1"}],
                    }
                ),
            ),
        ):
            f_task, h_task, _ = kick_off_side_searches(ctx, user_id="u1")
            result = await await_side_searches(f_task, h_task)

        # Flight returned no_results — empty list + no session; hotel still surfaces.
        assert result["flights"] == []
        assert result["flight_session_id"] is None
        assert result["flight_search_params"] is None
        assert len(result["hotels"]) == 1
        assert result["hotel_session_id"] == "hs1"

    @pytest.mark.asyncio
    async def test_helper_exception_caught_returns_empty(self) -> None:
        """An exception in the helper must not crash the orchestrator."""
        ctx = _trip_ctx_full()
        with (
            patch(
                "app.ai.graph.tools.flights._do_flight_search",
                new=AsyncMock(side_effect=RuntimeError("FL down")),
            ),
            patch(
                "app.ai.graph.tools.hotels._do_hotel_search",
                new=AsyncMock(
                    return_value={
                        "status": "success",
                        "session_id": "hs1",
                        "search_params": {"destination_city": "Tokyo"},
                        "hotels": [{"hotel_id": "h1"}],
                    }
                ),
            ),
        ):
            f_task, h_task, _ = kick_off_side_searches(ctx, user_id="u1")
            result = await await_side_searches(f_task, h_task)

        assert result["flights"] == []
        # Hotel side unaffected — graceful degradation.
        assert len(result["hotels"]) == 1
        assert result["hotel_session_id"] == "hs1"


# ---------------------------------------------------------------------------
# attach_search_results_to_response
# ---------------------------------------------------------------------------


def _side(
    flights: list[dict[str, Any]] | None = None,
    hotels: list[dict[str, Any]] | None = None,
    *,
    flight_session_id: str | None = None,
    hotel_session_id: str | None = None,
    flight_search_params: dict[str, Any] | None = None,
    hotel_search_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the side-search results dict the attach function consumes."""
    return {
        "flights": flights or [],
        "hotels": hotels or [],
        "flight_session_id": flight_session_id,
        "hotel_session_id": hotel_session_id,
        "flight_search_params": flight_search_params,
        "hotel_search_params": hotel_search_params,
    }


class TestAttachSearchResultsToResponse:
    def test_attaches_top_level_lists(self) -> None:
        response: dict[str, Any] = {
            "type": "itinerary_results",
            "metadata": {"structured_itinerary": {"itineraryItems": []}},
        }
        out = attach_search_results_to_response(
            response,
            _side(
                flights=[{"id": "f1"}],
                hotels=[{"hotel_id": "h1"}],
                flight_session_id="fs1",
                hotel_session_id="hs1",
                flight_search_params={"origin": "LHR"},
                hotel_search_params={"destination_city": "Tokyo"},
            ),
            is_round_trip=True,
        )

        assert out is response  # mutation, no copy
        assert out["flights"] == [{"id": "f1"}]
        assert out["hotels"] == [{"hotel_id": "h1"}]
        # New: session + params propagate so the FE can hydrate its slices.
        assert out["flight_session_id"] == "fs1"
        assert out["hotel_session_id"] == "hs1"
        assert out["flight_search_params"] == {"origin": "LHR"}
        assert out["hotel_search_params"] == {"destination_city": "Tokyo"}

    def test_stitches_when_structured_itinerary_present(self) -> None:
        """Stitcher should run on the itinerary inside metadata."""
        response: dict[str, Any] = {
            "type": "itinerary_results",
            "metadata": {
                "structured_itinerary": {
                    "itineraryItems": [
                        {
                            "day": 1,
                            "expandedContent": {
                                "activities": [{"location": "Senso-ji"}]
                            },
                        },
                        {
                            "day": 2,
                            "expandedContent": {
                                "activities": [{"location": "Tsukiji"}]
                            },
                        },
                    ]
                }
            },
        }

        attach_search_results_to_response(
            response,
            _side(
                flights=[{"id": "f1", "airline": "BA"}],
                hotels=[{"hotel_id": "h1", "hotel_name": "Mandarin"}],
            ),
            is_round_trip=True,
        )

        day1 = response["metadata"]["structured_itinerary"]["itineraryItems"][0][
            "expandedContent"
        ]["activities"]
        # Stitcher inserted flight + check-in at the top of Day 1
        assert day1[0]["kind"] == "flight"
        assert day1[0]["leg"] == "outbound"
        assert day1[1]["kind"] == "hotel-checkin"
        # LLM activity preserved after
        assert day1[2]["location"] == "Senso-ji"

    def test_no_structured_itinerary_still_attaches_top_level(self) -> None:
        """Response without structured_itinerary still gets top-level flights/hotels.

        Defensive — should never happen on the itinerary_results path, but if
        it does we don't crash; the FE rails still get their data.
        """
        response: dict[str, Any] = {"type": "itinerary_results", "metadata": {}}
        attach_search_results_to_response(
            response,
            _side(flights=[{"id": "f1"}], hotels=[{"hotel_id": "h1"}]),
            is_round_trip=False,
        )
        assert response["flights"] == [{"id": "f1"}]
        assert response["hotels"] == [{"hotel_id": "h1"}]


# ---------------------------------------------------------------------------
# _resolve_destination_for_hotel + _safe_hotel_search
#
# Issue #1076: PR #1071's previous resolver appended the MWGG-derived ISO-2
# country code into the geocoding query string ("Barcelona, ES"). Google
# interpreted "ES" as the Brazilian state Espírito Santo and returned a
# Brazilian village, so FlightLogic was searched for "Barcelona, Brazil"
# and threw HotelSearchError.
#
# The fix: geocode the destination ALONE — no country hint — and trust
# Google's relevance ranking to pick the right city. Hotel resolution now
# matches the frontend autocomplete and the hotel agent's resolve_city
# tool: one source of truth, one call, no ISO-2 collision class.
# ---------------------------------------------------------------------------


def _geo_result(
    *, lat: float, lng: float, country: str, city: str = "Lisbon"
) -> MagicMock:
    """Build a fake GeocodingResult-like object with the fields we read."""
    r = MagicMock()
    r.lat = lat
    r.lng = lng
    r.country = country
    r.city = city
    return r


class TestResolveDestinationForHotel:
    @pytest.mark.asyncio
    async def test_empty_destination_short_circuits_without_http_call(self) -> None:
        """Empty destination must return all None without instantiating
        GeocodingService — otherwise cold test envs incur a real call."""
        with patch("app.shared.geocoding.GeocodingService") as service_cls:
            assert await _resolve_destination_for_hotel("") == (None, None, None, None)
            service_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_city_country_and_coords_on_success(self) -> None:
        """Happy path: bare destination resolves to (city, country, lat, lng)."""
        geocode_city = AsyncMock(
            return_value=[
                _geo_result(lat=38.7223, lng=-9.1393, country="Portugal", city="Lisbon")
            ]
        )
        with patch("app.shared.geocoding.GeocodingService") as service_cls:
            service_cls.return_value.geocode_city = geocode_city
            assert await _resolve_destination_for_hotel("Lisbon") == (
                "Lisbon",
                "Portugal",
                38.7223,
                -9.1393,
            )
            # CRITICAL: no country hint ever appears in the query string — see
            # the issue #1076 regression test below for why.
            geocode_city.assert_awaited_once_with("Lisbon")

    @pytest.mark.asyncio
    async def test_geocode_query_never_includes_a_country_hint(self) -> None:
        """Regression for issue #1076.

        The old helper passed an ISO-2 country into the query ("Barcelona, ES")
        which Google misread as Espírito Santo, returning a Brazilian
        village. This test pins the resolver to the bare destination so the
        collision class can never come back.
        """
        geocode_city = AsyncMock(
            return_value=[
                _geo_result(lat=41.3851, lng=2.1734, country="Spain", city="Barcelona")
            ]
        )
        with patch("app.shared.geocoding.GeocodingService") as service_cls:
            service_cls.return_value.geocode_city = geocode_city
            await _resolve_destination_for_hotel("Barcelona")

        # Call site must never append a country/subdivision code to the
        # query. Soft assertion (no comma) on purpose — future cleanup is
        # free to rephrase the query as long as it doesn't reintroduce the
        # collision class.
        geocode_city.assert_awaited_once()
        (query,) = geocode_city.await_args.args
        assert "," not in query

    @pytest.mark.asyncio
    async def test_returns_all_none_on_empty_results(self) -> None:
        """Geocoding succeeded but returned 0 matches — caller falls back."""
        geocode_city = AsyncMock(return_value=[])
        with patch("app.shared.geocoding.GeocodingService") as service_cls:
            service_cls.return_value.geocode_city = geocode_city
            assert await _resolve_destination_for_hotel("NotARealPlace") == (
                None,
                None,
                None,
                None,
            )

    @pytest.mark.asyncio
    async def test_returns_all_none_and_logs_on_exception(self) -> None:
        """Geocoding raised (network / quota / bad key) — must not bubble up."""
        with patch("app.shared.geocoding.GeocodingService") as service_cls:
            service_cls.return_value.geocode_city = AsyncMock(
                side_effect=RuntimeError("Google Geocoding API quota exceeded")
            )
            assert await _resolve_destination_for_hotel("Lisbon") == (
                None,
                None,
                None,
                None,
            )


class TestSafeHotelSearchResolution:
    """``_safe_hotel_search`` reads trip_ctx, geocodes the destination once,
    and passes the geocoded city/country/coords to ``_do_hotel_search``.
    """

    @staticmethod
    def _ctx(**overrides: Any) -> dict[str, Any]:
        """trip_ctx shaped like the supervisor's pre_resolve_trip output."""
        ctx = {
            "destination": "Lisbon",
            "destination_country": "PT",
            "departure_date": "2026-06-01",
            "return_date": "2026-06-03",
            "adults": 2,
            "rooms": 1,
            "children": 0,
        }
        ctx.update(overrides)
        return ctx

    @pytest.mark.asyncio
    async def test_geocoded_city_country_and_coords_passed_through(self) -> None:
        """Happy path: ISO-2 in trip_ctx is *ignored*; geocoded country is used."""
        do_hotel = AsyncMock(return_value={"status": "no_results"})
        geocode_city = AsyncMock(
            return_value=[
                _geo_result(lat=38.7223, lng=-9.1393, country="Portugal", city="Lisbon")
            ]
        )
        with (
            patch(
                "app.ai.graph.tools.hotels._do_hotel_search",
                new=do_hotel,
            ),
            patch("app.shared.geocoding.GeocodingService") as service_cls,
        ):
            service_cls.return_value.geocode_city = geocode_city
            await _safe_hotel_search(self._ctx(), user_id="u1")

        do_hotel.assert_awaited_once()
        kwargs = do_hotel.await_args.kwargs
        assert kwargs["city_name"] == "Lisbon"
        assert kwargs["country_name"] == "Portugal"
        assert kwargs["nearby_lat"] == 38.7223
        assert kwargs["nearby_lng"] == -9.1393

    @pytest.mark.asyncio
    async def test_iso2_collision_resolved_correctly(self) -> None:
        """Issue #1076 end-to-end: Barcelona resolves to Spain, never Brazil.

        The old helper sent ``"Barcelona, ES"`` to Google, got back the
        Brazilian Espírito Santo Barcelona, and corrupted ``country_name``
        before FlightLogic ever saw it. The new helper sends ``"Barcelona"``
        alone, Google ranks Spain first, and FlightLogic gets the right
        country.
        """
        do_hotel = AsyncMock(return_value={"status": "no_results"})
        geocode_city = AsyncMock(
            return_value=[
                _geo_result(lat=41.3851, lng=2.1734, country="Spain", city="Barcelona")
            ]
        )
        ctx = self._ctx(destination="Barcelona", destination_country="ES")
        with (
            patch(
                "app.ai.graph.tools.hotels._do_hotel_search",
                new=do_hotel,
            ),
            patch("app.shared.geocoding.GeocodingService") as service_cls,
        ):
            service_cls.return_value.geocode_city = geocode_city
            await _safe_hotel_search(ctx, user_id="u1")

        # The MWGG-derived ISO-2 "ES" is discarded; the geocoded full name wins.
        kwargs = do_hotel.await_args.kwargs
        assert kwargs["country_name"] == "Spain"
        assert kwargs["country_name"] != "Brazil"
        assert kwargs["city_name"] == "Barcelona"
        # And the query Google saw never carried "ES" as a hint.
        (query,) = geocode_city.await_args.args
        assert query == "Barcelona"

    @pytest.mark.asyncio
    async def test_geocode_failure_falls_back_to_trip_ctx_values(self) -> None:
        """Graceful degradation: geocoding raises → fall back to trip_ctx
        destination + ISO-2 country (better than nothing; the local
        FlightLogic mock still accepts it in dev)."""
        do_hotel = AsyncMock(return_value={"status": "no_results"})
        with (
            patch(
                "app.ai.graph.tools.hotels._do_hotel_search",
                new=do_hotel,
            ),
            patch("app.shared.geocoding.GeocodingService") as service_cls,
        ):
            service_cls.return_value.geocode_city = AsyncMock(
                side_effect=RuntimeError("quota exceeded")
            )
            await _safe_hotel_search(self._ctx(), user_id="u1")

        kwargs = do_hotel.await_args.kwargs
        assert kwargs["city_name"] == "Lisbon"
        # Geocoding failed → trip_ctx's MWGG-derived ISO-2 is the fallback.
        assert kwargs["country_name"] == "PT"
        assert kwargs["nearby_lat"] is None
        assert kwargs["nearby_lng"] is None

    @pytest.mark.asyncio
    async def test_destination_search_city_used_for_country_input(self) -> None:
        """#1127: when the trip extractor recorded a country as the
        ``destination`` and a hub city as ``destination_search_city``, the
        hotel search must geocode and book against the HUB city, not the
        country label.  Mirrors the Montenegro → Kotor case."""
        do_hotel = AsyncMock(return_value={"status": "no_results"})
        geocode_city = AsyncMock(
            return_value=[
                _geo_result(
                    lat=42.4244,
                    lng=18.7710,
                    country="Montenegro",
                    city="Kotor",
                )
            ]
        )
        ctx = self._ctx(
            destination="Montenegro",
            destination_search_city="Kotor",
            destination_country="Montenegro",
        )
        with (
            patch(
                "app.ai.graph.tools.hotels._do_hotel_search",
                new=do_hotel,
            ),
            patch("app.shared.geocoding.GeocodingService") as service_cls,
        ):
            service_cls.return_value.geocode_city = geocode_city
            await _safe_hotel_search(ctx, user_id="u1")

        # Hotel search received the HUB city (Kotor), not "Montenegro".
        kwargs = do_hotel.await_args.kwargs
        assert kwargs["city_name"] == "Kotor"
        assert kwargs["country_name"] == "Montenegro"
        # And the geocoder was queried for Kotor, not Montenegro.
        (query,) = geocode_city.await_args.args
        assert query == "Kotor"


# ---------------------------------------------------------------------------
# Phase 3 O5 — pre-fired side-searches stash + pop + clear
# ---------------------------------------------------------------------------


class TestPreFiredSideSearchesStash:
    """Stash / pop / clear semantics for the pre-fired side-search dict."""

    def setup_method(self) -> None:
        """Clear the module-level stash so each test starts clean."""
        _PENDING_SIDE_SEARCHES.clear()

    def teardown_method(self) -> None:
        """Cancel any remaining tasks so they don't bleed into the next test."""
        for chat_id in list(_PENDING_SIDE_SEARCHES.keys()):
            clear_pending_side_searches(chat_id)

    @pytest.mark.asyncio
    async def test_stash_and_pop_roundtrip(self) -> None:
        """A stashed pair pops out exactly once and the dict empties."""
        import asyncio

        async def _placeholder() -> dict[str, Any] | None:
            return {"status": "success"}

        flight_task = asyncio.create_task(_placeholder())
        hotel_task = asyncio.create_task(_placeholder())

        stash_pending_side_searches("chat-1", flight_task, hotel_task)
        assert "chat-1" in _PENDING_SIDE_SEARCHES

        popped_flight, popped_hotel = pop_pending_side_searches("chat-1")
        assert popped_flight is flight_task
        assert popped_hotel is hotel_task
        # Pop drains the stash.
        assert "chat-1" not in _PENDING_SIDE_SEARCHES

        # Second pop on the same chat returns (None, None) so the caller
        # knows to fire its own side-searches.
        again_flight, again_hotel = pop_pending_side_searches("chat-1")
        assert again_flight is None
        assert again_hotel is None

        await flight_task
        await hotel_task

    @pytest.mark.asyncio
    async def test_clear_cancels_pending_tasks(self) -> None:
        """clear_pending_side_searches must cancel in-flight tasks so they
        don't leak when the user pivots to a non-itinerary agent."""
        import asyncio

        async def _slow_task() -> dict[str, Any] | None:
            await asyncio.sleep(10)
            return None

        flight_task = asyncio.create_task(_slow_task())
        hotel_task = asyncio.create_task(_slow_task())

        stash_pending_side_searches("chat-cancel", flight_task, hotel_task)
        clear_pending_side_searches("chat-cancel")

        # Give the event loop one tick so the cancellation actually lands.
        await asyncio.sleep(0)

        assert flight_task.cancelled() or flight_task.done()
        assert hotel_task.cancelled() or hotel_task.done()
        assert "chat-cancel" not in _PENDING_SIDE_SEARCHES

    @pytest.mark.asyncio
    async def test_clear_is_no_op_for_unknown_chat(self) -> None:
        """Calling clear on a chat_id that was never stashed must not raise."""
        clear_pending_side_searches("never-stashed")  # no exception

    @pytest.mark.asyncio
    async def test_stash_overwrites_and_cancels_previous(self) -> None:
        """If the same chat_id stashes twice (rare: re-route during one turn),
        the old tasks must be cancelled to avoid leaking."""
        import asyncio

        async def _slow_task() -> dict[str, Any] | None:
            await asyncio.sleep(10)
            return None

        old_flight = asyncio.create_task(_slow_task())
        old_hotel = asyncio.create_task(_slow_task())
        stash_pending_side_searches("chat-x", old_flight, old_hotel)

        new_flight = asyncio.create_task(_slow_task())
        new_hotel = asyncio.create_task(_slow_task())
        stash_pending_side_searches("chat-x", new_flight, new_hotel)

        # Give cancellation one event-loop tick to land.
        await asyncio.sleep(0)
        assert old_flight.cancelled() or old_flight.done()
        assert old_hotel.cancelled() or old_hotel.done()
        popped_flight, popped_hotel = pop_pending_side_searches("chat-x")
        assert popped_flight is new_flight
        assert popped_hotel is new_hotel

        # Clean up to avoid leaks.
        for t in (popped_flight, popped_hotel):
            if t is not None:
                t.cancel()
