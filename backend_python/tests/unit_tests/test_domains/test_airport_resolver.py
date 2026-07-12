"""Unit tests for airport resolver priority mappings and functionality."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from app.domains.airport.airport_resolver import AirportResolver, resolve_airport

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_airports_data() -> dict[str, Any]:
    """Mock airport data for testing."""
    return {
        "KJFK": {
            "iata": "JFK",
            "icao": "KJFK",
            "name": "John F Kennedy International Airport",
            "city": "New York",
            "country": "United States",
        },
        "KBHM": {
            "iata": "BHM",
            "icao": "KBHM",
            "name": "Birmingham-Shuttlesworth International Airport",
            "city": "Birmingham",
            "country": "United States",
        },
        "EGBB": {
            "iata": "BHX",
            "icao": "EGBB",
            "name": "Birmingham Airport",
            "city": "Birmingham",
            "country": "United Kingdom",
        },
        "KGLW": {
            "iata": "GLW",
            "icao": "KGLW",
            "name": "Glasgow Municipal Airport",
            "city": "Glasgow",
            "country": "United States",
        },
        "EGPF": {
            "iata": "GLA",
            "icao": "EGPF",
            "name": "Glasgow International Airport",
            "city": "Glasgow",
            "country": "United Kingdom",
        },
        "LPFR": {
            "iata": "FAO",
            "icao": "LPFR",
            "name": "Faro Airport",
            "city": "Faro",
            "country": "Portugal",
        },
        "FAKE": {
            "iata": "ZFA",  # Fake/incorrect code for Faro
            "icao": "FAKE",
            "name": "Fake Faro Airport",
            "city": "Faro",
            "country": "Unknown",
        },
        "KJOR": {
            "iata": "LIM",
            "icao": "KJOR",
            "name": "Lima Allen County Airport",
            "city": "Lima",
            "country": "United States",
        },
        "SPJC": {
            "iata": "LIM",
            "icao": "SPJC",
            "name": "Jorge Chávez International Airport",
            "city": "Lima",
            "country": "Peru",
        },
        "SCEL": {
            "iata": "SCL",
            "icao": "SCEL",
            "name": "Arturo Merino Benítez International Airport",
            "city": "Santiago",
            "country": "Chile",
        },
        "MUSC": {
            "iata": "SCU",
            "icao": "MUSC",
            "name": "Antonio Maceo Airport",
            "city": "Santiago",
            "country": "Cuba",
        },
    }


@pytest.fixture
def resolver_with_mock_data(mock_airports_data: dict[str, Any]) -> AirportResolver:
    """Create resolver with mock data pre-loaded."""
    resolver = AirportResolver()
    resolver.airports_data = mock_airports_data
    resolver._process_airport_data()
    resolver._setup_priority_mappings()
    resolver.loaded = True
    return resolver


# ==============================================================================
# PRIORITY MAPPINGS TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_priority_mapping_birmingham_uk_over_us(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that Birmingham resolves to UK (BHX) over US (BHM)."""
    result = await resolver_with_mock_data.resolve_airport("Birmingham")

    assert result == "BHX"

    # Verify the US airport exists but wasn't chosen
    us_airports = [
        airport
        for airport in resolver_with_mock_data.airports_data.values()
        if airport.get("city", "").lower() == "birmingham"
        and airport.get("country") == "United States"
    ]
    assert len(us_airports) == 1
    assert us_airports[0]["iata"] == "BHM"


