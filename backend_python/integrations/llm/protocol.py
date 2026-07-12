"""LLM Service Protocol - vendor-agnostic interface.

This module defines the Protocol (interface) that all LLM providers must implement.
Using Protocol enables:
- Structural typing (duck typing with type hints)
- Easy mocking in tests
- Future provider swapping (Claude, OpenAI, etc.)

Design Patterns:
- Strategy Pattern: Different providers implement the same interface
- Facade Pattern: Each provider wraps a complex SDK behind a simple interface
"""

from typing import Protocol, runtime_checkable

from integrations.llm.dto import LLMResponse


@runtime_checkable
class LLMService(Protocol):
    """Protocol for LLM service implementations.

    All LLM providers (Gemini, Claude, OpenAI) implement this protocol,
    enabling:
    - Provider independence in application code
    - Easy testing with mock implementations
    - A/B testing between providers
    - Failover capabilities

    Example:
        >>> from integrations.llm import get_llm_service
        >>> llm = get_llm_service()
        >>> response = await llm.generate_content("Hello, world!")
        >>> print(response.text)
    """

    async def generate_content(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate content from a prompt.

        Args:
            prompt: The text prompt to send to the LLM
            model: Optional model override (uses default if not specified)
            temperature: Optional sampling temperature (0.0-2.0)
            max_tokens: Optional maximum output tokens

        Returns:
            LLMResponse with generated text and usage metadata

        Raises:
            LLMAuthenticationError: Invalid or missing API key
            LLMRateLimitError: Rate limit exceeded
            LLMResponseError: Invalid response from provider
            LLMTimeoutError: Request timed out
            LLMError: Other provider errors
        """
        ...

    async def health_check(self) -> bool:
        """Verify service connectivity.

        Sends a minimal request to verify the service is available
        and properly authenticated.

        Returns:
            True if service is healthy, False otherwise
        """
        ...
