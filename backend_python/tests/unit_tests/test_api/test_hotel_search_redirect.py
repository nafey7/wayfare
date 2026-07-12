"""Unit tests for hotel search redirect API endpoint."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from app.api.hotels import (
    HotelSearchRedirectRequest,
    HotelSearchRedirectResponse,
    search_redirect,
)
from app.domains.common.enums import AuthProvider
from app.domains.hotel.service import HotelService
from app.domains.user.enums import UserRole, UserStatus
from app.domains.user.schemas import UserPublic


@pytest.fixture
def mock_user() -> UserPublic:
    """Mock authenticated user for testing."""
    return UserPublic(
        id="507f1f77bcf86cd799439011",
        email="user@example.com",
        first_name="Test",
        last_name="User",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        auth_provider=AuthProvider.LOCAL,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_hotel_service():
    """Mock HotelService for testing."""
    service = Mock(spec=HotelService)
    service.current_user = None
    return service


@pytest.fixture
def mock_authenticated_hotel_service(mock_user):
    """Mock HotelService with authenticated user."""
    service = Mock(spec=HotelService)
    service.current_user = mock_user
    return service


class TestHotelSearchRedirect:
    """Test cases for /api/hotels/search-redirect endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_search_redirect_with_authenticated_user(
        self,
        mock_logger,
        mock_settings,
        mock_authenticated_hotel_service,
        mock_user: UserPublic,
    ):
        """Test search redirect generates URL with auth token for authenticated user."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="Paris",
            country="France",
            check_in_date="2026-04-15",
            check_out_date="2026-04-20",
            rooms=2,
            adults=4,
            children=1,
        )

        result = await search_redirect(request, mock_authenticated_hotel_service)

        assert isinstance(result, HotelSearchRedirectResponse)
        redirect_url = result.redirect_url

        # Verify URL structure
        assert redirect_url.startswith(
            "https://test.example.com/dev/hotel-booker/index.html?"
        )

        # Parse URL to check parameters
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)

        assert params["destination_city"][0] == "Paris"
        assert params["country"][0] == "France"
        assert params["check_in_date"][0] == "2026-04-15"
        assert params["check_out_date"][0] == "2026-04-20"
        assert params["rooms"][0] == "2"
        assert params["adults"][0] == "4"
        assert params["children"][0] == "1"
        assert params["source"][0] == "chat_results"
        assert params["auto_search"][0] == "true"
        assert (
            params["initial_step"][0] == "results"
        )  # Hide search step; show results (like flight initial_step=select)
        assert "auth_token" in params  # Should have auth token for authenticated user

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_search_redirect_without_authentication(
        self, mock_logger, mock_settings, mock_hotel_service
    ):
        """Test search redirect generates URL without auth token for unauthenticated user."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="London",
            check_in_date="2026-04-10",
            check_out_date="2026-04-15",
            rooms=1,
            adults=2,
            children=0,
        )

        result = await search_redirect(request, mock_hotel_service)

        assert isinstance(result, HotelSearchRedirectResponse)
        redirect_url = result.redirect_url

        # Verify URL structure
        assert redirect_url.startswith(
            "https://test.example.com/dev/hotel-booker/index.html?"
        )

        # Parse URL to check parameters
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)

        assert params["destination_city"][0] == "London"
        assert params["check_in_date"][0] == "2026-04-10"
        assert params["check_out_date"][0] == "2026-04-15"
        assert params["rooms"][0] == "1"
        assert params["adults"][0] == "2"
        assert params["children"][0] == "0"
        assert params["source"][0] == "chat_results"
        assert params["auto_search"][0] == "true"
        assert params["initial_step"][0] == "results"
        assert "auth_token" not in params  # Should NOT have auth token

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_search_redirect_without_country(
        self, mock_logger, mock_settings, mock_hotel_service
    ):
        """Test search redirect works without optional country parameter."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="New York",
            check_in_date="2026-04-20",
            check_out_date="2026-04-25",
            rooms=1,
            adults=2,
            children=0,
        )

        result = await search_redirect(request, mock_hotel_service)

        assert isinstance(result, HotelSearchRedirectResponse)
        redirect_url = result.redirect_url

        # Parse URL to check parameters
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)

        # Country should not be in URL if not provided
        assert "country" not in params
        assert params["destination_city"][0] == "New York"

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_search_redirect_token_generation_failure(
        self, mock_logger, mock_settings, mock_authenticated_hotel_service
    ):
        """Test search redirect handles token generation failure gracefully."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="Paris",
            check_in_date="2026-04-15",
            check_out_date="2026-04-20",
            rooms=1,
            adults=2,
            children=0,
        )

        # Mock jwt.encode to raise an exception
        with patch("jwt.encode", side_effect=Exception("Token error")):
            result = await search_redirect(request, mock_authenticated_hotel_service)

            # Should still succeed but without auth token
            assert isinstance(result, HotelSearchRedirectResponse)
            redirect_url = result.redirect_url

            # Parse URL to check parameters
            parsed = urlparse(redirect_url)
            params = parse_qs(parsed.query)
            assert "auth_token" not in params

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_search_redirect_date_format_april_2026(
        self, mock_logger, mock_settings, mock_hotel_service
    ):
        """Test search redirect with dates in April 2026 (future dates)."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="Tokyo",
            country="Japan",
            check_in_date="2026-04-01",
            check_out_date="2026-04-10",
            rooms=1,
            adults=2,
            children=0,
        )

        result = await search_redirect(request, mock_hotel_service)

        assert isinstance(result, HotelSearchRedirectResponse)
        redirect_url = result.redirect_url

        # Parse URL to check parameters
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)

        # Verify dates are correctly included
        assert params["check_in_date"][0] == "2026-04-01"
        assert params["check_out_date"][0] == "2026-04-10"


class TestFilterParametersInURL:
    """Test that filter params are correctly included in the redirect URL."""

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_price_filters_in_url(
        self, mock_logger, mock_settings, mock_hotel_service
    ):
        """price_min and price_max appear in redirect URL."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="Rome",
            check_in_date="2026-05-01",
            check_out_date="2026-05-05",
            rooms=1,
            adults=2,
            children=0,
            price_min=80.0,
            price_max=150.0,
        )

        result = await search_redirect(request, mock_hotel_service)
        parsed = urlparse(result.redirect_url)
        params = parse_qs(parsed.query)

        assert params["price_min"][0] == "80.0"
        assert params["price_max"][0] == "150.0"

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_min_rating_in_url(
        self, mock_logger, mock_settings, mock_hotel_service
    ):
        """min_rating appears in redirect URL."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="Paris",
            check_in_date="2026-06-01",
            check_out_date="2026-06-05",
            rooms=1,
            adults=2,
            children=0,
            min_rating=5,
        )

        result = await search_redirect(request, mock_hotel_service)
        parsed = urlparse(result.redirect_url)
        params = parse_qs(parsed.query)

        assert params["min_rating"][0] == "5"

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_property_types_comma_separated_in_url(
        self, mock_logger, mock_settings, mock_hotel_service
    ):
        """property_types is comma-separated in redirect URL."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="Ibiza",
            check_in_date="2026-07-01",
            check_out_date="2026-07-07",
            rooms=1,
            adults=2,
            children=0,
            property_types=["Hotel", "Resort"],
        )

        result = await search_redirect(request, mock_hotel_service)
        parsed = urlparse(result.redirect_url)
        params = parse_qs(parsed.query)

        assert "property_types" in params
        types = params["property_types"][0].split(",")
        assert "Hotel" in types
        assert "Resort" in types

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_refundable_only_in_url(
        self, mock_logger, mock_settings, mock_hotel_service
    ):
        """refundable_only=true appears in redirect URL when set."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="London",
            check_in_date="2026-08-01",
            check_out_date="2026-08-03",
            rooms=1,
            adults=1,
            children=0,
            refundable_only=True,
        )

        result = await search_redirect(request, mock_hotel_service)
        parsed = urlparse(result.redirect_url)
        params = parse_qs(parsed.query)

        assert params["refundable_only"][0] == "true"

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_required_facilities_comma_separated_in_url(
        self, mock_logger, mock_settings, mock_hotel_service
    ):
        """required_facilities is comma-separated in redirect URL."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="Barcelona",
            check_in_date="2026-09-01",
            check_out_date="2026-09-05",
            rooms=1,
            adults=2,
            children=0,
            required_facilities=["pool", "spa"],
        )

        result = await search_redirect(request, mock_hotel_service)
        parsed = urlparse(result.redirect_url)
        params = parse_qs(parsed.query)

        assert "required_facilities" in params
        facilities = params["required_facilities"][0].split(",")
        assert "pool" in facilities
        assert "spa" in facilities

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_max_distance_km_in_url(
        self, mock_logger, mock_settings, mock_hotel_service
    ):
        """max_distance_km appears in redirect URL."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="Amsterdam",
            check_in_date="2026-10-01",
            check_out_date="2026-10-04",
            rooms=1,
            adults=2,
            children=0,
            max_distance_km=2.0,
        )

        result = await search_redirect(request, mock_hotel_service)
        parsed = urlparse(result.redirect_url)
        params = parse_qs(parsed.query)

        assert params["max_distance_km"][0] == "2.0"

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_locality_in_url(
        self, mock_logger, mock_settings, mock_hotel_service
    ):
        """locality appears in redirect URL."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="Paris",
            check_in_date="2026-07-15",
            check_out_date="2026-07-22",
            rooms=1,
            adults=2,
            children=0,
            locality="Montmartre",
        )

        result = await search_redirect(request, mock_hotel_service)
        parsed = urlparse(result.redirect_url)
        params = parse_qs(parsed.query)

        assert params["locality"][0] == "Montmartre"

    @pytest.mark.asyncio
    @patch("app.api.hotels.settings")
    @patch("app.api.hotels.logger")
    async def test_no_filter_params_absent_from_url(
        self, mock_logger, mock_settings, mock_hotel_service
    ):
        """Filter params are absent from URL when not provided."""
        mock_settings.BACKEND_URL = "https://test.example.com"
        mock_settings.SECRET_KEY = "test_secret_key"

        request = HotelSearchRedirectRequest(
            destination_city="Berlin",
            check_in_date="2026-11-01",
            check_out_date="2026-11-05",
            rooms=1,
            adults=2,
            children=0,
        )

        result = await search_redirect(request, mock_hotel_service)
        parsed = urlparse(result.redirect_url)
        params = parse_qs(parsed.query)

        for filter_param in [
            "price_min",
            "price_max",
            "min_rating",
            "property_types",
            "refundable_only",
            "required_facilities",
            "max_distance_km",
            "locality",
        ]:
            assert filter_param not in params
