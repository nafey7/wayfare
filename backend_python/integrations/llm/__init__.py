"""LLM Integration Module.

Provides vendor-agnostic LLM access following the Strategy pattern.

This module follows the same integration pattern as FlightLogic:
- Protocol-based interface for provider independence
- Facade pattern wrapping complex SDKs
- Factory function for instantiation

Usage:
    from integrations.llm import get_llm_service, LLMService

    # Get singleton instance (recommended for most cases)
    llm = get_llm_service()
    response = await llm.generate_content("Hello!")

    # Dependency injection in classes
    class MyService:
        def __init__(self, llm_service: LLMService | None = None):
            self._llm = llm_service or get_llm_service()

Configuration:
    Set these environment variables:
    - GEMINI_API_KEY (preferred) or GOOGLE_API_KEY

Future Providers:
    The protocol-based design allows adding new providers (Claude, OpenAI)
    by implementing the LLMService protocol.
"""

import logging

from .dto import LLMResponse, LLMUsageMetadata
from .exceptions import (
    LLMAuthenticationError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from .protocol import LLMService

logger = logging.getLogger(__name__)

# Singleton instance
_llm_service_instance: LLMService | None = None


def get_llm_service(*, force_new: bool = False) -> LLMService:
    """Factory function to get an LLM service instance.

    Returns a singleton instance of the configured LLM provider.
    Currently supports Gemini, with future support for Claude and OpenAI.

    Args:
        force_new: If True, create a new instance instead of returning singleton

    Returns:
        LLMService implementation (currently GeminiLLMService)

    Raises:
        LLMAuthenticationError: If no API key is configured

    Example:
        >>> llm = get_llm_service()
        >>> response = await llm.generate_content("Hello!")
        >>> print(response.text)
    """
    global _llm_service_instance

    if _llm_service_instance is None or force_new:
        # Import here to avoid circular imports and allow lazy loading
        from .gemini import GeminiLLMService

        _llm_service_instance = GeminiLLMService()
        logger.info("Created new GeminiLLMService instance")

    return _llm_service_instance


def reset_llm_service() -> None:
    """Reset the singleton instance.

    Useful for testing or when configuration changes.
    """
    global _llm_service_instance
    _llm_service_instance = None
    logger.info("Reset LLM service singleton")


__all__ = [
    "LLMAuthenticationError",
    "LLMError",
    "LLMRateLimitError",
    "LLMResponse",
    "LLMResponseError",
    "LLMService",
    "LLMTimeoutError",
    "LLMUsageMetadata",
    "get_llm_service",
    "reset_llm_service",
]
