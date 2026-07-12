"""Tests for GeminiLLMService implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integrations.llm.dto import LLMResponse
from integrations.llm.exceptions import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from integrations.llm.gemini import GeminiLLMService


class MockUsageMetadata:
    """Mock for Gemini usage metadata."""

    def __init__(
        self,
        prompt_token_count: int = 10,
        candidates_token_count: int = 20,
        total_token_count: int = 30,
    ) -> None:
        self.prompt_token_count = prompt_token_count
        self.candidates_token_count = candidates_token_count
        self.total_token_count = total_token_count


class MockGeminiResponse:
    """Mock for Gemini API response."""

    def __init__(
        self,
        text: str = "Mock response",
        usage_metadata: MockUsageMetadata | None = None,
    ) -> None:
        self.text = text
        self.usage_metadata = usage_metadata or MockUsageMetadata()


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings with API key."""
    settings_mock = MagicMock()
    settings_mock.GEMINI_API_KEY = "test-api-key"  # pragma: allowlist secret
    settings_mock.GOOGLE_API_KEY = None
    return settings_mock


@pytest.fixture
def mock_genai_client() -> MagicMock:
    """Create mock google-genai Client."""
    client_mock = MagicMock()
    client_mock.aio.models.generate_content = AsyncMock(
        return_value=MockGeminiResponse()
    )
    return client_mock


class TestGeminiLLMServiceInit:
    """Tests for GeminiLLMService initialization."""

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    def test_init_with_gemini_api_key(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test initialization with GEMINI_API_KEY stores the key."""
        mock_settings.GEMINI_API_KEY = "test-gemini-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        service = GeminiLLMService()

        # Client not created during init (lazy initialization)
        mock_client_class.assert_not_called()
        assert service._api_key == "test-gemini-key"  # pragma: allowlist secret
        assert service._default_model == "gemini-2.5-flash"

        # Client created on first use via _ensure_client
        service._ensure_client()
        mock_client_class.assert_called_once_with(
            api_key="test-gemini-key"  # pragma: allowlist secret
        )

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    def test_init_with_google_api_key_fallback(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test initialization falls back to GOOGLE_API_KEY."""
        mock_settings.GEMINI_API_KEY = None
        mock_settings.GOOGLE_API_KEY = "test-google-key"  # pragma: allowlist secret

        service = GeminiLLMService()

        # Client not created during init
        mock_client_class.assert_not_called()
        assert service._api_key == "test-google-key"  # pragma: allowlist secret

        # Client created on first use
        service._ensure_client()
        mock_client_class.assert_called_once_with(
            api_key="test-google-key"  # pragma: allowlist secret
        )

    @patch("integrations.llm.gemini.settings")
    def test_init_no_api_key_succeeds_but_warns(self, mock_settings: MagicMock) -> None:
        """Test initialization succeeds without API key (lazy validation)."""
        mock_settings.GEMINI_API_KEY = None
        mock_settings.GOOGLE_API_KEY = None

        # Should not raise during init - matches legacy SDK behavior
        service = GeminiLLMService()

        assert service._api_key is None
        assert service._client is None

    @patch("integrations.llm.gemini.settings")
    @pytest.mark.asyncio
    async def test_generate_content_no_api_key_raises(
        self, mock_settings: MagicMock
    ) -> None:
        """Test generate_content raises error when no API key is configured."""
        mock_settings.GEMINI_API_KEY = None
        mock_settings.GOOGLE_API_KEY = None

        service = GeminiLLMService()

        with pytest.raises(LLMAuthenticationError) as exc_info:
            await service.generate_content("Test prompt")

        assert "No Gemini API key configured" in str(exc_info.value)
        assert exc_info.value.provider == "gemini"

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    def test_init_with_custom_model(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test initialization with custom model."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        service = GeminiLLMService(model="gemini-pro")

        assert service._default_model == "gemini-pro"


class TestGeminiLLMServiceGenerateContent:
    """Tests for generate_content method."""

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_generate_content_success(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test successful content generation."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        mock_response = MockGeminiResponse(
            text="Generated response",
            usage_metadata=MockUsageMetadata(
                prompt_token_count=10, candidates_token_count=20, total_token_count=30
            ),
        )
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        service = GeminiLLMService()
        response = await service.generate_content("Test prompt")

        assert isinstance(response, LLMResponse)
        assert response.text == "Generated response"
        assert response.model == "gemini-2.5-flash"
        assert response.usage is not None
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 30
        assert response.response_time_ms >= 0

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_generate_content_with_custom_model(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test content generation with custom model override."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=MockGeminiResponse()
        )
        mock_client_class.return_value = mock_client

        service = GeminiLLMService()
        response = await service.generate_content("Test", model="gemini-pro")

        mock_client.aio.models.generate_content.assert_called_once()
        call_kwargs = mock_client.aio.models.generate_content.call_args
        assert call_kwargs.kwargs["model"] == "gemini-pro"

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_generate_content_empty_response_raises(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test that empty response raises LLMResponseError."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        mock_response = MagicMock()
        mock_response.text = None  # Empty response
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        service = GeminiLLMService()

        with pytest.raises(LLMResponseError) as exc_info:
            await service.generate_content("Test prompt")

        assert "empty response" in str(exc_info.value)
        assert exc_info.value.provider == "gemini"

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_generate_content_auth_error(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test authentication error handling."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=Exception("API key invalid or authentication failed")
        )
        mock_client_class.return_value = mock_client

        service = GeminiLLMService()

        with pytest.raises(LLMAuthenticationError) as exc_info:
            await service.generate_content("Test")

        assert "authentication" in str(exc_info.value).lower()

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_generate_content_rate_limit_error(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test rate limit error handling."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )
        mock_client_class.return_value = mock_client

        service = GeminiLLMService()

        with pytest.raises(LLMRateLimitError):
            await service.generate_content("Test")

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_generate_content_timeout_error(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test timeout error handling."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=Exception("Request timeout or deadline exceeded")
        )
        mock_client_class.return_value = mock_client

        service = GeminiLLMService()

        with pytest.raises(LLMTimeoutError):
            await service.generate_content("Test")


class TestGeminiLLMServiceHealthCheck:
    """Tests for health_check method."""

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_health_check_success(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test successful health check."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        mock_response = MagicMock()
        mock_response.text = "pong"
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        service = GeminiLLMService()
        result = await service.health_check()

        assert result is True

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_health_check_empty_response(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test health check with empty response returns False."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        mock_response = MagicMock()
        mock_response.text = None
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        service = GeminiLLMService()
        result = await service.health_check()

        assert result is False

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_health_check_exception_returns_false(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test health check returns False on exception."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=Exception("Connection error")
        )
        mock_client_class.return_value = mock_client

        service = GeminiLLMService()
        result = await service.health_check()

        assert result is False
