"""Unit tests for Google Places API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from integrations.googleplaces.client import (
    GooglePlacesClient,
    PlacesAPIError,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def mock_places_search_response() -> dict:
    """Mock Places Text Search API response."""
    return {
        "places": [
            {
                "id": "ChIJN1t_tDeuEmsRUsoyG83frY4",  # pragma: allowlist secret
                "displayName": {"text": "Eiffel Tower"},
                "formattedAddress": "Champ de Mars, 5 Av. Anatole France, 75007 Paris",
                "photos": [
                    {
                        "name": "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/ATCD",  # pragma: allowlist secret
                        "widthPx": 4032,
                        "heightPx": 3024,
                    }
                ],
                "rating": 4.6,
            }
        ],
        "nextPageToken": "token123",
    }


# ==============================================================================
# INIT TESTS
# ==============================================================================


class TestGooglePlacesClientInit:
    """Tests for client initialization."""

    def test_init_with_api_key(self) -> None:
        """Test initialization with explicit API key."""
        client = GooglePlacesClient(api_key="test-key")  # pragma: allowlist secret
        assert client.api_key == "test-key"  # pragma: allowlist secret

    def test_init_uses_google_api_key_from_settings(self) -> None:
        """Test initialization loads GOOGLE_API_KEY from settings."""
        with patch("integrations.googleplaces.client.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = "settings-key"  # pragma: allowlist secret
            mock_settings.GOOGLE_MAPS_API_KEY = None
            client = GooglePlacesClient()
            assert client.api_key == "settings-key"  # pragma: allowlist secret

    def test_init_fallback_to_maps_api_key(self) -> None:
        """Test GOOGLE_MAPS_API_KEY used when GOOGLE_API_KEY is None."""
        with patch("integrations.googleplaces.client.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = None
            mock_settings.GOOGLE_MAPS_API_KEY = "maps-key"  # pragma: allowlist secret
            client = GooglePlacesClient()
            assert client.api_key == "maps-key"  # pragma: allowlist secret


# ==============================================================================
# SEARCH TEXT TESTS
# ==============================================================================


class TestSearchText:
    """Tests for search_text method."""

    @pytest.mark.asyncio
    async def test_search_returns_places(
        self, mock_places_search_response: dict
    ) -> None:
        """Test successful text search returns places and next token."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_places_search_response

        with patch(
            "integrations.googleplaces.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.post = mock_post

            client = GooglePlacesClient(api_key="test-key")
            places, next_token = await client.search_text("Eiffel Tower")

        assert len(places) == 1
        assert places[0]["displayName"]["text"] == "Eiffel Tower"
        assert len(places[0]["photos"]) == 1
        # fmt: off
        assert places[0]["id"] == "ChIJN1t_tDeuEmsRUsoyG83frY4"  # pragma: allowlist secret
        assert places[0]["photos"][0]["name"] == "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/ATCD"  # pragma: allowlist secret
        # fmt: on
        assert next_token == "token123"

    @pytest.mark.asyncio
    async def test_search_raises_when_no_api_key(self) -> None:
        """Test search raises when API key not configured."""
        with patch("integrations.googleplaces.client.settings") as mock_settings:
            mock_settings.GOOGLE_API_KEY = None
            mock_settings.GOOGLE_MAPS_API_KEY = None
            client = GooglePlacesClient()

            with pytest.raises(PlacesAPIError) as exc_info:
                await client.search_text("Eiffel Tower")

        assert "not configured" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_search_raises_on_http_error(self) -> None:
        """Test search raises PlacesAPIError on non-200 response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {
            "error": {"message": "API key invalid", "code": 403},
        }
        mock_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Forbidden", request=MagicMock(), response=mock_resp
            )
        )

        with patch(
            "integrations.googleplaces.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.post = AsyncMock(return_value=mock_resp)

            client = GooglePlacesClient(api_key="test-key")

            with pytest.raises(PlacesAPIError) as exc_info:
                await client.search_text("Eiffel Tower")

        assert exc_info.value.status_code == 403


# ==============================================================================
# GET PHOTO MEDIA TESTS
# ==============================================================================


class TestGetPhotoMedia:
    """Tests for get_photo_media method."""

    @pytest.mark.asyncio
    async def test_get_photo_returns_bytes_and_content_type(self) -> None:
        """Test successful photo fetch returns image bytes and content-type."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        content = b"\xff\xd8\xff\xe0\x00\x10JFIF"  # JPEG header
        mock_resp.headers = {"content-type": "image/jpeg"}
        mock_resp.content = content

        async def mock_aiter_bytes():
            yield content

        mock_resp.aiter_bytes = lambda: mock_aiter_bytes()

        with patch(
            "integrations.googleplaces.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.get = AsyncMock(return_value=mock_resp)

            client = GooglePlacesClient(api_key="test-key")
            result = await client.get_photo_media(
                "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/ATCD",  # pragma: allowlist secret (Google Place ID test fixture)
                max_width_px=400,
            )

        assert result == (content, "image/jpeg")

    @pytest.mark.asyncio
    async def test_get_photo_raises_on_invalid_resource_name(self) -> None:
        """Test get_photo_media raises for invalid resource name."""
        client = GooglePlacesClient(api_key="test-key")

        with pytest.raises(PlacesAPIError) as exc_info:
            await client.get_photo_media("invalid/name")

        assert "Invalid" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_photo_raises_when_no_max_dimension(self) -> None:
        """Test get_photo_media requires maxWidthPx or maxHeightPx."""
        client = GooglePlacesClient(api_key="test-key")

        with pytest.raises(PlacesAPIError) as exc_info:
            await client.get_photo_media(
                "places/ChIJ.../photos/ATCD",
                max_width_px=0,
                max_height_px=None,
            )

        assert (
            "maxWidthPx" in exc_info.value.message
            or "maxHeightPx" in exc_info.value.message
            or "must be specified" in exc_info.value.message
        )

    @pytest.mark.asyncio
    async def test_get_photo_raises_on_403(self) -> None:
        """Test get_photo_media raises PlacesAPIError on 403 response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {
            "error": {"message": "API key invalid", "code": 403},
        }
        mock_resp.text = "Forbidden"

        with patch(
            "integrations.googleplaces.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.get = AsyncMock(return_value=mock_resp)

            client = GooglePlacesClient(api_key="test-key")
            with pytest.raises(PlacesAPIError) as exc_info:
                await client.get_photo_media(
                    "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/ATCD",  # pragma: allowlist secret
                    max_width_px=400,
                )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_photo_raises_on_500(self) -> None:
        """Test get_photo_media raises PlacesAPIError on 500 response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {
            "error": {"message": "Internal server error", "code": 500},
        }
        mock_resp.text = "Internal Server Error"

        with patch(
            "integrations.googleplaces.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.get = AsyncMock(return_value=mock_resp)

            client = GooglePlacesClient(api_key="test-key")
            with pytest.raises(PlacesAPIError) as exc_info:
                await client.get_photo_media(
                    "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/ATCD",  # pragma: allowlist secret
                    max_width_px=400,
                )

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_photo_raises_on_malformed_response(self) -> None:
        """Test get_photo_media handles malformed JSON in error response."""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        mock_resp.text = "Error body"

        with patch(
            "integrations.googleplaces.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.get = AsyncMock(return_value=mock_resp)

            client = GooglePlacesClient(api_key="test-key")
            with pytest.raises(PlacesAPIError) as exc_info:
                await client.get_photo_media(
                    "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/ATCD",  # pragma: allowlist secret
                    max_width_px=400,
                )

        assert exc_info.value.status_code == 403
        assert "Error body" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_photo_raises_on_network_error(self) -> None:
        """Test get_photo_media raises PlacesAPIError on httpx.RequestError."""
        with patch(
            "integrations.googleplaces.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Connection refused")
            )

            client = GooglePlacesClient(api_key="test-key")
            with pytest.raises(PlacesAPIError) as exc_info:
                await client.get_photo_media(
                    "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/ATCD",  # pragma: allowlist secret
                    max_width_px=400,
                )

        assert "Connection refused" in exc_info.value.message


# ==============================================================================
# LIFECYCLE (aclose) TESTS
# ==============================================================================


class TestAclose:
    """Tests for httpx client lifecycle shutdown."""

    @pytest.mark.asyncio
    async def test_aclose_no_op_when_client_never_created(self) -> None:
        """aclose is a no-op when _http_client was never created."""
        client = GooglePlacesClient(api_key="test-key")
        await client.aclose()
        assert client._http_client is None

    @pytest.mark.asyncio
    async def test_aclose_closes_and_clears_http_client(self) -> None:
        """aclose calls aclose on httpx client and clears the reference."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"places": [], "nextPageToken": None}

        with patch(
            "integrations.googleplaces.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_post = AsyncMock(return_value=mock_resp)
            mock_aclose = AsyncMock()
            mock_instance = MagicMock()
            mock_instance.post = mock_post
            mock_instance.aclose = mock_aclose
            mock_client_cls.return_value = mock_instance

            client = GooglePlacesClient(api_key="test-key")
            await client.search_text("test")
            assert client._http_client is mock_instance

            await client.aclose()

        mock_aclose.assert_awaited_once()
        assert client._http_client is None
