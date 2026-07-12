"""Unit tests for the geocoding service.

Tests cover:
- City to country resolution
- Disambiguation of ambiguous city names
- Error handling (API failures, timeouts)
- Response parsing
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.shared.geocoding import (
    GeocodingResult,
    GeocodingService,
    geocode_city,
    get_country_from_city,
)

# ==============================================================================
# FIXTURES - Mock API Responses
# ==============================================================================


@pytest.fixture
def mock_paris_response() -> dict:
    """Mock Google Geocoding API response for Paris (unambiguous)."""
    return {
        "status": "OK",
        "results": [
            {
                "formatted_address": "Paris, France",
                "geometry": {"location": {"lat": 48.8566, "lng": 2.3522}},
                "types": ["locality", "political"],
                "address_components": [
                    {
                        "long_name": "Paris",
                        "short_name": "Paris",
                        "types": ["locality"],
                    },
                    {
                        "long_name": "France",
                        "short_name": "FR",
                        "types": ["country"],
                    },
                ],
            }
        ],
    }


@pytest.fixture
def mock_utrecht_response() -> dict:
    """Mock Google Geocoding API response for Utrecht (ambiguous - NL and ZA)."""
    return {
        "status": "OK",
        "results": [
            {
                "formatted_address": "Utrecht, Netherlands",
                "geometry": {"location": {"lat": 52.0907, "lng": 5.1214}},
                "types": ["locality", "political"],
                "address_components": [
                    {
                        "long_name": "Utrecht",
                        "short_name": "Utrecht",
                        "types": ["locality"],
                    },
                    {
                        "long_name": "Netherlands",
                        "short_name": "NL",
                        "types": ["country"],
                    },
                ],
            },
            {
                "formatted_address": "Utrecht, Free State, South Africa",
                "geometry": {"location": {"lat": -27.6583, "lng": 29.6833}},
                "types": ["locality", "political"],
                "address_components": [
                    {
                        "long_name": "Utrecht",
                        "short_name": "Utrecht",
                        "types": ["locality"],
                    },
                    {
                        "long_name": "South Africa",
                        "short_name": "ZA",
                        "types": ["country"],
                    },
                ],
            },
        ],
    }


@pytest.fixture
def mock_birmingham_response() -> dict:
    """Mock Google Geocoding API response for Birmingham (UK and USA)."""
    return {
        "status": "OK",
        "results": [
            {
                "formatted_address": "Birmingham, UK",
                "geometry": {"location": {"lat": 52.4862, "lng": -1.8904}},
                "types": ["locality", "political"],
                "address_components": [
                    {
                        "long_name": "Birmingham",
                        "short_name": "Birmingham",
                        "types": ["locality"],
                    },
                    {
                        "long_name": "United Kingdom",
                        "short_name": "GB",
                        "types": ["country"],
                    },
                ],
            },
            {
                "formatted_address": "Birmingham, AL, USA",
                "geometry": {"location": {"lat": 33.5186, "lng": -86.8104}},
                "types": ["locality", "political"],
                "address_components": [
                    {
                        "long_name": "Birmingham",
                        "short_name": "Birmingham",
                        "types": ["locality"],
                    },
                    {
                        "long_name": "United States",
                        "short_name": "US",
                        "types": ["country"],
                    },
                ],
            },
        ],
    }


@pytest.fixture
def mock_zero_results_response() -> dict:
    """Mock response when no results found."""
    return {"status": "ZERO_RESULTS", "results": []}


@pytest.fixture
def mock_error_response() -> dict:
    """Mock response for API error."""
    return {"status": "REQUEST_DENIED", "error_message": "API key invalid"}


# ==============================================================================
# UNIT TESTS - GeocodingService
# ==============================================================================


class TestGeocodingService:
    """Tests for GeocodingService class."""

    def test_init_with_api_key(self) -> None:
        """Test initialization with explicit API key."""
        test_key = "test-api-key-value"  # pragma: allowlist secret
        service = GeocodingService(api_key=test_key)
        assert service.api_key == test_key

    def test_init_without_api_key_uses_settings(self) -> None:
        """Test initialization loads API key from settings."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = (
                "mock-settings-value"  # pragma: allowlist secret
            )
            service = GeocodingService()
            assert service.api_key == "mock-settings-value"  # pragma: allowlist secret

    def test_init_warns_when_no_api_key(self) -> None:
        """Test warning logged when no API key available."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = None
            with patch("app.shared.geocoding.logger") as mock_logger:
                service = GeocodingService()
                assert service.api_key is None
                mock_logger.warning.assert_called()


class TestGeocodeCityUnambiguous:
    """Tests for geocoding unambiguous city names."""

    @pytest.mark.asyncio
    async def test_geocode_paris_returns_france(
        self, mock_paris_response: dict
    ) -> None:
        """Test geocoding Paris returns France."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_paris_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            service = GeocodingService(api_key="test-key")
            results = await service.geocode_city("Paris")

            assert len(results) == 1
            assert results[0].city == "Paris"
            assert results[0].country == "France"
            assert results[0].country_code == "FR"
            assert results[0].lat == 48.8566
            assert results[0].lng == 2.3522

    @pytest.mark.asyncio
    async def test_get_country_from_city_paris(self, mock_paris_response: dict) -> None:
        """Test convenience method returns country name."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_paris_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            service = GeocodingService(api_key="test-key")
            country = await service.get_country_from_city("Paris")

            assert country == "France"


class TestGeocodeCityAmbiguous:
    """Tests for geocoding ambiguous city names."""

    @pytest.mark.asyncio
    async def test_geocode_utrecht_returns_multiple_results(
        self, mock_utrecht_response: dict
    ) -> None:
        """Test geocoding Utrecht returns both Netherlands and South Africa."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_utrecht_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            service = GeocodingService(api_key="test-key")
            results = await service.geocode_city("Utrecht")

            assert len(results) == 2
            countries = {r.country for r in results}
            assert "Netherlands" in countries
            assert "South Africa" in countries

    @pytest.mark.asyncio
    async def test_geocode_birmingham_returns_uk_and_usa(
        self, mock_birmingham_response: dict
    ) -> None:
        """Test geocoding Birmingham returns UK and USA."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_birmingham_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            service = GeocodingService(api_key="test-key")
            results = await service.geocode_city("Birmingham")

            assert len(results) == 2
            countries = {r.country for r in results}
            assert "United Kingdom" in countries
            assert "United States" in countries

    @pytest.mark.asyncio
    async def test_get_country_returns_first_result(
        self, mock_utrecht_response: dict
    ) -> None:
        """Test get_country_from_city returns first (most relevant) result."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_utrecht_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            service = GeocodingService(api_key="test-key")
            country = await service.get_country_from_city("Utrecht")

            # First result should be Netherlands (more relevant)
            assert country == "Netherlands"


