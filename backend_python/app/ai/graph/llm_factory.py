"""Multi-provider LLM factory for V2 multi-agent architecture.

Centralizes LLM creation across all components (supervisor, agents, tools).
Each component can be configured to use a different provider and model via
environment variables, with sensible defaults that match current behavior.

Environment variable pattern:
    LLM_{COMPONENT}_PROVIDER=gemini|openai|xai|bedrock
    LLM_{COMPONENT}_MODEL=model-name

Components:
    SUPERVISOR      — Intent classifier (Layer 1)
    AGENT_FLIGHT    — Flight agent ReAct loop (Layer 2)
    AGENT_HOTEL     — Hotel agent ReAct loop (Layer 2)
    AGENT_ITINERARY — Itinerary agent ReAct loop (Layer 2)
    AGENT_GENERAL   — General agent ReAct loop (Layer 2)
    TOOL_DATES      — Date parsing tool (Layer 3)
    TOOL_ITINERARY  — Itinerary generation tool (Layer 3)
    TOOL_BUDGET     — Budget estimation tool (Layer 3)

Usage:
    from app.ai.graph.llm_factory import create_llm

    llm = create_llm("supervisor", temperature=0.1)
    llm = create_llm("agent_flight", temperature=0.3)
    llm = create_llm("tool_dates", temperature=0.0)
"""

import logging
from typing import Any

__all__ = [
    "create_fallback_llm",
    "create_llm",
    "get_all_component_configs",
    "get_component_config",
    "get_fallback_config",
]

from langchain_core.language_models import BaseChatModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported providers
# ---------------------------------------------------------------------------
PROVIDERS = ("gemini", "openai", "xai", "bedrock")

# ---------------------------------------------------------------------------
# Default configuration per component — matches pre-factory production behavior.
# Every component defaults to gemini/gemini-2.5-pro so deploying this change
# is a no-op until env vars are set.  Override via LLM_{COMPONENT}_PROVIDER
# and LLM_{COMPONENT}_MODEL env vars (e.g. openai / gpt-5.4-mini for agents).
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: dict[str, dict[str, str]] = {
    "supervisor": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "agent_flight": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "agent_hotel": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "agent_itinerary": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "agent_general": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "tool_dates": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "tool_itinerary": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "tool_budget": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "conversation_namer": {"provider": "openai", "model": "gpt-5.4-nano"},
}

# Fallback models per provider (used by ModelFallbackMiddleware in agents)
DEFAULT_FALLBACK: dict[str, str] = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-5.4-mini",
    "xai": "grok-4-1-fast-non-reasoning",
    "bedrock": "deepseek.v3.2",
}


# ---------------------------------------------------------------------------
# Component config resolution
# ---------------------------------------------------------------------------
def get_component_config(component: str) -> dict[str, str]:
    """Resolve provider + model for a component.

    Priority:
        1. Env var: LLM_{COMPONENT}_PROVIDER / LLM_{COMPONENT}_MODEL
        2. Settings attribute (if added to config.py)
        3. DEFAULT_CONFIG fallback

    Args:
        component: One of the component names (e.g. "supervisor", "agent_flight")

    Returns:
        Dict with "provider" and "model" keys.
    """
    defaults = DEFAULT_CONFIG.get(component)
    if defaults is None:
        raise ValueError(
            f"Unknown LLM component: {component!r}. "
            f"Valid components: {sorted(DEFAULT_CONFIG.keys())}"
        )

    key = component.upper()

    # Check env-based settings on the Settings object
    provider = getattr(settings, f"LLM_{key}_PROVIDER", None) or defaults["provider"]
    model = getattr(settings, f"LLM_{key}_MODEL", None) or defaults["model"]

    return {"provider": provider.strip().lower(), "model": model.strip()}


def get_fallback_config(component: str) -> dict[str, str]:
    """Resolve fallback provider + model for a component.

    Uses same provider as the primary model but switches to the fallback model.
    Can be overridden via LLM_{COMPONENT}_FALLBACK_MODEL env var.
    """
    primary = get_component_config(component)
    key = component.upper()

    fallback_model = getattr(
        settings, f"LLM_{key}_FALLBACK_MODEL", None
    ) or DEFAULT_FALLBACK.get(primary["provider"], "gemini-2.5-flash")

    return {"provider": primary["provider"], "model": fallback_model}


# ---------------------------------------------------------------------------
# API key resolution per provider
# ---------------------------------------------------------------------------
def _get_api_key(provider: str) -> str | None:
    """Get API key for a provider from settings."""
    if provider == "gemini":
        key = settings.GEMINI_API_KEY or getattr(settings, "GOOGLE_API_KEY", None)
        if not key:
            raise ValueError(
                "No Gemini API key configured. Set GEMINI_API_KEY or GOOGLE_API_KEY."
            )
        return key

    if provider == "openai":
        key = getattr(settings, "OPENAI_API_KEY", None)
        if not key:
            raise ValueError("No OpenAI API key configured. Set OPENAI_API_KEY.")
        return key

    if provider == "xai":
        key = getattr(settings, "XAI_API_KEY", None)
        if not key:
            raise ValueError("No xAI API key configured. Set XAI_API_KEY.")
        return key

    if provider == "bedrock":
        # Bedrock uses IAM or bearer token — handled in _create_bedrock_llm
        return None

    raise ValueError(f"Unknown provider: {provider!r}")


