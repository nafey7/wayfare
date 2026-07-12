"""Unit tests for ActiveCampaign integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from integrations.activecampaign.client import (
    ActiveCampaignClient,
    ContactSyncResult,
    _reset_client_for_tests,
    get_activecampaign_client,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the module-level singleton between tests."""
    _reset_client_for_tests()
    yield
    _reset_client_for_tests()


def _mock_httpx_response(
    status_code: int, text: str = "", json_data: dict | None = None
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json = MagicMock(return_value=json_data or {})
    return resp


# ==============================================================================
# INIT TESTS
# ==============================================================================


class TestActiveCampaignClientInit:
    def test_init_requires_api_url(self) -> None:
        with pytest.raises(ValueError, match="api_url is required"):
            ActiveCampaignClient(api_url="", api_key="k")  # pragma: allowlist secret

    def test_init_requires_api_key(self) -> None:
        with pytest.raises(ValueError, match="api_key is required"):
            ActiveCampaignClient(api_url="https://x.api-ac.com", api_key="")

    def test_init_strips_trailing_slash(self) -> None:
        c = ActiveCampaignClient(
            api_url="https://x.api-ac.com/",
            api_key="k",  # pragma: allowlist secret
        )
        # private attribute is fine to assert on in unit tests
        assert c._api_url == "https://x.api-ac.com"


# ==============================================================================
# CREATE CONTACT TESTS
# ==============================================================================


class TestCreateContact:
    @pytest.mark.asyncio
    async def test_returns_failure_when_email_missing(self) -> None:
        client = ActiveCampaignClient(
            api_url="https://x.api-ac.com",
            api_key="k",  # pragma: allowlist secret
        )
        result = await client.create_contact(email="")
        assert result.success is False
        assert result.error_message == "email is required"

    @pytest.mark.asyncio
    async def test_success_on_201(self) -> None:
        post_mock = AsyncMock(return_value=_mock_httpx_response(201))

        with patch(
            "integrations.activecampaign.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value.post = post_mock

            client = ActiveCampaignClient(
                api_url="https://x.api-ac.com",
                api_key="k",  # pragma: allowlist secret
            )
            result = await client.create_contact(
                email="alice@example.com",
                first_name="Alice",
                last_name="Smith",
            )

        assert result.success is True
        assert result.status_code == 201
        post_mock.assert_called_once()
        _, kwargs = post_mock.call_args
        assert kwargs["json"] == {
            "contact": {
                "email": "alice@example.com",
                "firstName": "Alice",
                "lastName": "Smith",
            }
        }
        assert kwargs["headers"]["Api-Token"] == "k"
        assert kwargs["headers"]["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_success_on_200(self) -> None:
        post_mock = AsyncMock(return_value=_mock_httpx_response(200))

        with patch(
            "integrations.activecampaign.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value.post = post_mock

            client = ActiveCampaignClient(
                api_url="https://x.api-ac.com",
                api_key="k",  # pragma: allowlist secret
            )
            result = await client.create_contact(email="a@b.com")

        assert result.success is True
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_duplicate_422_is_treated_as_success(self) -> None:
        post_mock = AsyncMock(
            return_value=_mock_httpx_response(
                422, text='{"errors": [{"title": "Email address already exists"}]}'
            )
        )

        with patch(
            "integrations.activecampaign.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value.post = post_mock

            client = ActiveCampaignClient(
                api_url="https://x.api-ac.com",
                api_key="k",  # pragma: allowlist secret
            )
            result = await client.create_contact(email="dup@example.com")

        assert result.success is True
        assert result.status_code == 422

    @pytest.mark.asyncio
    async def test_non_2xx_non_422_returns_failure(self) -> None:
        post_mock = AsyncMock(
            return_value=_mock_httpx_response(500, text="internal server error")
        )

        with patch(
            "integrations.activecampaign.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value.post = post_mock

            client = ActiveCampaignClient(
                api_url="https://x.api-ac.com",
                api_key="k",  # pragma: allowlist secret
            )
            result = await client.create_contact(email="a@b.com")

        assert result.success is False
        assert result.status_code == 500
        assert "500" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_timeout_is_swallowed(self) -> None:
        post_mock = AsyncMock(side_effect=httpx.TimeoutException("slow"))

        with patch(
            "integrations.activecampaign.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value.post = post_mock

            client = ActiveCampaignClient(
                api_url="https://x.api-ac.com",
                api_key="k",  # pragma: allowlist secret
            )
            result = await client.create_contact(email="a@b.com")

        assert result.success is False
        assert "timeout" in (result.error_message or "").lower()

    @pytest.mark.asyncio
    async def test_network_error_is_swallowed(self) -> None:
        post_mock = AsyncMock(side_effect=httpx.ConnectError("unreachable"))

        with patch(
            "integrations.activecampaign.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value.post = post_mock

            client = ActiveCampaignClient(
                api_url="https://x.api-ac.com",
                api_key="k",  # pragma: allowlist secret
            )
            result = await client.create_contact(email="a@b.com")

        assert result.success is False
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_only_email_in_payload_when_names_missing(self) -> None:
        post_mock = AsyncMock(return_value=_mock_httpx_response(201))

        with patch(
            "integrations.activecampaign.client.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client_cls.return_value.__aenter__.return_value.post = post_mock

            client = ActiveCampaignClient(
                api_url="https://x.api-ac.com",
                api_key="k",  # pragma: allowlist secret
            )
            result = await client.create_contact(email="a@b.com")

        assert result.success is True
        _, kwargs = post_mock.call_args
        assert kwargs["json"] == {"contact": {"email": "a@b.com"}}


# ==============================================================================
# SINGLETON / CONFIG TESTS
# ==============================================================================


class TestGetActiveCampaignClient:
    def test_returns_none_when_api_url_missing(self) -> None:
        with patch("integrations.activecampaign.client.settings") as mock_settings:
            mock_settings.ACTIVECAMPAIGN_API_URL = None
            mock_settings.ACTIVECAMPAIGN_API_KEY = "k"  # pragma: allowlist secret
            assert get_activecampaign_client() is None

    def test_returns_none_when_api_key_missing(self) -> None:
        with patch("integrations.activecampaign.client.settings") as mock_settings:
            mock_settings.ACTIVECAMPAIGN_API_URL = "https://x.api-ac.com"
            mock_settings.ACTIVECAMPAIGN_API_KEY = None
            assert get_activecampaign_client() is None

    def test_returns_client_when_configured(self) -> None:
        with patch("integrations.activecampaign.client.settings") as mock_settings:
            mock_settings.ACTIVECAMPAIGN_API_URL = "https://x.api-ac.com"
            mock_settings.ACTIVECAMPAIGN_API_KEY = "k"  # pragma: allowlist secret
            c = get_activecampaign_client()
            assert isinstance(c, ActiveCampaignClient)

    def test_singleton_reused_across_calls(self) -> None:
        with patch("integrations.activecampaign.client.settings") as mock_settings:
            mock_settings.ACTIVECAMPAIGN_API_URL = "https://x.api-ac.com"
            mock_settings.ACTIVECAMPAIGN_API_KEY = "k"  # pragma: allowlist secret
            first = get_activecampaign_client()
            second = get_activecampaign_client()
            assert first is second

    def test_disabled_state_cached(self) -> None:
        """Once disabled, subsequent calls short-circuit without re-reading settings."""
        with patch("integrations.activecampaign.client.settings") as mock_settings:
            mock_settings.ACTIVECAMPAIGN_API_URL = None
            mock_settings.ACTIVECAMPAIGN_API_KEY = None
            assert get_activecampaign_client() is None
            # Flip the settings - should still return None because disabled is cached
            mock_settings.ACTIVECAMPAIGN_API_URL = "https://x.api-ac.com"
            mock_settings.ACTIVECAMPAIGN_API_KEY = "k"  # pragma: allowlist secret
            assert get_activecampaign_client() is None


# ==============================================================================
# DATACLASS TESTS
# ==============================================================================


class TestContactSyncResult:
    def test_defaults(self) -> None:
        r = ContactSyncResult(success=True)
        assert r.success is True
        assert r.status_code is None
        assert r.error_message is None

    def test_frozen(self) -> None:
        r = ContactSyncResult(success=True)
        with pytest.raises(Exception):
            r.success = False  # type: ignore[misc]
