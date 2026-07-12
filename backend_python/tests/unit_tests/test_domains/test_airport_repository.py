"""Unit tests for AirportRepository.

Tests cover:
- Data loading and processing
- IATA/ICAO lookups
- City-based searches
- Airport name searches
- Nearby airport searches (haversine)
- Priority mappings
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.domains.airport.models import Airport
from app.domains.airport.repository import AirportRepository

# Sample airport data for testing
SAMPLE_AIRPORT_DATA = {
    "EGLL": {
        "iata": "LHR",
        "icao": "EGLL",
        "name": "London Heathrow Airport",
        "city": "London",
        "country": "United Kingdom",
        "lat": 51.4706,
        "lon": -0.4619,
        "tz": "Europe/London",
    },
    "EGKK": {
        "iata": "LGW",
        "icao": "EGKK",
        "name": "London Gatwick Airport",
        "city": "London",
        "country": "United Kingdom",
        "lat": 51.1537,
        "lon": -0.1821,
        "tz": "Europe/London",
    },
    "EGSS": {
        "iata": "STN",
        "icao": "EGSS",
        "name": "London Stansted Airport",
        "city": "London",
        "country": "United Kingdom",
        "lat": 51.885,
        "lon": 0.235,
        "tz": "Europe/London",
    },
    "EHAM": {
        "iata": "AMS",
        "icao": "EHAM",
        "name": "Amsterdam Airport Schiphol",
        "city": "Amsterdam",
        "country": "Netherlands",
        "lat": 52.3086,
        "lon": 4.7639,
        "tz": "Europe/Amsterdam",
    },
    "LFPG": {
        "iata": "CDG",
        "icao": "LFPG",
        "name": "Paris Charles de Gaulle Airport",
        "city": "Paris",
        "country": "France",
        "lat": 49.0097,
        "lon": 2.5479,
        "tz": "Europe/Paris",
    },
    "EGBB": {
        "iata": "BHX",
        "icao": "EGBB",
        "name": "Birmingham Airport",
        "city": "Birmingham",
        "country": "United Kingdom",
        "lat": 52.4539,
        "lon": -1.7480,
        "tz": "Europe/London",
    },
    "KBHM": {
        "iata": "BHM",
        "icao": "KBHM",
        "name": "Birmingham-Shuttlesworth International Airport",
        "city": "Birmingham",
        "country": "United States",
        "lat": 33.5629,
        "lon": -86.7535,
        "tz": "America/Chicago",
    },
    "KJFK": {
        "iata": "JFK",
        "icao": "KJFK",
        "name": "John F Kennedy International Airport",
        "city": "New York",
        "country": "United States",
        "lat": 40.6413,
        "lon": -73.7781,
        "tz": "America/New_York",
    },
    "INVALID": {
        "iata": "",  # Invalid - no IATA
        "icao": "XXXX",
        "name": "Invalid Airport",
        "city": "Nowhere",
        "country": "Unknown",
        "lat": 0,
        "lon": 0,
    },
}


@pytest.fixture
def repository() -> AirportRepository:
    """Create a repository with sample data loaded."""
    repo = AirportRepository(data_path=Path("/fake/path.json"))
    repo.airports_data = SAMPLE_AIRPORT_DATA
    repo._process_airport_data()
    repo._setup_priority_mappings()
    repo.loaded = True
    return repo


# =============================================================================
# Data Loading Tests
# =============================================================================


class TestDataLoading:
    """Tests for data loading and processing."""

    @pytest.mark.asyncio
    async def test_ensure_loaded_from_cache(self, tmp_path: Path) -> None:
        """ensure_loaded loads from cache file if exists."""
        cache_file = tmp_path / "airports.json"
        cache_file.write_text(json.dumps(SAMPLE_AIRPORT_DATA))

        repo = AirportRepository(data_path=cache_file)
        await repo.ensure_loaded()

        assert repo.loaded is True
        assert len(repo._iata_index) > 0

    @pytest.mark.asyncio
    async def test_ensure_loaded_idempotent(
        self, repository: AirportRepository
    ) -> None:
        """ensure_loaded only loads once."""
        original_data = repository.airports_data.copy()

        await repository.ensure_loaded()
        await repository.ensure_loaded()

        assert repository.airports_data == original_data

    def test_process_airport_data_builds_indexes(
        self, repository: AirportRepository
    ) -> None:
        """_process_airport_data builds IATA and ICAO indexes."""
        # IATA index
        assert "LHR" in repository._iata_index
        assert "AMS" in repository._iata_index
        assert repository._iata_index["LHR"].name == "London Heathrow Airport"

        # ICAO index
        assert "EGLL" in repository._icao_index
        assert "EHAM" in repository._icao_index

    def test_process_airport_data_builds_city_index(
        self, repository: AirportRepository
    ) -> None:
        """_process_airport_data builds city to airports mapping."""
        assert "london" in repository.city_to_airports
        assert len(repository.city_to_airports["london"]) == 3  # LHR, LGW, STN
        assert "LHR" in repository.city_to_airports["london"]

    def test_process_airport_data_skips_invalid(
        self, repository: AirportRepository
    ) -> None:
        """_process_airport_data skips airports without valid IATA."""
        # The INVALID airport has empty IATA, should not be indexed
        assert "" not in repository._iata_index
        assert "INVALID" not in repository._iata_index

    def test_priority_mappings_setup(self, repository: AirportRepository) -> None:
        """_setup_priority_mappings creates major city mappings."""
        assert repository.priority_city_mappings["london"] == "LHR"
        assert repository.priority_city_mappings["paris"] == "CDG"
        assert repository.priority_city_mappings["amsterdam"] == "AMS"
        assert repository.priority_city_mappings["birmingham"] == "BHX"


# =============================================================================
# IATA Lookup Tests
# =============================================================================


class TestIATALookup:
    """Tests for get_by_iata method."""

    def test_get_by_iata_valid(self, repository: AirportRepository) -> None:
        """get_by_iata returns airport for valid code."""
        airport = repository.get_by_iata("LHR")

        assert airport is not None
        assert airport.iata == "LHR"
        assert airport.name == "London Heathrow Airport"
        assert airport.city == "London"
        assert airport.country == "United Kingdom"

    def test_get_by_iata_lowercase(self, repository: AirportRepository) -> None:
        """get_by_iata is case-insensitive."""
        airport = repository.get_by_iata("lhr")

        assert airport is not None
        assert airport.iata == "LHR"

    def test_get_by_iata_invalid(self, repository: AirportRepository) -> None:
        """get_by_iata returns None for invalid code."""
        airport = repository.get_by_iata("XYZ")

        assert airport is None


# =============================================================================
# ICAO Lookup Tests
# =============================================================================


class TestICAOLookup:
    """Tests for get_by_icao method."""

    def test_get_by_icao_valid(self, repository: AirportRepository) -> None:
        """get_by_icao returns airport for valid code."""
        airport = repository.get_by_icao("EGLL")

        assert airport is not None
        assert airport.iata == "LHR"
        assert airport.icao == "EGLL"

    def test_get_by_icao_lowercase(self, repository: AirportRepository) -> None:
        """get_by_icao is case-insensitive."""
        airport = repository.get_by_icao("egll")

        assert airport is not None
        assert airport.iata == "LHR"

    def test_get_by_icao_invalid(self, repository: AirportRepository) -> None:
        """get_by_icao returns None for invalid code."""
        airport = repository.get_by_icao("XXXX")

        assert airport is None


# =============================================================================
# City Lookup Tests
# =============================================================================


class TestCityLookup:
    """Tests for get_by_city method."""

    def test_get_by_city_returns_all_airports(
        self, repository: AirportRepository
    ) -> None:
        """get_by_city returns all airports in a city."""
        airports = repository.get_by_city("London")

        assert len(airports) == 3
        iata_codes = {a.iata for a in airports}
        assert iata_codes == {"LHR", "LGW", "STN"}

    def test_get_by_city_priority_first(self, repository: AirportRepository) -> None:
        """get_by_city puts priority airport first."""
        airports = repository.get_by_city("London")

        # LHR is priority for London
        assert airports[0].iata == "LHR"

    def test_get_by_city_with_country_filter(
        self, repository: AirportRepository
    ) -> None:
        """get_by_city filters by country when provided."""
        uk_airports = repository.get_by_city("Birmingham", "United Kingdom")
        us_airports = repository.get_by_city("Birmingham", "United States")

        assert len(uk_airports) == 1
        assert uk_airports[0].iata == "BHX"

        assert len(us_airports) == 1
        assert us_airports[0].iata == "BHM"

    def test_get_by_city_case_insensitive(self, repository: AirportRepository) -> None:
        """get_by_city is case-insensitive."""
        airports1 = repository.get_by_city("london")
        airports2 = repository.get_by_city("LONDON")
        airports3 = repository.get_by_city("London")

        assert len(airports1) == len(airports2) == len(airports3) == 3

    def test_get_by_city_unknown(self, repository: AirportRepository) -> None:
        """get_by_city returns empty list for unknown city."""
        airports = repository.get_by_city("UnknownCity")

        assert airports == []


# =============================================================================
# Priority Airport Tests
# =============================================================================


class TestPriorityAirport:
    """Tests for get_priority_airport method."""

    def test_get_priority_airport_exists(self, repository: AirportRepository) -> None:
        """get_priority_airport returns code for major cities."""
        assert repository.get_priority_airport("london") == "LHR"
        assert repository.get_priority_airport("paris") == "CDG"
        assert repository.get_priority_airport("amsterdam") == "AMS"

    def test_get_priority_airport_case_insensitive(
        self, repository: AirportRepository
    ) -> None:
        """get_priority_airport is case-insensitive."""
        assert repository.get_priority_airport("LONDON") == "LHR"
        assert repository.get_priority_airport("London") == "LHR"

    def test_get_priority_airport_none(self, repository: AirportRepository) -> None:
        """get_priority_airport returns None for non-priority cities."""
        assert repository.get_priority_airport("SmallTown") is None


# =============================================================================
# Search by Name Tests
# =============================================================================


class TestSearchByName:
    """Tests for search_by_name method."""

    def test_search_by_name_exact(self, repository: AirportRepository) -> None:
        """search_by_name finds exact name matches."""
        results = repository.search_by_name("Heathrow")

        assert len(results) >= 1
        assert any(a.iata == "LHR" for a in results)

    def test_search_by_name_partial(self, repository: AirportRepository) -> None:
        """search_by_name finds partial name matches."""
        results = repository.search_by_name("Charles de Gaulle")

        assert len(results) >= 1
        assert any(a.iata == "CDG" for a in results)

    def test_search_by_name_case_insensitive(
        self, repository: AirportRepository
    ) -> None:
        """search_by_name is case-insensitive."""
        results = repository.search_by_name("heathrow")

        assert len(results) >= 1
        assert any(a.iata == "LHR" for a in results)

    def test_search_by_name_limit(self, repository: AirportRepository) -> None:
        """search_by_name respects limit parameter."""
        results = repository.search_by_name("Airport", limit=2)

        assert len(results) <= 2

    def test_search_by_name_no_match(self, repository: AirportRepository) -> None:
        """search_by_name returns empty for no matches."""
        results = repository.search_by_name("NonexistentAirport12345")

        assert results == []


# =============================================================================
# General Search Tests
# =============================================================================


class TestGeneralSearch:
    """Tests for search method."""

    def test_search_finds_by_city(self, repository: AirportRepository) -> None:
        """search finds airports by city name."""
        results = repository.search("Paris")

        assert len(results) >= 1
        assert any(a.iata == "CDG" for a in results)

    def test_search_finds_by_name(self, repository: AirportRepository) -> None:
        """search finds airports by airport name."""
        results = repository.search("Schiphol")

        assert len(results) >= 1
        assert any(a.iata == "AMS" for a in results)

    def test_search_limit(self, repository: AirportRepository) -> None:
        """search respects limit parameter."""
        results = repository.search("London", limit=2)

        assert len(results) <= 2


# =============================================================================
# Nearby Airport Tests
# =============================================================================


class TestNearbyAirports:
    """Tests for find_nearby method."""

    def test_find_nearby_returns_sorted_by_distance(
        self, repository: AirportRepository
    ) -> None:
        """find_nearby returns airports sorted by distance."""
        # Coordinates near London
        results = repository.find_nearby(51.5, -0.1, limit=5)

        assert len(results) > 0
        # Check distances are sorted
        distances = [d for _, d in results]
        assert distances == sorted(distances)

    def test_find_nearby_with_radius(self, repository: AirportRepository) -> None:
        """find_nearby filters by radius_km."""
        # Very small radius - should only find very close airports
        results = repository.find_nearby(51.5, -0.1, radius_km=50, limit=10)

        for _, distance in results:
            assert distance <= 50

    def test_find_nearby_returns_tuples(self, repository: AirportRepository) -> None:
        """find_nearby returns (Airport, distance) tuples."""
        results = repository.find_nearby(51.5, -0.1, limit=1)

        assert len(results) == 1
        airport, distance = results[0]
        assert isinstance(airport, Airport)
        assert isinstance(distance, float)

    def test_find_nearby_limit(self, repository: AirportRepository) -> None:
        """find_nearby respects limit parameter."""
        results = repository.find_nearby(51.5, -0.1, limit=2)

        assert len(results) <= 2


# =============================================================================
# Haversine Distance Tests
# =============================================================================


class TestHaversineDistance:
    """Tests for _haversine_distance static method."""

    def test_haversine_same_point(self) -> None:
        """Distance between same point is 0."""
        distance = AirportRepository._haversine_distance(51.5, -0.1, 51.5, -0.1)

        assert distance == 0.0

    def test_haversine_london_to_paris(self) -> None:
        """Distance London to Paris is approximately 340km."""
        # London: 51.5, -0.1
        # Paris: 48.85, 2.35
        distance = AirportRepository._haversine_distance(51.5, -0.1, 48.85, 2.35)

        # Should be around 340km
        assert 330 < distance < 360

    def test_haversine_london_to_new_york(self) -> None:
        """Distance London to NYC is approximately 5500km."""
        # London: 51.5, -0.1
        # NYC: 40.7, -74.0
        distance = AirportRepository._haversine_distance(51.5, -0.1, 40.7, -74.0)

        # Should be around 5500km
        assert 5400 < distance < 5700


# =============================================================================
# Airport Count Test
# =============================================================================


class TestAirportCount:
    """Tests for get_airport_count method."""

    def test_get_airport_count(self, repository: AirportRepository) -> None:
        """get_airport_count returns correct count."""
        count = repository.get_airport_count()

        # We have 8 valid airports in sample data (one has no IATA)
        assert count == 8


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_airport_data_normalized(self, repository: AirportRepository) -> None:
        """Airport IATA codes are normalized to uppercase."""
        airport = repository.get_by_iata("lhr")

        assert airport is not None
        assert airport.iata == "LHR"  # Uppercase

    def test_city_with_whitespace(self, repository: AirportRepository) -> None:
        """get_by_city handles whitespace."""
        airports = repository.get_by_city("  London  ")

        assert len(airports) == 3

    @pytest.mark.asyncio
    async def test_download_fallback_on_error(self) -> None:
        """Falls back to minimal mappings on download error."""
        repo = AirportRepository(data_path=Path("/nonexistent/path.json"))

        with patch.object(
            repo, "_download_airport_data", new_callable=AsyncMock
        ) as mock_download:
            mock_download.side_effect = Exception("Network error")

            await repo.ensure_loaded()

            # Should have loaded fallback
            assert repo.loaded is True
            # Fallback includes priority mappings
            assert "london" in repo.priority_city_mappings