class TestGeocodeCityErrorHandling:
    """Tests for error handling in geocoding."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_api_key(self) -> None:
        """Test returns empty list when API key not configured."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = None

            service = GeocodingService()
            results = await service.geocode_city("Paris")

            assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_zero_results(
        self, mock_zero_results_response: dict
    ) -> None:
        """Test returns empty list when no results found."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_zero_results_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            service = GeocodingService(api_key="test-key")
            results = await service.geocode_city("NonExistentCity12345")

            assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_api_error(
        self, mock_error_response: dict
    ) -> None:
        """Test returns empty list on API error response."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_error_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            service = GeocodingService(api_key="test-key")
            results = await service.geocode_city("Paris")

            assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_timeout(self) -> None:
        """Test returns empty list on timeout after retries."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            service = GeocodingService(api_key="test-key")
            results = await service.geocode_city("Paris")

            assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_http_error(self) -> None:
        """Test returns empty list on HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Server Error", request=MagicMock(), response=mock_response
                )
            )

            service = GeocodingService(api_key="test-key")
            results = await service.geocode_city("Paris")

            assert results == []

    @pytest.mark.asyncio
    async def test_get_country_returns_none_on_error(self) -> None:
        """Test get_country_from_city returns None on error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            service = GeocodingService(api_key="test-key")
            country = await service.get_country_from_city("Paris")

            assert country is None


class TestDisambiguationFormatting:
    """Tests for formatting disambiguation options."""

    def test_format_single_result(self) -> None:
        """Test formatting single result."""
        results = [
            GeocodingResult(
                city="Paris",
                country="France",
                country_code="FR",
                formatted_address="Paris, France",
                lat=48.8566,
                lng=2.3522,
            )
        ]

        service = GeocodingService(api_key="test-key")
        formatted = service.format_disambiguation_options(results)

        assert formatted == "Paris, France"

    def test_format_multiple_results(self) -> None:
        """Test formatting multiple results for disambiguation."""
        results = [
            GeocodingResult(
                city="Utrecht",
                country="Netherlands",
                country_code="NL",
                formatted_address="Utrecht, Netherlands",
                lat=52.0907,
                lng=5.1214,
            ),
            GeocodingResult(
                city="Utrecht",
                country="South Africa",
                country_code="ZA",
                formatted_address="Utrecht, South Africa",
                lat=-27.6583,
                lng=29.6833,
            ),
        ]

        service = GeocodingService(api_key="test-key")
        formatted = service.format_disambiguation_options(results)

        assert "Did you mean:" in formatted
        assert "1. Utrecht, Netherlands" in formatted
        assert "2. Utrecht, South Africa" in formatted

    def test_format_empty_results(self) -> None:
        """Test formatting empty results."""
        service = GeocodingService(api_key="test-key")
        formatted = service.format_disambiguation_options([])

        assert formatted == ""


class TestReverseGeocodeRefinement:
    """Tests for reverse geocode city refinement (landmarks/POIs)."""

    @pytest.fixture
    def mock_disney_forward_response(self) -> dict:
        """Mock forward geocode for 'Walt Disney World' — returns Florida (state)."""
        return {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "Walt Disney World Resort, Orlando, FL, USA",
                    "geometry": {"location": {"lat": 28.3772, "lng": -81.5707}},
                    "types": ["amusement_park", "point_of_interest", "establishment"],
                    "address_components": [
                        {
                            "long_name": "Walt Disney World Resort",
                            "short_name": "Walt Disney World Resort",
                            "types": [
                                "amusement_park",
                                "point_of_interest",
                                "establishment",
                            ],
                        },
                        {
                            "long_name": "Florida",
                            "short_name": "FL",
                            "types": ["administrative_area_level_1", "political"],
                        },
                        {
                            "long_name": "United States",
                            "short_name": "US",
                            "types": ["country", "political"],
                        },
                    ],
                }
            ],
        }

    @pytest.fixture
    def mock_disney_reverse_response(self) -> dict:
        """Mock reverse geocode at Disney World coords — returns Kissimmee."""
        return {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "Kissimmee, FL, USA",
                    "geometry": {"location": {"lat": 28.2920, "lng": -81.4076}},
                    "types": ["locality", "political"],
                    "address_components": [
                        {
                            "long_name": "Kissimmee",
                            "short_name": "Kissimmee",
                            "types": ["locality", "political"],
                        },
                        {
                            "long_name": "United States",
                            "short_name": "US",
                            "types": ["country", "political"],
                        },
                    ],
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_landmark_refined_to_nearest_city(
        self,
        mock_disney_forward_response: dict,
        mock_disney_reverse_response: dict,
    ) -> None:
        """Test that a landmark query gets refined to the nearest city via reverse geocode."""
        forward_resp = MagicMock()
        forward_resp.json.return_value = mock_disney_forward_response
        forward_resp.raise_for_status = MagicMock()

        reverse_resp = MagicMock()
        reverse_resp.json.return_value = mock_disney_reverse_response
        reverse_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            # First call = forward geocode, second call = reverse geocode
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=[forward_resp, reverse_resp]
            )

            service = GeocodingService(api_key="test-key")
            results = await service.geocode_city("Walt Disney World")

            assert len(results) == 1
            # City should be refined from "Florida" to "Kissimmee"
            assert results[0].city == "Kissimmee"
            assert results[0].country == "United States"
            # Coordinates should remain the LANDMARK coords (for nearby sorting)
            assert results[0].lat == 28.3772
            assert results[0].lng == -81.5707

    @pytest.mark.asyncio
    async def test_landmark_keeps_original_when_reverse_fails(
        self,
        mock_disney_forward_response: dict,
    ) -> None:
        """Test that reverse geocode failure falls back to original result."""
        forward_resp = MagicMock()
        forward_resp.json.return_value = mock_disney_forward_response
        forward_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=[forward_resp, httpx.TimeoutException("Timeout")]
            )

            service = GeocodingService(api_key="test-key")
            results = await service.geocode_city("Walt Disney World")

            assert len(results) == 1
            # Falls back to original "Florida"
            assert results[0].city == "Florida"

    @pytest.mark.asyncio
    async def test_reverse_geocode_ok_but_empty_results(
        self,
        mock_disney_forward_response: dict,
    ) -> None:
        """Test that reverse geocode returning OK with empty results keeps original city."""
        forward_resp = MagicMock()
        forward_resp.json.return_value = mock_disney_forward_response
        forward_resp.raise_for_status = MagicMock()

        empty_reverse_resp = MagicMock()
        empty_reverse_resp.json.return_value = {"status": "OK", "results": []}
        empty_reverse_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=[forward_resp, empty_reverse_resp]
            )

            service = GeocodingService(api_key="test-key")
            results = await service.geocode_city("Walt Disney World")

            assert len(results) == 1
            # Falls back to original "Florida" since reverse returned no results
            assert results[0].city == "Florida"

    @pytest.mark.asyncio
    async def test_locality_result_not_refined(self, mock_paris_response: dict) -> None:
        """Test that a normal city (locality) result is NOT reverse geocoded."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_paris_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            service = GeocodingService(api_key="test-key")
            results = await service.geocode_city("Paris")

            assert len(results) == 1
            assert results[0].city == "Paris"
            # Only 1 API call (forward geocode) — no reverse geocode
            assert mock_get.call_count == 1


