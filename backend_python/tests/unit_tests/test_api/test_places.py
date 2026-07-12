"""Unit tests for Places API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

import app.api.places as places_module
from app.api.places import router as places_router

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_places_client():
    """Mock Google Places client for API tests."""
    client = MagicMock()
    client.search_text = AsyncMock(
        return_value=(
            [
                {
                    "id": "ChIJ123",
                    "displayName": {"text": "Eiffel Tower"},
                    "formattedAddress": "Paris, France",
                    "photos": [
                        {
                            "name": "places/ChIJ123/photos/ATCD",
                            "widthPx": 800,
                            "heightPx": 600,
                        }
                    ],
                    "rating": 4.6,
                }
            ],
            None,
        )
    )
    client.get_photo_media = AsyncMock(return_value=(b"\xff\xd8\xffJPEG", "image/jpeg"))
    client.resolve_place_image_url = AsyncMock(
        return_value="http://localhost:8000/api/places/photos/places/ChIJ123/photos/ATCD/media?maxWidthPx=800"
    )
    return client


@pytest.fixture
def mock_auth_user() -> MagicMock:
    """Mock authenticated user for Places API tests. User object is never inspected."""
    return MagicMock()


@pytest.fixture
def places_app(mock_auth_user):
    """Minimal FastAPI app with only places router and auth override."""
    app = FastAPI()

    async def override_require_authenticated():
        return mock_auth_user

    app.include_router(places_router)
    app.dependency_overrides[places_module.require_authenticated] = (
        override_require_authenticated
    )
    return app


@pytest.fixture
def client_with_mock(mock_places_client, places_app):
    """Test client with mocked Places API."""
    with patch.object(
        places_module,
        "_get_client",
        return_value=mock_places_client,
    ):
        yield TestClient(places_app)


@pytest.fixture
def unauthenticated_places_app():
    """Minimal FastAPI app that rejects authenticated endpoints."""
    app = FastAPI()

    async def override_require_authenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    app.include_router(places_router)
    app.dependency_overrides[places_module.require_authenticated] = (
        override_require_authenticated
    )
    return app


@pytest.fixture
def unauthenticated_client_with_mock(mock_places_client, unauthenticated_places_app):
    """Test client with mocked Places API and rejected auth."""
    with patch.object(
        places_module,
        "_get_client",
        return_value=mock_places_client,
    ):
        yield TestClient(unauthenticated_places_app)


# ==============================================================================
# SEARCH ENDPOINT TESTS
# ==============================================================================


class TestSearchPlaces:
    """Tests for POST /api/places/search."""

    def test_search_returns_places(self, client_with_mock, mock_places_client) -> None:
        """Test search endpoint returns place results."""
        response = client_with_mock.post(
            "/places/search",
            json={"textQuery": "Eiffel Tower"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "places" in data
        assert len(data["places"]) == 1
        # API returns camelCase (displayName) per response model
        place = data["places"][0]
        assert place["displayName"] == "Eiffel Tower"
        assert len(place["photos"]) == 1
        assert "places/ChIJ123/photos/ATCD" in place["photos"][0]["name"]

    def test_search_validates_text_query(self, client_with_mock) -> None:
        """Test search requires non-empty textQuery."""
        response = client_with_mock.post(
            "/places/search",
            json={"textQuery": ""},
        )
        assert response.status_code == 422

    def test_search_accepts_page_params(
        self, client_with_mock, mock_places_client
    ) -> None:
        """Test search accepts pageSize and pageToken."""
        response = client_with_mock.post(
            "/places/search",
            json={
                "textQuery": "Paris",
                "pageSize": 10,
                "pageToken": "next123",
            },
        )
        assert response.status_code == 200
        mock_places_client.search_text.assert_called_once()
        call_kwargs = mock_places_client.search_text.call_args[1]
        assert call_kwargs["page_size"] == 10
        assert call_kwargs["page_token"] == "next123"


# ==============================================================================
# PHOTO MEDIA ENDPOINT TESTS
# ==============================================================================


class TestGetPlacePhoto:
    """Tests for GET /api/places/photos/{path}/media."""

    def test_photo_returns_image(self, client_with_mock, mock_places_client) -> None:
        """Test photo endpoint streams image bytes."""
        response = client_with_mock.get(
            "/places/photos/places/ChIJ123/photos/ATCD/media",
            params={"maxWidthPx": 400},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert response.headers["cache-control"] == "private, max-age=86400"
        assert response.content == b"\xff\xd8\xffJPEG"

    def test_photo_requires_auth(
        self, unauthenticated_client_with_mock, mock_places_client
    ) -> None:
        """Test photo endpoint rejects unauthenticated requests."""
        response = unauthenticated_client_with_mock.get(
            "/places/photos/places/ChIJ123/photos/ATCD/media",
            params={"maxWidthPx": 400},
        )

        assert response.status_code == 401
        mock_places_client.get_photo_media.assert_not_called()

    def test_photo_404_when_not_found(
        self, client_with_mock, mock_places_client
    ) -> None:
        """Test photo returns 404 when Places API returns not found."""
        from integrations.googleplaces.client import PlacesAPIError

        mock_places_client.get_photo_media = AsyncMock(
            side_effect=PlacesAPIError("Photo not found", 404)
        )

        response = client_with_mock.get(
            "/places/photos/places/ChIJ999/photos/ATCD/media",
            params={"maxWidthPx": 400},
        )

        assert response.status_code == 404

    def test_photo_400_on_path_traversal(self, client_with_mock) -> None:
        """Test photo returns 400 for path traversal attempts (SSRF protection)."""
        # Dots and slashes in photo ref invalidate the resource pattern
        response = client_with_mock.get(
            "/places/photos/places/ChIJ123/photos/../../../etc/passwd/media",
        )
        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]

        # Invalid format - empty place ID segment
        response = client_with_mock.get(
            "/places/photos/places//photos/ATCD/media",
        )
        assert response.status_code == 400

    def test_photo_502_on_request_error(
        self, client_with_mock, mock_places_client
    ) -> None:
        """Test photo returns 502 when network/RequestError occurs."""
        from integrations.googleplaces.client import PlacesAPIError

        mock_places_client.get_photo_media = AsyncMock(
            side_effect=PlacesAPIError(
                "Places photo request failed: Connection refused"
            )
        )

        response = client_with_mock.get(
            "/places/photos/places/ChIJ123/photos/ATCD/media",
            params={"maxWidthPx": 400},
        )
        assert response.status_code == 502

    def test_search_validates_max_length(self, client_with_mock) -> None:
        """Test search rejects textQuery over 500 chars."""
        response = client_with_mock.post(
            "/places/search",
            json={"textQuery": "x" * 501},
        )
        assert response.status_code == 422


# ==============================================================================
# IMAGE URL ENDPOINT TESTS
# ==============================================================================


class TestGetPlaceImageUrl:
    """Tests for GET /api/places/image-url."""

    def test_returns_proxy_url(self, client_with_mock, mock_places_client) -> None:
        """Test image-url returns proxy URL for first place's first photo."""
        response = client_with_mock.get(
            "/places/image-url",
            params={"place": "Eiffel Tower"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "imageUrl" in data
        assert "/api/places/photos/" in data["imageUrl"]
        assert "places/ChIJ123/photos/ATCD" in data["imageUrl"]
        # Verify resolve_place_image_url was called with correct args
        mock_places_client.resolve_place_image_url.assert_called_once_with(
            "Eiffel Tower", 800
        )

    def test_respects_max_width_param(
        self, client_with_mock, mock_places_client
    ) -> None:
        """Test image-url passes maxWidthPx to resolve function."""
        mock_places_client.resolve_place_image_url = AsyncMock(
            return_value="http://localhost:8000/api/places/photos/places/ChIJ123/photos/ATCD/media?maxWidthPx=400"
        )

        response = client_with_mock.get(
            "/places/image-url",
            params={"place": "Eiffel Tower", "max_width_px": 400},
        )

        assert response.status_code == 200
        assert "maxWidthPx=400" in response.json()["imageUrl"]
        mock_places_client.resolve_place_image_url.assert_called_once_with(
            "Eiffel Tower", 400
        )

    def test_404_when_no_image(self, client_with_mock, mock_places_client) -> None:
        """Test image-url returns 404 when resolve returns None."""
        mock_places_client.resolve_place_image_url = AsyncMock(return_value=None)

        response = client_with_mock.get(
            "/places/image-url",
            params={"place": "NonexistentPlace12345"},
        )

        assert response.status_code == 404

    def test_404_when_no_photos(self, client_with_mock, mock_places_client) -> None:
        """Test image-url returns 404 when resolve returns None (no photos)."""
        mock_places_client.resolve_place_image_url = AsyncMock(return_value=None)

        response = client_with_mock.get(
            "/places/image-url",
            params={"place": "Place Without Photos"},
        )

        assert response.status_code == 404

    def test_hotel_name_city_format_passed_through(
        self, client_with_mock, mock_places_client
    ) -> None:
        """Test place=HotelName, City format is passed through for hotel fallback."""
        mock_places_client.resolve_place_image_url = AsyncMock(
            return_value="http://localhost:8000/api/places/photos/places/ChIJx/photos/ATCD/media?maxWidthPx=400"
        )

        response = client_with_mock.get(
            "/places/image-url",
            params={"place": "Hilton Paris Opera, Paris", "max_width_px": 400},
        )

        assert response.status_code == 200
        mock_places_client.resolve_place_image_url.assert_called_once_with(
            "Hilton Paris Opera, Paris", 400
        )


# ==============================================================================
# RATE LIMIT TESTS
# ==============================================================================


@patch("app.core.places_rate_limit.settings")
@patch("app.core.places_rate_limit.PLACES_SEARCH_RATE_LIMIT_PER_MINUTE", 3)
class TestPlacesSearchRateLimitIntegration:
    """Integration tests: search/image-url endpoints return 429 when over limit."""

    def test_search_429_after_limit(
        self, mock_settings: MagicMock, client_with_mock: TestClient
    ) -> None:
        """Exactly LIMIT search requests succeed; next returns 429."""
        mock_settings.RATE_LIMIT_ENABLED = True
        headers = {"X-Forwarded-For": "rate-limit-test-search"}

        limit = 3  # Patched in class decorator
        for _ in range(limit):
            resp = client_with_mock.post(
                "/places/search",
                json={"textQuery": "Paris"},
                headers=headers,
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        resp = client_with_mock.post(
            "/places/search",
            json={"textQuery": "Paris"},
            headers=headers,
        )
        assert resp.status_code == 429
        assert "detail" in resp.json()

    def test_image_url_429_after_limit(
        self, mock_settings: MagicMock, client_with_mock: TestClient
    ) -> None:
        """Exactly LIMIT image-url requests succeed; next returns 429."""
        mock_settings.RATE_LIMIT_ENABLED = True
        headers = {"X-Forwarded-For": "rate-limit-test-image-url"}

        limit = 3  # Patched in class decorator
        for _ in range(limit):
            resp = client_with_mock.get(
                "/places/image-url",
                params={"place": "Eiffel Tower"},
                headers=headers,
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        resp = client_with_mock.get(
            "/places/image-url",
            params={"place": "Eiffel Tower"},
            headers=headers,
        )
        assert resp.status_code == 429


@patch("app.core.places_rate_limit.settings")
@patch("app.core.places_rate_limit.PLACES_PHOTO_RATE_LIMIT_PER_MINUTE", 5)
class TestPlacesPhotoRateLimitIntegration:
    """Integration tests: photo media endpoint returns 429 when over limit."""

    def test_photo_429_after_limit(
        self, mock_settings: MagicMock, client_with_mock: TestClient
    ) -> None:
        """Exactly LIMIT photo requests succeed; next returns 429."""
        mock_settings.RATE_LIMIT_ENABLED = True
        headers = {"X-Forwarded-For": "rate-limit-test-photo"}
        url = "/places/photos/places/ChIJ123/photos/ATCD/media"

        limit = 5  # Patched in class decorator
        for _ in range(limit):
            resp = client_with_mock.get(
                url, params={"maxWidthPx": 400}, headers=headers
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

        resp = client_with_mock.get(url, params={"maxWidthPx": 400}, headers=headers)
        assert resp.status_code == 429