# ---------------------------------------------------------------------------
# Provider-specific LLM constructors
# ---------------------------------------------------------------------------
def _create_gemini_llm(model: str, temperature: float, **kwargs: Any) -> BaseChatModel:
    """Create a Gemini LLM via LangChain."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=_get_api_key("gemini"),
        temperature=temperature,
        **kwargs,
    )


def _create_openai_llm(model: str, temperature: float, **kwargs: Any) -> BaseChatModel:
    """Create an OpenAI LLM via LangChain.

    GPT-5.x models (5-nano, 5-mini, 5.4-nano, 5.4-mini, etc.) use the Responses API
    internally. Without use_responses_api=True, ChatOpenAI returns empty content for
    these models. See: https://github.com/langchain-ai/langchain/issues/32477
    """
    from langchain_openai import ChatOpenAI

    # Enable Responses API for GPT-5.x models to avoid empty content bug
    use_responses_api = model.startswith("gpt-5")

    return ChatOpenAI(
        model=model,
        api_key=_get_api_key("openai"),
        temperature=temperature,
        use_responses_api=use_responses_api,
        **kwargs,
    )


def _create_xai_llm(model: str, temperature: float, **kwargs: Any) -> BaseChatModel:
    """Create an xAI (Grok) LLM via LangChain."""
    from langchain_xai import ChatXAI

    return ChatXAI(
        model=model,
        xai_api_key=_get_api_key("xai"),
        temperature=temperature,
        **kwargs,
    )


def _create_bedrock_llm(model: str, temperature: float, **kwargs: Any) -> BaseChatModel:
    """Create an AWS Bedrock LLM via LangChain.

    Supports two auth methods:
        1. Bearer token: AWS_BEARER_TOKEN_BEDROCK env var
        2. IAM keys: AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (boto3 auto-discovery)

    Requires optional dependencies: langchain-aws>=0.2.0 and boto3>=1.34.0
    Install with: pip install langchain-aws boto3
    """
    try:
        from langchain_aws import ChatBedrockConverse
    except ImportError as e:
        raise ImportError(
            "Bedrock provider requires 'langchain-aws' and 'boto3'. "
            "Install with: pip install langchain-aws>=0.2.0 boto3>=1.34.0"
        ) from e

    region = getattr(settings, "AWS_REGION", None) or "us-east-1"
    bearer_token = getattr(settings, "AWS_BEARER_TOKEN_BEDROCK", None)

    llm_kwargs: dict[str, Any] = {
        "model_id": model,
        "region_name": region,
        "temperature": temperature,
        **kwargs,
    }

    if bearer_token:
        try:
            import boto3
        except ImportError as e:
            raise ImportError(
                "Bedrock bearer token auth requires 'boto3'. "
                "Install with: pip install boto3>=1.34.0"
            ) from e

        # boto3 requires aws_access_key_id to be a non-empty string even when
        # using bearer token auth. The value is intentionally a fixed placeholder
        # — it is ignored by the Bedrock endpoint; only aws_secret_access_key
        # (the bearer token) is used for authentication.
        client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            endpoint_url=f"https://bedrock-runtime.{region}.amazonaws.com",
            aws_access_key_id="bedrock-bearer-token-placeholder",
            aws_secret_access_key=bearer_token,
        )
        llm_kwargs["client"] = client

    return ChatBedrockConverse(**llm_kwargs)


# Provider → constructor mapping
_PROVIDER_FACTORIES = {
    "gemini": _create_gemini_llm,
    "openai": _create_openai_llm,
    "xai": _create_xai_llm,
    "bedrock": _create_bedrock_llm,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def create_llm(
    component: str,
    temperature: float,
    **kwargs: Any,
) -> BaseChatModel:
    """Create an LLM for a specific component.

    Looks up the configured provider + model for the component and returns
    a LangChain BaseChatModel instance.

    Args:
        component: Component name (e.g. "supervisor", "agent_flight", "tool_dates")
        temperature: LLM temperature
        **kwargs: Additional kwargs passed to the provider constructor

    Returns:
        A LangChain BaseChatModel instance (ChatGoogleGenerativeAI, ChatOpenAI, etc.)

    Example:
        llm = create_llm("supervisor", temperature=0.1)
        llm = create_llm("agent_flight", temperature=0.3)
    """
    config = get_component_config(component)
    provider = config["provider"]
    model = config["model"]

    factory = _PROVIDER_FACTORIES.get(provider)
    if factory is None:
        raise ValueError(
            f"Unsupported provider: {provider!r}. "
            f"Supported: {sorted(_PROVIDER_FACTORIES.keys())}"
        )

    logger.info(
        "Creating LLM: component=%s provider=%s model=%s temp=%.1f",
        component,
        provider,
        model,
        temperature,
    )
    return factory(model, temperature, **kwargs)


def create_fallback_llm(
    component: str,
    temperature: float,
    **kwargs: Any,
) -> BaseChatModel:
    """Create a fallback LLM for a component (used by ModelFallbackMiddleware).

    Uses same provider as primary but with the fallback model.

    Args:
        component: Component name
        temperature: LLM temperature
        **kwargs: Additional kwargs

    Returns:
        A LangChain BaseChatModel instance for the fallback model
    """
    config = get_fallback_config(component)
    provider = config["provider"]
    model = config["model"]

    factory = _PROVIDER_FACTORIES.get(provider)
    if factory is None:
        raise ValueError(f"Unsupported provider: {provider!r}")

    logger.info(
        "Creating fallback LLM: component=%s provider=%s model=%s temp=%.1f",
        component,
        provider,
        model,
        temperature,
    )
    return factory(model, temperature, **kwargs)


def get_all_component_configs() -> dict[str, dict[str, str]]:
    """Return resolved config for all components (for logging/debugging)."""
    return {name: get_component_config(name) for name in DEFAULT_CONFIG}
