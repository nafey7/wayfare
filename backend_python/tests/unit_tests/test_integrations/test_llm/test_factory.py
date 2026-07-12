"""Tests for LLM factory and singleton management."""

from unittest.mock import MagicMock, patch

from integrations.llm import get_llm_service, reset_llm_service
from integrations.llm.protocol import LLMService


class TestGetLLMService:
    """Tests for get_llm_service factory function."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_llm_service()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        reset_llm_service()

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    def test_returns_llm_service(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test that factory returns an LLMService instance."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        service = get_llm_service()

        assert isinstance(service, LLMService)

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    def test_returns_singleton(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test that factory returns the same instance on multiple calls."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        service1 = get_llm_service()
        service2 = get_llm_service()

        assert service1 is service2

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    def test_force_new_creates_new_instance(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test that force_new=True creates a new instance."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        service1 = get_llm_service()
        service2 = get_llm_service(force_new=True)

        assert service1 is not service2


class TestResetLLMService:
    """Tests for reset_llm_service function."""

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    def test_reset_clears_singleton(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test that reset clears the singleton, causing new instance on next call."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        service1 = get_llm_service()
        reset_llm_service()
        service2 = get_llm_service()

        assert service1 is not service2


class TestLLMServiceProtocol:
    """Tests verifying protocol compliance."""

    @patch("integrations.llm.gemini.settings")
    @patch("integrations.llm.gemini.genai.Client")
    def test_gemini_service_implements_protocol(
        self, mock_client_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test that GeminiLLMService implements LLMService protocol."""
        mock_settings.GEMINI_API_KEY = "test-key"  # pragma: allowlist secret
        mock_settings.GOOGLE_API_KEY = None

        from integrations.llm.gemini import GeminiLLMService

        service = GeminiLLMService()

        # Check protocol compliance via isinstance (runtime_checkable)
        assert isinstance(service, LLMService)

        # Verify required methods exist
        assert hasattr(service, "generate_content")
        assert callable(service.generate_content)
        assert hasattr(service, "health_check")
        assert callable(service.health_check)
