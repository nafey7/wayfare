"""Unit tests for country-as-destination resolution (#1127).

When the user names a country instead of a city ("Montenegro", "Iceland",
"Morocco") the existing flow had two problems:

1. ``resolve_airport`` fuzzy-matches the country name to an unrelated
   airport (in dev, "Montenegro" → QGF in Brazil), populating bogus
   ``destination_iata`` / ``destination_country`` on the trip context.
2. ``_safe_hotel_search`` passes ``city_name="Montenegro"`` to FlightLogic,
   which rejects it (the API requires a real city).

The fix splits the destination into TWO fields:
- ``destination`` stays as the user wrote it ("Montenegro") so the itinerary
  LLM still produces a multi-city country-wide plan.
- ``destination_search_city`` carries a curated tourist hub ("Kotor") used
  by the flight + hotel side-searches.

These tests exercise the resolution logic in
``itinerary_trip_extractor.extract_and_resolve`` and the static map in
``country_to_city``.  We mock the geocoder + airport resolver so the suite
exercises orchestration without hitting external APIs.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.graph.country_to_city import lookup_country_tourist_hub
from app.ai.graph.itinerary_trip_extractor import (
    TripParamsExtraction,
    extract_and_resolve,
)

# ---------------------------------------------------------------------------
# Helpers — kept narrow on purpose; happy-path tests already live in
# ``test_itinerary_trip_extractor.py`` and we don't want to duplicate them.
# ---------------------------------------------------------------------------


def _country_extraction(country: str) -> TripParamsExtraction:
    """Extraction shaped like the user typed only a country destination."""
    return TripParamsExtraction(
        origin_city=None,
        destination_city=country,
        date_expression="July 20 for 2 weeks",
        adults=2,
        children=2,
        infants=0,
        trip_type="round-trip",
    )


def _dates_resolved(
    departure: str = "2026-07-20",
    return_date: str = "2026-08-02",
) -> dict[str, Any]:
    return {
        "departure_date": departure,
        "return_date": return_date,
        "is_range": True,
        "error": None,
    }


def _patch_extraction(extracted: TripParamsExtraction) -> Any:
    return patch(
        "app.ai.graph.itinerary_trip_extractor._extract_with_llm",
        new=AsyncMock(return_value=extracted),
    )


def _patch_resolve_airport(side_effect: Any) -> Any:
    tool_mock = MagicMock()
    tool_mock.ainvoke = AsyncMock(side_effect=side_effect)
    return patch("app.ai.graph.tools.airport.resolve_airport", new=tool_mock)


def _patch_parse_dates(return_value: Any) -> Any:
    tool_mock = MagicMock()
    tool_mock.ainvoke = AsyncMock(return_value=return_value)
    return patch("app.ai.graph.tools.dates.parse_dates", new=tool_mock)


def _patch_destination_country_check(returns_true: bool) -> Any:
    """Force ``_is_destination_country_only`` to return True/False."""
    return patch(
        "app.ai.graph.itinerary_trip_extractor._is_destination_country_only",
        new=AsyncMock(return_value=returns_true),
    )


# ---------------------------------------------------------------------------
# Static map (country_to_city.lookup_country_tourist_hub)
# ---------------------------------------------------------------------------


class TestStaticMap:
    def test_montenegro_resolves_to_kotor_TIV(self) -> None:
        hub = lookup_country_tourist_hub("Montenegro")
        assert hub == ("Kotor", "TIV", "Montenegro")

    def test_lookup_is_case_insensitive(self) -> None:
        assert lookup_country_tourist_hub("montenegro") == lookup_country_tourist_hub(
            "MONTENEGRO"
        )
        assert lookup_country_tourist_hub("montenegro") == lookup_country_tourist_hub(
            "Montenegro"
        )

    def test_leading_article_is_stripped(self) -> None:
        """'the UK' / 'the US' / 'the Netherlands' should all hit the table."""
        assert lookup_country_tourist_hub("the UK") == lookup_country_tourist_hub("UK")
        assert lookup_country_tourist_hub("the US") == lookup_country_tourist_hub("US")
        assert lookup_country_tourist_hub(
            "the Netherlands"
        ) == lookup_country_tourist_hub("Netherlands")

    def test_unknown_country_returns_none(self) -> None:
        assert lookup_country_tourist_hub("Mars") is None
        assert lookup_country_tourist_hub("Atlantis") is None

    def test_empty_input_returns_none(self) -> None:
        assert lookup_country_tourist_hub("") is None
        assert lookup_country_tourist_hub("   ") is None

    def test_uk_variants_all_map_to_london(self) -> None:
        """User phrasings 'UK' / 'England' / 'Great Britain' / 'United Kingdom'
        should all map to the same hub."""
        for q in ("UK", "England", "Great Britain", "United Kingdom"):
            hub = lookup_country_tourist_hub(q)
            assert hub is not None, q
            assert hub[0] == "London"
            assert hub[1] == "LHR"

    def test_known_countries_have_three_letter_iata(self) -> None:
        """Sanity-check that every entry uses a 3-letter IATA code.

        Catches typos like ``"LHRR"`` or a swapped name/iata when adding
        new entries to the map.
        """
        from app.ai.graph.country_to_city import _COUNTRY_TOURIST_HUBS

        for country, (country_name, hubs) in _COUNTRY_TOURIST_HUBS.items():
            assert country_name, f"{country!r}: empty country_name"
            assert hubs, f"{country!r}: hub list must not be empty"
            for city, iata in hubs:
                assert city, f"{country!r}: empty city in hub list"
                assert len(iata) == 3, (
                    f"{country!r}/{city!r}: IATA {iata!r} wrong length"
                )
                assert iata.isalpha(), (
                    f"{country!r}/{city!r}: IATA {iata!r} not alphabetic"
                )
                assert iata.isupper(), (
                    f"{country!r}/{city!r}: IATA {iata!r} not uppercase"
                )


# ---------------------------------------------------------------------------
# extract_and_resolve — country destination path
# ---------------------------------------------------------------------------


class TestCountryDestinationPath:
    @pytest.mark.asyncio
    async def test_montenegro_uses_kotor_hub_for_search(self) -> None:
        """Montenegro should resolve to Kotor / TIV for side-searches while
        ``destination`` keeps the country label."""
        # Airport resolver returns the bogus QGF/BR fuzzy match (real dev
        # behaviour observed in #1127). The country-check kicks in and
        # discards it in favour of the curated hub.
        airport_results = [
            {"status": "resolved", "iata": "QGF", "country": "BR"},
        ]
        with (
            _patch_extraction(_country_extraction("Montenegro")),
            _patch_resolve_airport(airport_results),
            _patch_parse_dates(_dates_resolved()),
            _patch_destination_country_check(True),
        ):
            result = await extract_and_resolve(
                "Plan a summer holiday to Montenegro starting July 20 for 2 weeks"
            )

        # Itinerary destination is preserved exactly as the user wrote it.
        assert result["destination"] == "Montenegro"
        # Side-search city comes from the hub map, NOT the airport resolver.
        assert result["destination_search_city"] == "Kotor"
        # IATA + country are OVERRIDDEN — the QGF/BR fuzzy match is gone.
        assert result["destination_iata"] == "TIV"
        assert result["destination_country"] == "Montenegro"
        # The country flag is recorded so downstream code can branch on it.
        assert result["destination_is_country"] is True

    @pytest.mark.asyncio
    async def test_country_with_no_static_map_drops_bogus_iata(self) -> None:
        """Long-tail country (not in the static map) must NOT keep the
        airport resolver's likely-bogus fuzzy match — the side-searches
        should skip silently instead."""
        airport_results = [
            # Imagine the resolver fuzzy-matched some obscure airport in
            # the wrong country — we still want to throw it away.
            {"status": "resolved", "iata": "XXX", "country": "ZZ"},
        ]
        with (
            _patch_extraction(_country_extraction("Atlantis")),
            _patch_resolve_airport(airport_results),
            _patch_parse_dates(_dates_resolved()),
            _patch_destination_country_check(True),
        ):
            result = await extract_and_resolve("Plan a trip to Atlantis for 2 weeks")

        assert result["destination"] == "Atlantis"
        # Flag still set so callers know this was a country.
        assert result["destination_is_country"] is True
        # IATA / country dropped to avoid bad downstream searches.
        assert "destination_iata" not in result
        assert "destination_country" not in result
        # No search city populated → hotel side-search will skip silently.
        assert "destination_search_city" not in result

    @pytest.mark.asyncio
    async def test_city_destination_unchanged_by_country_path(self) -> None:
        """City destinations (Tokyo, Paris) must not be touched by the
        country-hub code path — no extra fields, IATA from the resolver."""
        extraction = TripParamsExtraction(
            origin_city=None,
            destination_city="Tokyo",
            date_expression="June 20",
            adults=1,
        )
        airport_results = [{"status": "resolved", "iata": "HND", "country": "JP"}]
        with (
            _patch_extraction(extraction),
            _patch_resolve_airport(airport_results),
            _patch_parse_dates(_dates_resolved(return_date="2026-06-25")),
            _patch_destination_country_check(False),  # geocoder said "city"
        ):
            result = await extract_and_resolve("Take me to Tokyo on June 20")

        assert result["destination"] == "Tokyo"
        assert result["destination_iata"] == "HND"
        assert result["destination_country"] == "JP"
        # No country-only fields polluting the city path.
        assert "destination_is_country" not in result
        assert "destination_search_city" not in result


# ---------------------------------------------------------------------------
# Region inputs (Europe / Caribbean) must NOT take the country path
# ---------------------------------------------------------------------------


class TestRegionStaysOutOfCountryPath:
    """Regions ("Europe", "the Caribbean") already have their own deterministic
    gate in ``tools/itinerary.py``. They're geographically countries-of-countries
    so Google Geocoding returns no ``locality`` AND no ``country`` for them —
    ``_is_destination_country_only`` therefore returns False and the region
    gate downstream keeps its existing semantics (refuse + ask for a city).

    This test pins that behaviour so the country path doesn't accidentally
    swallow region inputs.
    """

    @pytest.mark.asyncio
    async def test_europe_does_not_get_hub_resolution(self) -> None:
        extraction = TripParamsExtraction(
            origin_city=None,
            destination_city="Europe",
            date_expression="next month for 5 days",
            adults=1,
        )
        with (
            _patch_extraction(extraction),
            _patch_resolve_airport(
                [{"status": "not_found"}]
            ),  # resolver won't find an IATA for "Europe"
            _patch_parse_dates(_dates_resolved()),
            # Geocoder reports neither country nor locality for "Europe" →
            # the country path should NOT activate. We simulate that here by
            # forcing the check to return False.
            _patch_destination_country_check(False),
        ):
            result = await extract_and_resolve("Plan a 5-day Europe city break")

        assert result["destination"] == "Europe"
        # Hub fields must stay absent — region guard downstream owns this case.
        assert "destination_search_city" not in result
        assert "destination_is_country" not in result
        # IATA absent since resolver returned not_found AND country path
        # didn't run.
        assert "destination_iata" not in result


# ---------------------------------------------------------------------------
# #1127 follow-up — bare-location reply fast-path
#
# When the agent asks "Departing from?" and the user replies with a 1-3 word
# location string ("Dubai", "Mumbai International", "DXB"), the extractor LLM
# in isolation can't tell if it's origin or destination — and on the
# follow-up turn it may even output nothing. This fast-path treats such
# replies as origin candidates ONLY when trip_ctx shows we're explicitly
# waiting for origin (destination + dates set, no origin_iata yet).
# ---------------------------------------------------------------------------


class TestBareLocationOriginFallback:
    @pytest.mark.asyncio
    async def test_dubai_reply_resolves_to_DXB_origin(self) -> None:
        """The #1127 user-reported case: after the agent asks for origin,
        a bare 'Dubai' reply must resolve to DXB and populate origin_iata —
        without going through the extractor LLM."""
        existing_trip = {
            "destination": "Montenegro",
            "destination_iata": "TIV",
            "destination_search_city": "Kotor",
            "destination_country": "Montenegro",
            "destination_is_country": True,
            "departure_date": "2026-07-20",
            "return_date": "2026-08-02",
        }
        airport_results = [{"status": "resolved", "iata": "DXB", "country": "AE"}]

        with (
            _patch_resolve_airport(airport_results),
            _patch_parse_dates({"departure_date": None, "return_date": None}),
            _patch_destination_country_check(False),
            patch(
                "app.ai.graph.itinerary_trip_extractor._extract_with_llm",
                new=AsyncMock(),  # would fail the test if called
            ) as llm_mock,
            patch(
                "app.ai.graph.itinerary_trip_extractor._is_country_only",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await extract_and_resolve("Dubai", existing_trip=existing_trip)

        # The fast-path skipped the LLM entirely.
        assert llm_mock.await_count == 0
        # origin resolved end-to-end.
        assert result["origin"] == "Dubai"
        assert result["origin_iata"] == "DXB"

    @pytest.mark.asyncio
    async def test_conversational_reply_does_not_fire(self) -> None:
        """'yes' / 'thanks' / 'sure' are conversational acks, NOT origins —
        the fast-path heuristic must reject them so we don't resolve random
        strings as airports."""
        existing_trip = {
            "destination": "Montenegro",
            "destination_iata": "TIV",
            "departure_date": "2026-07-20",
        }
        # If the heuristic incorrectly fires, resolve_airport will be called.
        # We assert it isn't.
        resolve_mock = MagicMock()
        resolve_mock.ainvoke = AsyncMock(return_value={"status": "not_found"})
        extractor_mock = AsyncMock(
            return_value=TripParamsExtraction(
                origin_city=None,
                destination_city=None,
                date_expression=None,
                adults=None,
                children=None,
                infants=None,
                trip_type=None,
            )
        )

        with (
            patch(
                "app.ai.graph.tools.airport.resolve_airport",
                new=resolve_mock,
            ),
            _patch_parse_dates({"departure_date": None, "return_date": None}),
            patch(
                "app.ai.graph.itinerary_trip_extractor._extract_with_llm",
                new=extractor_mock,
            ),
            patch(
                "app.ai.graph.itinerary_trip_extractor._is_country_only",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await extract_and_resolve("thanks", existing_trip=existing_trip)

        # No origin extracted, no airport lookup fired for the bare reply.
        assert "origin" not in result
        assert "origin_iata" not in result
        # LLM was the path taken — fallback didn't short-circuit it.
        assert extractor_mock.await_count == 1

    @pytest.mark.asyncio
    async def test_fallback_inactive_on_cold_turn(self) -> None:
        """On a cold turn (no existing trip context) the fallback must NOT
        steal location-shaped messages — the LLM still owns extraction so it
        can correctly assign origin vs destination based on context.

        Example: "Tokyo" on a cold turn could be either origin OR destination —
        the LLM decides. Our fallback only fires when we're explicitly waiting
        for origin (destination + dates already in trip_ctx)."""
        extractor_mock = AsyncMock(
            return_value=TripParamsExtraction(
                origin_city=None,
                destination_city="Tokyo",
                date_expression=None,
                adults=None,
                children=None,
                infants=None,
                trip_type=None,
            )
        )

        with (
            patch(
                "app.ai.graph.itinerary_trip_extractor._extract_with_llm",
                new=extractor_mock,
            ),
            _patch_resolve_airport([{"status": "resolved", "iata": "HND"}]),
            _patch_parse_dates({"departure_date": None, "return_date": None}),
            patch(
                "app.ai.graph.itinerary_trip_extractor._is_country_only",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "app.ai.graph.itinerary_trip_extractor._is_destination_country_only",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await extract_and_resolve("Tokyo", existing_trip=None)

        # LLM ran (no fallback short-circuit).
        assert extractor_mock.await_count == 1
        # Tokyo treated as destination per the LLM's call.
        assert result.get("destination") == "Tokyo"
        # No origin — fallback didn't fire because cold turn.
        assert "origin" not in result

    @pytest.mark.asyncio
    async def test_sentence_reply_does_not_fire_fast_path(self) -> None:
        """Multi-word sentences ('I'm in Dubai', 'flying from Dubai') must
        fall through to the LLM extractor rather than the bare-location
        fast-path — the LLM can interpret the sentence properly."""
        existing_trip = {
            "destination": "Montenegro",
            "destination_iata": "TIV",
            "departure_date": "2026-07-20",
        }
        extractor_mock = AsyncMock(
            return_value=TripParamsExtraction(
                origin_city="Dubai",  # LLM correctly extracted from sentence
                destination_city=None,
                date_expression=None,
                adults=None,
                children=None,
                infants=None,
                trip_type=None,
            )
        )

        with (
            patch(
                "app.ai.graph.itinerary_trip_extractor._extract_with_llm",
                new=extractor_mock,
            ),
            _patch_resolve_airport([{"status": "resolved", "iata": "DXB"}]),
            _patch_parse_dates({"departure_date": None, "return_date": None}),
            patch(
                "app.ai.graph.itinerary_trip_extractor._is_country_only",
                new=AsyncMock(return_value=False),
            ),
        ):
            result = await extract_and_resolve(
                "I'm flying from Dubai", existing_trip=existing_trip
            )

        # LLM was used (sentence → not a bare-location reply).
        assert extractor_mock.await_count == 1
        assert result["origin_iata"] == "DXB"