class TestGeocodingResult:
    """Tests for GeocodingResult model."""

    def test_geocoding_result_creation(self) -> None:
        """Test creating a GeocodingResult."""
        result = GeocodingResult(
            city="Amsterdam",
            country="Netherlands",
            country_code="NL",
            formatted_address="Amsterdam, Netherlands",
            lat=52.3676,
            lng=4.9041,
        )

        assert result.city == "Amsterdam"
        assert result.country == "Netherlands"
        assert result.country_code == "NL"
        assert result.lat == 52.3676
        assert result.lng == 4.9041


# ==============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# ==============================================================================


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_geocode_city_function(self, mock_paris_response: dict) -> None:
        """Test module-level geocode_city function."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_paris_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            with patch("app.core.config.settings") as mock_settings:
                mock_settings.GOOGLE_API_KEY = "test-key"  # pragma: allowlist secret

                results = await geocode_city("Paris")

                assert len(results) == 1
                assert results[0].country == "France"

    @pytest.mark.asyncio
    async def test_get_country_from_city_function(
        self, mock_paris_response: dict
    ) -> None:
        """Test module-level get_country_from_city function."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_paris_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            with patch("app.core.config.settings") as mock_settings:
                mock_settings.GOOGLE_API_KEY = "test-key"  # pragma: allowlist secret

                country = await get_country_from_city("Paris")

                assert country == "France"
