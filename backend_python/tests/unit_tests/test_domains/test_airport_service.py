"""Unit tests for AirportService.

Tests cover:
- IATA code resolution
- ICAO code resolution
- Multi-city disambiguation (Birmingham UK vs USA)
- Multi-airport cities (London → LHR, LGW, STN...)
- Code vs city disambiguation (GOA)
- Airport name resolution
- City lookups and nearby searches
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.airport.models import (
    Airport,
    DisambiguationType,
    ResolveContext,
)
from app.domains.airport.repository import AirportRepository
from app.domains.airport.service import AirportService
from app.shared.geocoding import GeocodingResult


# Test fixtures
@pytest.fixture
def mock_airports() -> dict[str, Airport]:
    """Create a set of test airports."""
    return {
        "LHR": Airport(
            iata="LHR",
            icao="EGLL",
            name="London Heathrow",
            city="London",
            country="United Kingdom",
            lat=51.47,
            lon=-0.45,
        ),
        "LGW": Airport(
            iata="LGW",
            icao="EGKK",
            name="London Gatwick",
            city="London",
            country="United Kingdom",
            lat=51.15,
            lon=-0.19,
        ),
        "STN": Airport(
            iata="STN",
            icao="EGSS",
            name="London Stansted",
            city="London",
            country="United Kingdom",
            lat=51.89,
            lon=0.26,
        ),
        "BHX": Airport(
            iata="BHX",
            icao="EGBB",
            name="Birmingham Airport",
            city="Birmingham",
            country="United Kingdom",
            lat=52.45,
            lon=-1.75,
        ),
        "BHM": Airport(
            iata="BHM",
            icao="KBHM",
            name="Birmingham-Shuttlesworth International",
            city="Birmingham",
            country="United States",
            lat=33.56,
            lon=-86.75,
        ),
        "VCE": Airport(
            iata="VCE",
            icao="LIPZ",
            name="Venice Marco Polo",
            city="Venice",
            country="Italy",
            lat=45.51,
            lon=12.35,
        ),
        "VNC": Airport(
            iata="VNC",
            icao="KVNC",
            name="Venice Municipal",
            city="Venice",
            country="United States",
            lat=27.07,
            lon=-82.44,
        ),
        "GOA": Airport(
            iata="GOA",
            icao="LIMJ",
            name="Genoa Cristoforo Colombo",
            city="Genoa",
            country="Italy",
            lat=44.41,
            lon=8.84,
        ),
        "GOI": Airport(
            iata="GOI",
            icao="VOGO",
            name="Goa International",
            city="Goa",
            country="India",
            lat=15.38,
            lon=73.83,
        ),
        "AMS": Airport(
            iata="AMS",
            icao="EHAM",
            name="Amsterdam Schiphol",
            city="Amsterdam",
            country="Netherlands",
            lat=52.31,
            lon=4.77,
        ),
        "CDG": Airport(
            iata="CDG",
            icao="LFPG",
            name="Paris Charles de Gaulle",
            city="Paris",
            country="France",
            lat=49.01,
            lon=2.55,
        ),
    }


@pytest.fixture
def mock_repository(mock_airports: dict[str, Airport]) -> MagicMock:
    """Create a mock AirportRepository."""
    repo = MagicMock(spec=AirportRepository)
    repo.loaded = True

    # Mock ensure_loaded as async
    repo.ensure_loaded = AsyncMock()

    # Build city_to_airports index (used by Strategy 3 multi-country check)
    city_index: dict[str, list[str]] = {}
    for airport in mock_airports.values():
        city_key = airport.city.lower()
        if city_key not in city_index:
            city_index[city_key] = []
        city_index[city_key].append(airport.iata)
    repo.city_to_airports = city_index

    # Mock get_by_iata
    def get_by_iata(code: str) -> Airport | None:
        return mock_airports.get(code.upper())

    repo.get_by_iata = MagicMock(side_effect=get_by_iata)

    # Mock get_by_icao
    def get_by_icao(code: str) -> Airport | None:
        icao_map = {a.icao: a for a in mock_airports.values() if a.icao}
        return icao_map.get(code.upper())

    repo.get_by_icao = MagicMock(side_effect=get_by_icao)

    # Mock get_by_city
    # Map ISO codes to full country names for test matching
    iso_to_name = {
        "GB": "United Kingdom",
        "US": "United States",
        "IT": "Italy",
        "IN": "India",
        "NL": "Netherlands",
        "FR": "France",
    }

    def get_by_city(city: str, country: str | None = None) -> list[Airport]:
        # Convert ISO code to full name if needed
        if country and len(country) == 2:
            country = iso_to_name.get(country.upper(), country)

        results = [
            a
            for a in mock_airports.values()
            if a.city.lower() == city.lower()
            and (country is None or a.country.lower() == country.lower())
        ]
        # Sort to put priority airports first (LHR for London, BHX for Birmingham)
        priority = {"london": "LHR", "birmingham": "BHX", "venice": "VCE"}
        priority_code = priority.get(city.lower())
        if priority_code:
            results.sort(key=lambda a: 0 if a.iata == priority_code else 1)
        return results

    repo.get_by_city = MagicMock(side_effect=get_by_city)

    # Mock search_by_name
    def search_by_name(query: str, limit: int = 10) -> list[Airport]:
        query_lower = query.lower()
        results = [a for a in mock_airports.values() if query_lower in a.name.lower()]
        return results[:limit]

    repo.search_by_name = MagicMock(side_effect=search_by_name)

    # Mock search (general)
    def search(query: str, limit: int = 10) -> list[Airport]:
        query_lower = query.lower()
        results = [
            a
            for a in mock_airports.values()
            if query_lower in a.city.lower() or query_lower in a.name.lower()
        ]
        return results[:limit]

    repo.search = MagicMock(side_effect=search)

    # Mock find_nearby
    def find_nearby(
        lat: float, lon: float, radius_km: int | None = None, limit: int = 10
    ) -> list[tuple[Airport, float]]:
        # Simple mock: return all airports with fake distances
        results = [(a, 100.0 * i) for i, a in enumerate(mock_airports.values())]
        if radius_km:
            results = [(a, d) for a, d in results if d <= radius_km]
        return results[:limit]

    repo.find_nearby = MagicMock(side_effect=find_nearby)

    # Mock get_priority_airport
    priority = {
        "london": "LHR",
        "birmingham": "BHX",
        "paris": "CDG",
        "amsterdam": "AMS",
    }
    repo.get_priority_airport = MagicMock(side_effect=lambda c: priority.get(c.lower()))

    return repo


@pytest.fixture
def mock_geocoding() -> MagicMock:
    """Create a mock GeocodingService."""
    geo = MagicMock()

    # Default: return empty (no ambiguity)
    geo.geocode_city = AsyncMock(return_value=[])

    return geo


@pytest.fixture
def service(mock_repository: MagicMock, mock_geocoding: MagicMock) -> AirportService:
    """Create an AirportService with mocked dependencies."""
    return AirportService(mock_repository, mock_geocoding)


# =============================================================================
# IATA Code Resolution Tests
# =============================================================================


class TestIATAResolution:
    """Tests for IATA code resolution."""

    @pytest.mark.asyncio
    async def test_resolve_valid_iata_code(
        self, service: AirportService, mock_geocoding: MagicMock
    ) -> None:
        """resolve("LHR") → resolved, airport=LHR"""
        result = await service.resolve("LHR")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "LHR"
        assert result.airport.name == "London Heathrow"
        assert result.original_query == "LHR"

    @pytest.mark.asyncio
    async def test_resolve_lowercase_iata_code(self, service: AirportService) -> None:
        """resolve("lhr") → resolved, airport=LHR (case insensitive)"""
        result = await service.resolve("lhr")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "LHR"

    @pytest.mark.asyncio
    async def test_resolve_invalid_iata_code(
        self, service: AirportService, mock_repository: MagicMock
    ) -> None:
        """resolve("XYZ") → not_found (invalid code)"""
        # Make sure XYZ doesn't exist
        mock_repository.get_by_iata.side_effect = lambda c: None

        result = await service.resolve("XYZ")

        assert result.status == "not_found"
        assert result.airport is None
        assert result.original_query == "XYZ"


# =============================================================================
# ICAO Code Resolution Tests
# =============================================================================


class TestICAOResolution:
    """Tests for ICAO code resolution."""

    @pytest.mark.asyncio
    async def test_resolve_valid_icao_code(self, service: AirportService) -> None:
        """resolve("EGLL") → resolved, airport=LHR"""
        result = await service.resolve("EGLL")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "LHR"

    @pytest.mark.asyncio
    async def test_resolve_lowercase_icao_code(self, service: AirportService) -> None:
        """resolve("egll") → resolved, airport=LHR (case insensitive)"""
        result = await service.resolve("egll")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "LHR"


# =============================================================================
# Multi-City Disambiguation Tests
# =============================================================================


class TestMultiCityDisambiguation:
    """Tests for multi-city disambiguation (same city name, different countries)."""

    @pytest.mark.asyncio
    async def test_resolve_birmingham_needs_disambiguation(
        self, service: AirportService, mock_geocoding: MagicMock
    ) -> None:
        """resolve("Birmingham") → needs_disambiguation, MULTI_CITY"""
        # Mock geocoding to return both UK and US Birmingham
        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="Birmingham",
                    country="United Kingdom",
                    country_code="GB",
                    formatted_address="Birmingham, UK",
                    lat=52.48,
                    lng=-1.90,
                ),
                GeocodingResult(
                    city="Birmingham",
                    country="United States",
                    country_code="US",
                    formatted_address="Birmingham, AL, USA",
                    lat=33.52,
                    lng=-86.81,
                ),
            ]
        )

        result = await service.resolve("Birmingham")

        assert result.status == "needs_disambiguation"
        assert result.disambiguation_type == DisambiguationType.MULTI_CITY
        assert len(result.options) == 2
        # display_name uses formatted_address from geocoding mock
        assert any("UK" in opt.display_name for opt in result.options)
        assert any("USA" in opt.display_name for opt in result.options)
        assert result.suggested_prompt is not None
        assert "Which city" in result.suggested_prompt

    @pytest.mark.asyncio
    async def test_resolve_birmingham_with_country_hint(
        self, service: AirportService, mock_geocoding: MagicMock
    ) -> None:
        """resolve("Birmingham", country_hint="UK") → resolved, BHX"""
        # With country hint, should resolve directly without geocoding check
        result = await service.resolve(
            "Birmingham", ResolveContext(country_hint="United Kingdom")
        )

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "BHX"

    @pytest.mark.asyncio
    async def test_resolve_venice_needs_disambiguation(
        self, service: AirportService, mock_geocoding: MagicMock
    ) -> None:
        """resolve("Venice") → needs_disambiguation, options=[Italy, Florida]"""
        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="Venice",
                    country="Italy",
                    country_code="IT",
                    formatted_address="Venice, Italy",
                    lat=45.44,
                    lng=12.32,
                ),
                GeocodingResult(
                    city="Venice",
                    country="United States",
                    country_code="US",
                    formatted_address="Venice, FL, USA",
                    lat=27.10,
                    lng=-82.45,
                ),
            ]
        )

        result = await service.resolve("Venice")

        assert result.status == "needs_disambiguation"
        assert result.disambiguation_type == DisambiguationType.MULTI_CITY
        assert len(result.options) == 2


# =============================================================================
# Multi-Airport City Tests
# =============================================================================


class TestMultiAirportCity:
    """Tests for multi-airport cities (London → LHR, LGW, STN...)."""

    @pytest.mark.asyncio
    async def test_resolve_london_shows_all_airports(
        self, service: AirportService, mock_geocoding: MagicMock
    ) -> None:
        """resolve("London") → resolved, needs_airport_preference=True, all_airports=[LHR,LGW,STN]"""
        # Mock geocoding to return single result (no multi-city ambiguity)
        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="London",
                    country="United Kingdom",
                    country_code="GB",
                    formatted_address="London, UK",
                    lat=51.51,
                    lng=-0.13,
                ),
            ]
        )

        result = await service.resolve("London")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "LHR"  # Priority airport
        assert result.needs_airport_preference is True
        assert len(result.all_airports) == 3  # LHR, LGW, STN
        assert {a.iata for a in result.all_airports} == {"LHR", "LGW", "STN"}

    @pytest.mark.asyncio
    async def test_resolve_single_airport_city(
        self, service: AirportService, mock_geocoding: MagicMock
    ) -> None:
        """resolve("Amsterdam") → resolved, needs_airport_preference=False"""
        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="Amsterdam",
                    country="Netherlands",
                    country_code="NL",
                    formatted_address="Amsterdam, Netherlands",
                    lat=52.37,
                    lng=4.89,
                ),
            ]
        )

        result = await service.resolve("Amsterdam")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "AMS"
        assert result.needs_airport_preference is False
        assert len(result.all_airports) == 1


# =============================================================================
# Code vs City Disambiguation Tests
# =============================================================================


class TestCodeVsCityDisambiguation:
    """Tests for CODE_VS_CITY disambiguation (GOA)."""

    @pytest.mark.asyncio
    async def test_resolve_goa_needs_disambiguation(
        self, service: AirportService, mock_geocoding: MagicMock
    ) -> None:
        """resolve("GOA") → needs_disambiguation, CODE_VS_CITY, options=[Genoa, Goa India]"""
        # GOA is both an IATA code (Genoa) and a city (Goa, India)
        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="Goa",
                    country="India",
                    country_code="IN",
                    formatted_address="Goa, India",
                    lat=15.30,
                    lng=73.91,
                ),
            ]
        )

        result = await service.resolve("GOA")

        assert result.status == "needs_disambiguation"
        assert result.disambiguation_type == DisambiguationType.CODE_VS_CITY
        assert len(result.options) == 2
        # One option should be the IATA match (Genoa)
        iata_option = next(
            (opt for opt in result.options if opt.match_type == "iata"), None
        )
        assert iata_option is not None
        assert "Genoa" in iata_option.display_name or "GOA" in iata_option.display_name
        # One option should be the city match (Goa, India)
        city_option = next(
            (opt for opt in result.options if opt.match_type == "city"), None
        )
        assert city_option is not None
        assert "India" in city_option.display_name

    @pytest.mark.asyncio
    async def test_resolve_iata_code_no_city_match(
        self, service: AirportService, mock_geocoding: MagicMock
    ) -> None:
        """resolve("AMS") → resolved (no city ambiguity)"""
        # AMS is just an IATA code, no city called "AMS"
        mock_geocoding.geocode_city = AsyncMock(return_value=[])

        result = await service.resolve("AMS")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "AMS"


# =============================================================================
# Airport Name Resolution Tests
# =============================================================================


class TestAirportNameResolution:
    """Tests for airport name resolution."""

    @pytest.mark.asyncio
    async def test_resolve_heathrow(self, service: AirportService) -> None:
        """resolve("Heathrow") → resolved, airport=LHR"""
        result = await service.resolve("Heathrow")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "LHR"

    @pytest.mark.asyncio
    async def test_resolve_full_airport_name(self, service: AirportService) -> None:
        """resolve("Charles de Gaulle") → resolved, airport=CDG"""
        result = await service.resolve("Charles de Gaulle")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "CDG"


# =============================================================================
# get_airports_in_city Tests
# =============================================================================


class TestGetAirportsInCity:
    """Tests for get_airports_in_city method."""

    def test_get_london_airports(self, service: AirportService) -> None:
        """get_airports_in_city("London") returns all London airports."""
        airports = service.get_airports_in_city("London")

        assert len(airports) == 3
        assert {a.iata for a in airports} == {"LHR", "LGW", "STN"}

    def test_get_london_airports_with_country(self, service: AirportService) -> None:
        """get_airports_in_city("London", "United Kingdom") filters by country."""
        airports = service.get_airports_in_city("London", "United Kingdom")

        assert len(airports) == 3
        assert all(a.country == "United Kingdom" for a in airports)

    def test_get_airports_unknown_city(self, service: AirportService) -> None:
        """get_airports_in_city("UnknownCity") returns empty list."""
        airports = service.get_airports_in_city("UnknownCity")

        assert airports == []


# =============================================================================
# get_nearby_airports Tests
# =============================================================================


class TestGetNearbyAirports:
    """Tests for get_nearby_airports method."""

    def test_get_nearby_airports(self, service: AirportService) -> None:
        """get_nearby_airports returns airports sorted by distance."""
        results = service.get_nearby_airports(51.5, -0.12, limit=5)

        assert len(results) == 5
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
        # Check distances are sorted
        distances = [d for _, d in results]
        assert distances == sorted(distances)

    def test_get_nearby_airports_with_radius(self, service: AirportService) -> None:
        """get_nearby_airports with radius_km filters results."""
        results = service.get_nearby_airports(51.5, -0.12, radius_km=50, limit=10)

        # With mock returning 100*i distances, only first one (0km) would be in 50km
        assert all(d <= 50 for _, d in results)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_resolve_empty_string(self, service: AirportService) -> None:
        """resolve("") → not_found"""
        result = await service.resolve("")

        assert result.status == "not_found"

    @pytest.mark.asyncio
    async def test_resolve_whitespace_only(self, service: AirportService) -> None:
        """resolve("   ") → not_found"""
        result = await service.resolve("   ")

        assert result.status == "not_found"

    @pytest.mark.asyncio
    async def test_resolve_with_leading_trailing_whitespace(
        self, service: AirportService
    ) -> None:
        """resolve("  LHR  ") → resolved (whitespace trimmed)"""
        result = await service.resolve("  LHR  ")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "LHR"

    @pytest.mark.asyncio
    async def test_resolve_unknown_location(
        self, service: AirportService, mock_repository: MagicMock
    ) -> None:
        """resolve("NonexistentPlace") → not_found"""
        # Make all lookups return empty
        mock_repository.get_by_iata.return_value = None
        mock_repository.get_by_icao.return_value = None
        mock_repository.search_by_name.return_value = []
        mock_repository.get_by_city.return_value = []
        mock_repository.search.return_value = []

        result = await service.resolve("NonexistentPlace")

        assert result.status == "not_found"


# =============================================================================
# Suggested Prompt Tests
# =============================================================================


class TestSuggestedPrompts:
    """Tests for suggested prompt generation."""

    @pytest.mark.asyncio
    async def test_multi_city_prompt_format(
        self, service: AirportService, mock_geocoding: MagicMock
    ) -> None:
        """Multi-city disambiguation has proper prompt format."""
        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="Birmingham",
                    country="United Kingdom",
                    country_code="GB",
                    formatted_address="Birmingham, UK",
                    lat=52.48,
                    lng=-1.90,
                ),
                GeocodingResult(
                    city="Birmingham",
                    country="United States",
                    country_code="US",
                    formatted_address="Birmingham, AL, USA",
                    lat=33.52,
                    lng=-86.81,
                ),
            ]
        )

        result = await service.resolve("Birmingham")

        assert result.suggested_prompt is not None
        assert "Which city" in result.suggested_prompt
        assert "1." in result.suggested_prompt
        assert "2." in result.suggested_prompt

    @pytest.mark.asyncio
    async def test_code_vs_city_prompt_format(
        self, service: AirportService, mock_geocoding: MagicMock
    ) -> None:
        """Code vs city disambiguation has proper prompt format."""
        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="Goa",
                    country="India",
                    country_code="IN",
                    formatted_address="Goa, India",
                    lat=15.30,
                    lng=73.91,
                ),
            ]
        )

        result = await service.resolve("GOA")

        assert result.suggested_prompt is not None
        assert (
            "airport code" in result.suggested_prompt.lower()
            or "city" in result.suggested_prompt.lower()
        )


# =============================================================================
# City Suffix Stripping Tests
# =============================================================================


class TestCountryDetectionGuard:
    """Tests for country detection via geocoding result_types.

    When a query is a country name (e.g., "Costa Rica"), Google Geocoding returns
    result_types=["country", "political"]. The service should return not_found
    instead of resolving to an unrelated airport.
    """

    @pytest.mark.asyncio
    async def test_country_query_returns_not_found(
        self,
        service: AirportService,
        mock_geocoding: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """resolve("Costa Rica") → not_found (country, not a city)."""
        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="Costa Rica",
                    country="Costa Rica",
                    country_code="CR",
                    formatted_address="Costa Rica",
                    lat=9.93,
                    lng=-84.09,
                    result_types=["country", "political"],
                ),
            ]
        )
        # Ensure no IATA/name shortcuts fire
        mock_repository.get_by_iata.return_value = None
        mock_repository.search_by_name.return_value = []

        result = await service.resolve("Costa Rica")

        assert result.status == "not_found"
        assert result.original_query == "Costa Rica"

    @pytest.mark.asyncio
    async def test_city_with_locality_type_resolves_normally(
        self,
        service: AirportService,
        mock_geocoding: MagicMock,
    ) -> None:
        """resolve("Amsterdam") → resolved (locality, not country)."""
        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="Amsterdam",
                    country="Netherlands",
                    country_code="NL",
                    formatted_address="Amsterdam, Netherlands",
                    lat=52.37,
                    lng=4.89,
                    result_types=["locality", "political"],
                ),
            ]
        )

        result = await service.resolve("Amsterdam")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "AMS"


class TestCitySuffixStripping:
    """Tests for city suffix stripping in _resolve_via_geocoding.

    Geocoding APIs often append "City", "Town", "Metro", etc. to city names
    that the airport database doesn't use (e.g. "Tacloban City" vs "Tacloban").
    The service strips the suffix and retries the airport lookup.
    """

    @pytest.mark.asyncio
    async def test_city_suffix_strips_and_retries_successfully(
        self,
        service: AirportService,
        mock_geocoding: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """'Tacloban City' geocoded city → strips ' city' → retries → finds airport."""
        tacloban_airport = Airport(
            iata="TAC",
            icao="RPVA",
            name="Daniel Z. Romualdez Airport",
            city="Tacloban",
            country="Philippines",
            lat=11.24,
            lon=125.02,
        )

        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="Tacloban City",
                    country="Philippines",
                    country_code="PH",
                    formatted_address="Tacloban City, Philippines",
                    lat=11.24,
                    lng=125.02,
                ),
            ]
        )

        def get_by_city(city: str, country: str | None = None) -> list[Airport]:
            if city.lower() == "tacloban":
                return [tacloban_airport]
            return []

        mock_repository.get_by_city = MagicMock(side_effect=get_by_city)

        result = await service.resolve("Tacloban City")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "TAC"

    @pytest.mark.asyncio
    async def test_city_suffix_strips_metro_variant(
        self,
        service: AirportService,
        mock_geocoding: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """' metro' suffix is also stripped (e.g. 'Manila Metro' → 'Manila')."""
        manila_airport = Airport(
            iata="MNL",
            icao="RPLL",
            name="Ninoy Aquino International",
            city="Manila",
            country="Philippines",
            lat=14.51,
            lon=121.02,
        )

        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="Manila Metro",
                    country="Philippines",
                    country_code="PH",
                    formatted_address="Metro Manila, Philippines",
                    lat=14.60,
                    lng=120.98,
                ),
            ]
        )

        def get_by_city(city: str, country: str | None = None) -> list[Airport]:
            if city.lower() == "manila":
                return [manila_airport]
            return []

        mock_repository.get_by_city = MagicMock(side_effect=get_by_city)

        result = await service.resolve("Manila Metro")

        assert result.status == "resolved"
        assert result.airport is not None
        assert result.airport.iata == "MNL"

    @pytest.mark.asyncio
    async def test_city_suffix_only_tries_first_matching_suffix(
        self,
        service: AirportService,
        mock_geocoding: MagicMock,
        mock_repository: MagicMock,
    ) -> None:
        """After the first matching suffix, break — no further suffix variants tried."""
        mock_geocoding.geocode_city = AsyncMock(
            return_value=[
                GeocodingResult(
                    city="Nowhere City",
                    country="TestLand",
                    country_code="TL",
                    formatted_address="Nowhere City, TestLand",
                    lat=0.0,
                    lng=0.0,
                ),
            ]
        )

        # Track every city name passed to get_by_city
        city_lookup_calls: list[str] = []

        def get_by_city(city: str, country: str | None = None) -> list[Airport]:
            city_lookup_calls.append(city)
            return []  # Always empty — no airports

        mock_repository.get_by_city = MagicMock(side_effect=get_by_city)
        mock_repository.find_nearby = MagicMock(return_value=[])

        await service.resolve("Nowhere City")

        # " city" is the first suffix in _CITY_SUFFIXES — "Nowhere City" → "Nowhere"
        # After that single suffix attempt, loop breaks — no further stripping
        suffix_stripped_calls = [c for c in city_lookup_calls if c != "Nowhere City"]
        assert suffix_stripped_calls == ["Nowhere"], (
            f"Expected only ['Nowhere'] from suffix stripping, got {suffix_stripped_calls}"
        )
