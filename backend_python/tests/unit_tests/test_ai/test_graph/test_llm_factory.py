"""Unit tests for the multi-provider LLM factory.

Tests cover:
- use_responses_api=True is set for GPT-5.x models (avoids empty content bug)
- use_responses_api=False for older OpenAI models (gpt-4o, gpt-4.1-nano, etc.)
- Correct LLM class returned per provider (OpenAI, xAI, Gemini)
- Component config resolution from env/defaults
- Unknown component raises ValueError
"""

from unittest.mock import MagicMock, patch

import pytest


class TestCreateOpenAILLM:
    """Tests for _create_openai_llm — specifically use_responses_api behaviour."""

    def _make_llm(self, model: str) -> MagicMock:
        """Helper: call _create_openai_llm with a mocked ChatOpenAI constructor."""
        from app.ai.graph.llm_factory import _create_openai_llm

        with (
            patch("app.ai.graph.llm_factory._get_api_key", return_value="test-key"),
            patch("langchain_openai.ChatOpenAI") as mock_cls,
        ):
            mock_cls.return_value = MagicMock()
            _create_openai_llm(model, temperature=0.1)
            return mock_cls

    def test_gpt5_nano_uses_responses_api(self) -> None:
        """gpt-5.4-nano must set use_responses_api=True to avoid empty content."""
        mock_cls = self._make_llm("gpt-5.4-nano")
        _, kwargs = mock_cls.call_args
        assert kwargs.get("use_responses_api") is True

    def test_gpt5_mini_uses_responses_api(self) -> None:
        """gpt-5.4-mini must set use_responses_api=True."""
        mock_cls = self._make_llm("gpt-5.4-mini")
        _, kwargs = mock_cls.call_args
        assert kwargs.get("use_responses_api") is True

    def test_gpt5_base_uses_responses_api(self) -> None:
        """gpt-5 must set use_responses_api=True."""
        mock_cls = self._make_llm("gpt-5")
        _, kwargs = mock_cls.call_args
        assert kwargs.get("use_responses_api") is True

    def test_gpt5_1_uses_responses_api(self) -> None:
        """gpt-5.1 must set use_responses_api=True."""
        mock_cls = self._make_llm("gpt-5.1")
        _, kwargs = mock_cls.call_args
        assert kwargs.get("use_responses_api") is True

    def test_gpt4o_does_not_use_responses_api(self) -> None:
        """gpt-4o uses Chat Completions — must NOT set use_responses_api=True."""
        mock_cls = self._make_llm("gpt-4o")
        _, kwargs = mock_cls.call_args
        assert kwargs.get("use_responses_api") is False

    def test_gpt4o_mini_does_not_use_responses_api(self) -> None:
        """gpt-4o-mini must NOT set use_responses_api=True."""
        mock_cls = self._make_llm("gpt-4o-mini")
        _, kwargs = mock_cls.call_args
        assert kwargs.get("use_responses_api") is False

    def test_gpt41_nano_does_not_use_responses_api(self) -> None:
        """gpt-4.1-nano must NOT set use_responses_api=True."""
        mock_cls = self._make_llm("gpt-4.1-nano")
        _, kwargs = mock_cls.call_args
        assert kwargs.get("use_responses_api") is False


class TestCreateLLMProviderRouting:
    """Tests that create_llm returns the correct LLM class per provider."""

    def test_openai_provider_returns_chatopenai(self) -> None:
        from app.ai.graph.llm_factory import _create_openai_llm

        with (
            patch("app.ai.graph.llm_factory._get_api_key", return_value="test-key"),
            patch("langchain_openai.ChatOpenAI") as mock_cls,
        ):
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            result = _create_openai_llm("gpt-5.4-nano", temperature=0.1)
            assert result is mock_instance

    def test_xai_provider_returns_chatxai(self) -> None:
        from app.ai.graph.llm_factory import _create_xai_llm

        with (
            patch("app.ai.graph.llm_factory._get_api_key", return_value="test-key"),
            patch("langchain_xai.ChatXAI") as mock_cls,
        ):
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            result = _create_xai_llm("grok-4-1-fast-non-reasoning", temperature=0.3)
            assert result is mock_instance

    def test_gemini_provider_returns_chatgooglegenai(self) -> None:
        from app.ai.graph.llm_factory import _create_gemini_llm

        with (
            patch("app.ai.graph.llm_factory._get_api_key", return_value="test-key"),
            patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_cls,
        ):
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            result = _create_gemini_llm("gemini-2.5-pro", temperature=0.5)
            assert result is mock_instance