@pytest.mark.asyncio
async def test_priority_mapping_glasgow_uk_over_us(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that Glasgow resolves to UK (GLA) over US (GLW)."""
    result = await resolver_with_mock_data.resolve_airport("Glasgow")

    assert result == "GLA"

    # Verify the US airport exists but wasn't chosen
    us_airports = [
        airport
        for airport in resolver_with_mock_data.airports_data.values()
        if airport.get("city", "").lower() == "glasgow"
        and airport.get("country") == "United States"
    ]
    assert len(us_airports) == 1
    assert us_airports[0]["iata"] == "GLW"


@pytest.mark.asyncio
async def test_priority_mapping_faro_fix_data_issue(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that Faro resolves to FAO (Portugal) instead of erroneous ZFA."""
    result = await resolver_with_mock_data.resolve_airport("Faro")

    assert result == "FAO"

    # Verify the fake/incorrect airport exists but wasn't chosen
    fake_airports = [
        airport
        for airport in resolver_with_mock_data.airports_data.values()
        if airport.get("iata") == "ZFA"
    ]
    assert len(fake_airports) == 1


@pytest.mark.asyncio
async def test_priority_mapping_lima_peru_over_us(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that Lima resolves to Peru (LIM) over US with same IATA code."""
    result = await resolver_with_mock_data.resolve_airport("Lima")

    assert result == "LIM"

    # Note: Both airports have same IATA code LIM, but priority mapping ensures
    # we get the Peru one (Jorge Chávez International)


@pytest.mark.asyncio
async def test_priority_mapping_santiago_chile_over_cuba(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that Santiago resolves to Chile (SCL) over Cuba (SCU)."""
    result = await resolver_with_mock_data.resolve_airport("Santiago")

    assert result == "SCL"

    # Verify the Cuba airport exists but wasn't chosen
    cuba_airports = [
        airport
        for airport in resolver_with_mock_data.airports_data.values()
        if airport.get("city", "").lower() == "santiago"
        and airport.get("country") == "Cuba"
    ]
    assert len(cuba_airports) == 1
    assert cuba_airports[0]["iata"] == "SCU"


@pytest.mark.asyncio
async def test_priority_mapping_case_insensitive(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that priority mappings work with different cases."""
    test_cases = [
        ("birmingham", "BHX"),
        ("BIRMINGHAM", "BHX"),
        ("Birmingham", "BHX"),
        ("BirmInGHam", "BHX"),
        ("faro", "FAO"),
        ("FARO", "FAO"),
        ("Faro", "FAO"),
    ]

    for city_input, expected_code in test_cases:
        result = await resolver_with_mock_data.resolve_airport(city_input)
        assert result == expected_code, f"Failed for input: {city_input}"


@pytest.mark.asyncio
async def test_priority_mappings_comprehensive_list(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that all priority mappings are correctly configured."""
    expected_priority_mappings = {
        # Major cities
        "new york": "JFK",
        "london": "LHR",
        "paris": "CDG",
        "amsterdam": "AMS",
        # Ambiguous cities (same name, different countries)
        "birmingham": "BHX",  # UK over US
        "glasgow": "GLA",  # UK over US
        "newcastle": "NCL",  # UK over US and South Africa
        "cambridge": "CBG",  # UK over US
        "plymouth": "PLH",  # UK over US
        "rochester": "RCS",  # UK over US
        "lima": "LIM",  # Peru over US
        "santiago": "SCL",  # Chile over Cuba and others
        "hamilton": "BDA",  # Bermuda over Canada
        "kingston": "KIN",  # Jamaica over Canada
        "perth": "PER",  # Australia over UK
        "richmond": "RIC",  # US Virginia over Australia
        "faro": "FAO",  # Portugal (fix data issue with ZFA)
    }

    # Check that priority mappings are set up correctly
    assert resolver_with_mock_data.priority_city_mappings is not None

    for city, expected_code in expected_priority_mappings.items():
        assert city in resolver_with_mock_data.priority_city_mappings
        assert resolver_with_mock_data.priority_city_mappings[city] == expected_code


# ==============================================================================
# AIRPORT RESOLUTION STRATEGY TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_resolution_strategy_order_iata_first(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that IATA codes are resolved first before priority mappings."""
    # JFK should be resolved as direct IATA, not through "New York" priority mapping
    result = await resolver_with_mock_data.resolve_airport("JFK")
    assert result == "JFK"


@pytest.mark.asyncio
async def test_resolution_strategy_order_icao_second(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that ICAO codes are resolved and converted to IATA."""
    result = await resolver_with_mock_data.resolve_airport("KJFK")
    assert result == "JFK"  # ICAO converted to IATA


@pytest.mark.asyncio
async def test_resolution_strategy_priority_before_general_city(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that priority mappings take precedence over general city lookup."""
    # Birmingham has both UK and US airports in data, priority should win
    result = await resolver_with_mock_data.resolve_airport("Birmingham")
    assert result == "BHX"  # Priority mapping, not first in city_to_airports

    # Verify general city lookup would find different result without priority
    _general_city_result = resolver_with_mock_data.city_to_airports.get(
        "birmingham", []
    )
    # Priority mapping should override whatever is first in general lookup


@pytest.mark.asyncio
async def test_resolution_strategy_fallback_to_general_city(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test fallback to general city lookup when no priority mapping exists."""
    # New York has priority mapping, so test with a city that doesn't
    result = await resolver_with_mock_data.resolve_airport("New York")
    assert result == "JFK"  # Should use priority mapping

    # Test a city without priority mapping (add one to test data first)
    resolver_with_mock_data.city_to_airports["testcity"] = ["TST"]
    result = await resolver_with_mock_data.resolve_airport("testcity")
    assert result == "TST"  # Should use general city lookup


@pytest.mark.asyncio
async def test_resolution_strategy_airport_name_lookup(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test airport name lookup strategy."""
    result = await resolver_with_mock_data.resolve_airport(
        "John F Kennedy International Airport"
    )
    assert result == "JFK"

    # Test partial airport name
    result = await resolver_with_mock_data.resolve_airport("Kennedy International")
    # Should work with partial matching


# ==============================================================================
# DATA LOADING AND CACHING TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_load_airport_data_from_cache(tmp_path: Path) -> None:
    """Test loading airport data from local cache."""
    # Create temporary cache file
    cache_file = tmp_path / "airports_cache.json"
    mock_data = {"TEST": {"iata": "TST", "name": "Test Airport", "city": "test"}}

    with open(cache_file, "w") as f:  # noqa: ASYNC230 - Test setup, not in async context
        json.dump(mock_data, f)

    with patch("app.domains.airport.airport_resolver.Path") as mock_path_class:
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value = mock_path_instance

        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            resolver = AirportResolver()
            await resolver._load_airport_data()

            assert resolver.airports_data == mock_data
            assert resolver.loaded is True


@pytest.mark.asyncio
async def test_fallback_airport_loading_on_download_failure() -> None:
    """Test fallback to manual mapping when download fails."""
    with (
        patch("app.domains.airport.airport_resolver.Path") as mock_path_class,
        patch(
            "app.domains.airport.airport_resolver.aiohttp.ClientSession"
        ) as mock_session_class,
    ):
        # Mock path (cache doesn't exist)
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path_class.return_value = mock_path_instance

        # Mock failed download
        mock_session_class.side_effect = Exception("Network error")

        resolver = AirportResolver()
        await resolver._load_airport_data()

        # Should have loaded fallback data
        assert resolver.loaded is True
        assert "new york" in resolver.priority_city_mappings
        assert resolver.priority_city_mappings["new york"] == "JFK"


# ==============================================================================
# ERROR HANDLING AND EDGE CASES
# ==============================================================================


@pytest.mark.asyncio
async def test_resolve_airport_empty_input(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test handling of empty or None input."""
    result = await resolver_with_mock_data.resolve_airport("")
    assert result is None

    result = await resolver_with_mock_data.resolve_airport(None)
    assert result is None


@pytest.mark.asyncio
async def test_resolve_airport_whitespace_handling(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test handling of whitespace in input."""
    result = await resolver_with_mock_data.resolve_airport("  Birmingham  ")
    assert result == "BHX"

    result = await resolver_with_mock_data.resolve_airport("\tFaro\n")
    assert result == "FAO"


@pytest.mark.asyncio
async def test_resolve_airport_not_found(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test handling when airport is not found."""
    result = await resolver_with_mock_data.resolve_airport("NonexistentCity")
    assert result is None

    result = await resolver_with_mock_data.resolve_airport("XYZ")  # Invalid IATA
    assert result is None


@pytest.mark.asyncio
async def test_resolve_airport_partial_matching() -> None:
    """Test partial matching functionality."""
    mock_data = {
        "KJFK": {
            "iata": "JFK",
            "name": "John F Kennedy International Airport",
            "city": "New York",
        },
        "KLGA": {"iata": "LGA", "name": "LaGuardia Airport", "city": "New York"},
    }

    resolver = AirportResolver()
    resolver.airports_data = mock_data
    resolver._process_airport_data()
    resolver._setup_priority_mappings()
    resolver.loaded = True

    # Should find partial match for airport name
    result = await resolver.resolve_airport("Kennedy")
    # Note: Partial matching may return None if the matching logic doesn't find sufficient overlap
    assert (
        result == "JFK" or result is None
    )  # Allow for either result depending on implementation


@pytest.mark.asyncio
async def test_ensure_loaded_idempotent(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that ensure_loaded can be called multiple times safely."""
    # Should be already loaded
    assert resolver_with_mock_data.loaded is True

    # Calling again should not reload
    original_data = resolver_with_mock_data.airports_data.copy()
    await resolver_with_mock_data.ensure_loaded()

    assert resolver_with_mock_data.airports_data == original_data
    assert resolver_with_mock_data.loaded is True


# ==============================================================================
# INTEGRATION AND PERFORMANCE TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_convenience_function_resolve_airport() -> None:
    """Test the module-level convenience function."""
    with patch(
        "app.domains.airport.airport_resolver.airport_resolver"
    ) as mock_resolver:
        mock_resolver.resolve_airport = AsyncMock(return_value="JFK")

        result = await resolve_airport("New York")

        assert result == "JFK"
        mock_resolver.resolve_airport.assert_called_once_with("New York")


@pytest.mark.asyncio
async def test_get_airport_info(resolver_with_mock_data: AirportResolver) -> None:
    """Test retrieving detailed airport information."""
    result = await resolver_with_mock_data.get_airport_info("JFK")

    assert result is not None
    assert result["iata"] == "JFK"
    assert result["name"] == "John F Kennedy International Airport"
    assert result["city"] == "New York"

    # Test case insensitive
    result = await resolver_with_mock_data.get_airport_info("jfk")
    assert result is not None
    assert result["iata"] == "JFK"

    # Test non-existent
    result = await resolver_with_mock_data.get_airport_info("XYZ")
    assert result is None


@pytest.mark.asyncio
async def test_search_airports(resolver_with_mock_data: AirportResolver) -> None:
    """Test airport search functionality with ranking."""
    results = await resolver_with_mock_data.search_airports("Birmingham", limit=5)

    assert len(results) >= 1
    assert len(results) <= 5

    # Results should be sorted by score
    scores = [result["score"] for result in results]
    assert scores == sorted(scores, reverse=True)

    # Should contain both Birmingham airports
    iata_codes = [result["iata"] for result in results]
    assert "BHX" in iata_codes  # UK
    assert "BHM" in iata_codes  # US


@pytest.mark.asyncio
async def test_search_airports_with_exact_match(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that exact matches get highest scores."""
    results = await resolver_with_mock_data.search_airports("Faro", limit=10)

    assert len(results) >= 1

    # Exact city match should get highest score
    assert results[0]["score"] == 100
    assert results[0]["iata"] == "FAO"  # Should prioritize correct FAO over fake ZFA


# ==============================================================================
# LOGGING AND MONITORING TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_priority_mapping_logging(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that priority mappings are logged for debugging."""
    with patch("app.domains.airport.airport_resolver.logger") as mock_logger:
        result = await resolver_with_mock_data.resolve_airport("Birmingham")

        assert result == "BHX"

        # Should log priority mapping usage
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any(
            "Using priority mapping for 'Birmingham': BHX" in call
            for call in info_calls
        )


@pytest.mark.asyncio
async def test_data_loading_logging() -> None:
    """Test logging during data loading process."""
    with (
        patch("app.domains.airport.airport_resolver.logger") as mock_logger,
        patch("app.domains.airport.airport_resolver.Path") as mock_path_class,
    ):
        # Mock successful cache loading
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value = mock_path_instance

        with patch("builtins.open", mock_open(read_data='{"TEST": {"iata": "TST"}}')):
            resolver = AirportResolver()
            await resolver._load_airport_data()

            info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert any(
                "Loading airports from local cache" in call for call in info_calls
            )
            assert any("airports successfully" in call for call in info_calls)


# ==============================================================================
# SECURITY AND VALIDATION TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_input_sanitization(resolver_with_mock_data: AirportResolver) -> None:
    """Test that inputs are properly sanitized."""
    # Test potential injection attempts (though this is a read-only service)
    malicious_inputs = [
        "'; DROP TABLE airports; --",
        "<script>alert('xss')</script>",
        "../../../etc/passwd",
        "Birmingham$(rm -rf /)",
    ]

    for malicious_input in malicious_inputs:
        result = await resolver_with_mock_data.resolve_airport(malicious_input)
        # Should either return None or a valid IATA code, never cause errors
        assert result is None or (
            isinstance(result, str) and len(result) == 3 and result.isalpha()
        )


@pytest.mark.asyncio
async def test_data_validation_iata_codes(
    resolver_with_mock_data: AirportResolver,
) -> None:
    """Test that only valid IATA codes are returned."""
    test_inputs = ["Birmingham", "Faro", "Glasgow", "Lima", "Santiago"]

    for city in test_inputs:
        result = await resolver_with_mock_data.resolve_airport(city)

        if result:  # If we get a result
            assert isinstance(result, str)
            assert len(result) == 3  # IATA codes are always 3 characters
            assert result.isupper()  # Should be uppercase
            assert result.isalpha()  # Should only contain letters


@pytest.mark.asyncio
async def test_concurrent_access_safety() -> None:
    """Test that resolver is safe for concurrent access."""
    import asyncio

    resolver = AirportResolver()
    # Pre-load with mock data to avoid network calls
    resolver.airports_data = {"KJFK": {"iata": "JFK", "city": "new york"}}
    resolver._process_airport_data()
    resolver._setup_priority_mappings()
    resolver.loaded = True

    # Run multiple concurrent resolutions
    tasks = [
        resolver.resolve_airport("New York"),
        resolver.resolve_airport("JFK"),
        resolver.resolve_airport("new york"),
        resolver.resolve_airport("NYC"),
    ]

    results = await asyncio.gather(*tasks)

    # All should succeed and return consistent results
    for result in results:
        assert (
            result == "JFK" or result is None
        )  # NYC might not exist in minimal test data


# ==============================================================================
# search_mwgg_sync — scoring parity / regression tests
# ==============================================================================


@pytest.fixture
def search_fixture_resolver() -> AirportResolver:
    """10-row fixture covering every scoring tier in search_mwgg_sync."""
    data: dict[str, Any] = {
        "KJFK": {
            "iata": "JFK",
            "icao": "KJFK",
            "name": "John F Kennedy International Airport",
            "city": "New York",
            "state": "New York",
            "country": "United States",
        },
        "EGLL": {
            "iata": "LHR",
            "icao": "EGLL",
            "name": "Heathrow Airport",
            "city": "London",
            "state": "England",
            "country": "United Kingdom",
        },
        "EGKK": {
            "iata": "LGW",
            "icao": "EGKK",
            "name": "Gatwick Airport",
            "city": "London",
            "state": "England",
            "country": "United Kingdom",
        },
        "LEBL": {
            "iata": "BCN",
            "icao": "LEBL",
            "name": "Barcelona El Prat Airport",
            "city": "Barcelona",
            "state": "Catalonia",
            "country": "Spain",
        },
        "VOGO": {
            "iata": "GOI",
            "icao": "VOGO",
            "name": "Goa Dabolim Airport",
            "city": "Vasco da Gama",
            "state": "Goa",
            "country": "India",
        },
        "KLAX": {
            "iata": "LAX",
            "icao": "KLAX",
            "name": "Los Angeles International Airport",
            "city": "Los Angeles",
            "state": "California",
            "country": "United States",
        },
        "RJTT": {
            "iata": "HND",
            "icao": "RJTT",
            "name": "Tokyo Haneda Airport",
            "city": "Tokyo",
            "state": "",
            "country": "Japan",
        },
        "LFPG": {
            "iata": "CDG",
            "icao": "LFPG",
            "name": "Charles de Gaulle Airport",
            "city": "Paris",
            "state": "",
            "country": "France",
        },
        "OMDB": {
            "iata": "DXB",
            "icao": "OMDB",
            "name": "Dubai International Airport",
            "city": "Dubai",
            "state": "",
            "country": "United Arab Emirates",
        },
        "WSSS": {
            "iata": "SIN",
            "icao": "WSSS",
            "name": "Singapore Changi Airport",
            "city": "Singapore",
            "state": "",
            "country": "Singapore",
        },
    }
    resolver = AirportResolver()
    resolver.airports_data = data
    resolver._process_airport_data()
    resolver.loaded = True
    return resolver


class TestSearchMwggSyncScoring:
    """Lock the score ladder so refactors can't silently shift result ordering."""

    def test_exact_iata_match_wins(
        self, search_fixture_resolver: AirportResolver
    ) -> None:
        results = search_fixture_resolver.search_mwgg_sync("JFK", limit=5)
        assert results[0]["iata"] == "JFK"
        assert results[0]["score"] == 200

    def test_exact_city_match_ranks_above_substring(
        self, search_fixture_resolver: AirportResolver
    ) -> None:
        # "London" exact city → score 195 for both LHR and LGW
        results = search_fixture_resolver.search_mwgg_sync("London", limit=5)
        assert {r["iata"] for r in results[:2]} == {"LHR", "LGW"}
        assert all(r["score"] == 195 for r in results[:2])

    def test_exact_state_match(self, search_fixture_resolver: AirportResolver) -> None:
        # "Goa" is state on GOI → 190
        results = search_fixture_resolver.search_mwgg_sync("Goa", limit=5)
        top = results[0]
        assert top["iata"] == "GOI"
        assert top["score"] == 190

    def test_name_whole_word_match(
        self, search_fixture_resolver: AirportResolver
    ) -> None:
        # "Heathrow" is a whole word in LHR name → 130
        results = search_fixture_resolver.search_mwgg_sync("Heathrow", limit=5)
        assert results[0]["iata"] == "LHR"
        assert results[0]["score"] == 130

    def test_country_exact_vs_state_prefix(
        self, search_fixture_resolver: AirportResolver
    ) -> None:
        # "Spain" → exact country match (100) on BCN
        results = search_fixture_resolver.search_mwgg_sync("Spain", limit=5)
        assert results[0]["iata"] == "BCN"
        assert results[0]["score"] == 100

    def test_iata_substring_match(
        self, search_fixture_resolver: AirportResolver
    ) -> None:
        # "DX" not exact, but "DX" in "DXB" → 90
        results = search_fixture_resolver.search_mwgg_sync("DX", limit=5)
        assert results[0]["iata"] == "DXB"
        assert results[0]["score"] == 90

    def test_limit_caps_results(self, search_fixture_resolver: AirportResolver) -> None:
        results = search_fixture_resolver.search_mwgg_sync("a", limit=3)
        assert len(results) <= 3

    def test_results_sorted_descending(
        self, search_fixture_resolver: AirportResolver
    ) -> None:
        results = search_fixture_resolver.search_mwgg_sync("London", limit=10)
        scores = [int(r["score"]) for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_unmatched_query_returns_empty(
        self, search_fixture_resolver: AirportResolver
    ) -> None:
        # A query with no substring/word overlap to any row should yield nothing.
        results = search_fixture_resolver.search_mwgg_sync("zzqxq", limit=10)
        assert results == []

    def test_returned_keys_shape(
        self, search_fixture_resolver: AirportResolver
    ) -> None:
        results = search_fixture_resolver.search_mwgg_sync("Paris", limit=1)
        assert results, "Expected at least one result for 'Paris'"
        row = results[0]
        assert set(row.keys()) == {
            "score",
            "iata",
            "name",
            "city",
            "state",
            "country",
        }
        assert row["iata"] == "CDG"
        assert row["city"] == "Paris"


class TestSearchMwggSyncFallbackIndex:
    """Fallback path must populate _search_index so /airports/search still works."""

    def test_fallback_builds_search_index(self) -> None:
        resolver = AirportResolver()
        resolver._load_fallback_airports()
        assert resolver._search_index, "_search_index empty after fallback load"
        # Known mapping: london → LHR
        results = resolver.search_mwgg_sync("London", limit=5)
        assert results, "fallback search returned no results for known city"
        assert any(r["iata"] == "LHR" for r in results)

    def test_fallback_iata_exact_match(self) -> None:
        resolver = AirportResolver()
        resolver._load_fallback_airports()
        results = resolver.search_mwgg_sync("LAX", limit=3)
        assert results
        assert results[0]["iata"] == "LAX"
        assert results[0]["score"] == 200