class TestGetComponentConfig:
    """Tests for component config resolution."""

    def test_unknown_component_raises(self) -> None:
        from app.ai.graph.llm_factory import get_component_config

        with pytest.raises(ValueError, match="Unknown LLM component"):
            get_component_config("nonexistent_component")

    def test_known_component_returns_dict(self) -> None:
        from app.ai.graph.llm_factory import get_component_config

        config = get_component_config("supervisor")
        assert "provider" in config
        assert "model" in config

    def test_env_override_takes_priority(self) -> None:
        """Env var LLM_SUPERVISOR_PROVIDER/MODEL overrides default."""
        from app.ai.graph.llm_factory import get_component_config
        from app.core.config import settings

        with (
            patch.object(settings, "LLM_SUPERVISOR_PROVIDER", "openai"),
            patch.object(settings, "LLM_SUPERVISOR_MODEL", "gpt-5.4-nano"),
        ):
            config = get_component_config("supervisor")
            assert config["provider"] == "openai"
            assert config["model"] == "gpt-5.4-nano"

    def test_all_8_components_are_valid(self) -> None:
        """All expected components resolve without error."""
        from app.ai.graph.llm_factory import get_component_config

        components = [
            "supervisor",
            "agent_flight",
            "agent_hotel",
            "agent_itinerary",
            "agent_general",
            "tool_dates",
            "tool_itinerary",
            "tool_budget",
        ]
        for component in components:
            config = get_component_config(component)
            assert "provider" in config
            assert "model" in config

    def test_provider_env_var_with_surrounding_spaces_is_stripped(self) -> None:
        """Provider value with surrounding spaces is stripped before use."""
        from app.ai.graph.llm_factory import get_component_config
        from app.core.config import settings

        with patch.object(settings, "LLM_SUPERVISOR_PROVIDER", "  openai  "):
            config = get_component_config("supervisor")
            assert config["provider"] == "openai"


class TestGetFallbackConfig:
    """Tests for fallback model resolution."""

    def test_default_fallback_uses_same_provider(self) -> None:
        """Fallback config uses same provider as primary."""
        from app.ai.graph.llm_factory import get_fallback_config

        config = get_fallback_config("supervisor")
        assert "provider" in config
        assert "model" in config

    def test_fallback_model_differs_from_primary(self) -> None:
        """Default fallback model is different from primary model."""
        from app.ai.graph.llm_factory import get_component_config, get_fallback_config

        primary = get_component_config("supervisor")
        fallback = get_fallback_config("supervisor")
        assert primary["provider"] == fallback["provider"]
        assert primary["model"] != fallback["model"]

    def test_env_override_fallback_model(self) -> None:
        """LLM_{COMPONENT}_FALLBACK_MODEL env var overrides default fallback."""
        from app.ai.graph.llm_factory import get_fallback_config
        from app.core.config import settings

        with patch.object(settings, "LLM_SUPERVISOR_FALLBACK_MODEL", "gpt-5.4-nano"):
            config = get_fallback_config("supervisor")
            assert config["model"] == "gpt-5.4-nano"


class TestCreateBedrockLLM:
    """Tests for _create_bedrock_llm — optional dependency and auth paths."""

    def test_bedrock_missing_langchain_aws_raises_helpful_error(self) -> None:
        """ImportError for langchain-aws produces a helpful install message."""
        from app.ai.graph.llm_factory import _create_bedrock_llm

        with (
            patch.dict("sys.modules", {"langchain_aws": None}),
            pytest.raises(ImportError, match="langchain-aws"),
        ):
            _create_bedrock_llm("deepseek.v3.2", temperature=0.1)

    def test_bedrock_iam_auth_creates_llm(self) -> None:
        """Bedrock with IAM (no bearer token) creates ChatBedrockConverse directly."""
        from app.ai.graph.llm_factory import _create_bedrock_llm
        from app.core.config import settings

        mock_converse_cls = MagicMock()
        mock_instance = MagicMock()
        mock_converse_cls.return_value = mock_instance

        fake_aws = MagicMock()
        fake_aws.ChatBedrockConverse = mock_converse_cls

        with (
            patch.dict("sys.modules", {"langchain_aws": fake_aws}),
            patch.object(settings, "AWS_BEARER_TOKEN_BEDROCK", None),
        ):
            result = _create_bedrock_llm("deepseek.v3.2", temperature=0.1)

        assert result is mock_instance
        _, kwargs = mock_converse_cls.call_args
        assert kwargs["model_id"] == "deepseek.v3.2"
        # No boto3 client injected for IAM auth
        assert "client" not in kwargs

    def test_bedrock_bearer_token_injects_boto3_client(self) -> None:
        """Bedrock with bearer token creates boto3 client and injects into kwargs."""
        from app.ai.graph.llm_factory import _create_bedrock_llm
        from app.core.config import settings

        mock_converse_cls = MagicMock()
        mock_converse_cls.return_value = MagicMock()
        fake_aws = MagicMock()
        fake_aws.ChatBedrockConverse = mock_converse_cls

        mock_boto3 = MagicMock()
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        with (
            patch.dict("sys.modules", {"langchain_aws": fake_aws, "boto3": mock_boto3}),
            patch.object(settings, "AWS_BEARER_TOKEN_BEDROCK", "test-bearer-token"),
        ):
            _create_bedrock_llm("deepseek.v3.2", temperature=0.1)

        # boto3.client called with bearer token as secret key
        mock_boto3.client.assert_called_once()
        _, boto_kwargs = mock_boto3.client.call_args
        assert boto_kwargs["aws_secret_access_key"] == "test-bearer-token"
        # Injected client passed to ChatBedrockConverse
        _, converse_kwargs = mock_converse_cls.call_args
        assert converse_kwargs["client"] is mock_client
