"""Gemini LLM Service implementation.

This module provides the GeminiLLMService class that implements the LLMService
protocol using Google's new unified google-genai SDK.

Design Patterns:
- Facade: Simplifies access to the complex google-genai SDK
- Strategy: Implements LLMService protocol for provider swapping

Migration Notes:
- OLD SDK: google-generativeai (deprecated Nov 30, 2025)
- NEW SDK: google-genai (unified SDK for all GenAI models)
- Guide: https://ai.google.dev/gemini-api/docs/migrate
"""

import logging
import time
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings

from .dto import LLMResponse, LLMUsageMetadata
from .exceptions import (
    LLMAuthenticationError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


class GeminiLLMService:
    """Gemini implementation of LLMService protocol.

    This class wraps the google-genai SDK, providing a clean interface
    for generating content with Gemini models.

    Attributes:
        DEFAULT_MODEL: Default model to use for generation
        _client: The google-genai Client instance

    Example:
        >>> service = GeminiLLMService()
        >>> response = await service.generate_content("Hello!")
        >>> print(response.text)
    """

    DEFAULT_MODEL = "gemini-2.5-flash"
    PROVIDER_NAME = "gemini"

    def __init__(self, model: str | None = None) -> None:
        """Initialize the Gemini service.

        Args:
            model: Optional default model override

        Note:
            API key validation is deferred to first use to match legacy SDK
            behavior and allow tests to import modules without API keys.
        """
        # Resolve API key: GEMINI_API_KEY preferred, GOOGLE_API_KEY fallback
        self._api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        self._client: genai.Client | None = None
        self._default_model = model or self.DEFAULT_MODEL

        if self._api_key:
            # Log masked API key for debugging (first 8 + last 4 chars)
            masked_key = self._mask_api_key(self._api_key)
            key_source = (
                "GEMINI_API_KEY"
                if settings.GEMINI_API_KEY
                else "GOOGLE_API_KEY (fallback)"
            )
            logger.info(
                f"GeminiLLMService initialized with model: {self._default_model} "
                f"using google-genai SDK | key_source={key_source} | "
                f"api_key={masked_key}"
            )
        else:
            logger.warning(
                "GeminiLLMService initialized without API key - "
                "generate_content will fail until key is configured"
            )

    # Truncation limits for logging
    PROMPT_LOG_LIMIT = 200
    RESPONSE_LOG_LIMIT = 200

    @staticmethod
    def _mask_api_key(api_key: str) -> str:
        """Mask API key for safe logging, showing first 8 and last 4 chars."""
        if len(api_key) <= 12:
            return "***" + api_key[-4:] if len(api_key) >= 4 else "****"
        return api_key[:8] + "..." + api_key[-4:]

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        """Truncate text for logging, adding ellipsis if truncated."""
        if len(text) <= limit:
            return text
        return text[:limit] + "..."

    def _ensure_client(self) -> genai.Client:
        """Get or create the Gemini client, validating API key.

        Returns:
            The initialized genai.Client

        Raises:
            LLMAuthenticationError: If no API key is configured
        """
        if self._client is None:
            if not self._api_key:
                raise LLMAuthenticationError(
                    "No Gemini API key configured. Set GEMINI_API_KEY or GOOGLE_API_KEY.",
                    provider=self.PROVIDER_NAME,
                )
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def generate_content(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate content using Gemini.

        Args:
            prompt: The text prompt to send
            model: Optional model override
            temperature: Optional sampling temperature (0.0-2.0)
            max_tokens: Optional maximum output tokens

        Returns:
            LLMResponse with generated text and usage metadata

        Raises:
            LLMAuthenticationError: Invalid API key
            LLMRateLimitError: Rate limit exceeded
            LLMResponseError: Empty or invalid response
            LLMTimeoutError: Request timed out
            LLMError: Other errors
        """
        model_name = model or self._default_model
        start_time = time.time()

        try:
            # Build generation config if custom parameters provided
            config: dict[str, Any] | None = None
            if temperature is not None or max_tokens is not None:
                config_params: dict[str, Any] = {}
                if temperature is not None:
                    config_params["temperature"] = temperature
                if max_tokens is not None:
                    config_params["max_output_tokens"] = max_tokens
                config = config_params

            # Log request
            logger.info(
                f"Gemini request | model={model_name} | "
                f"prompt_len={len(prompt)} | prompt={self._truncate(prompt, self.PROMPT_LOG_LIMIT)!r}"
            )

            # Call Gemini API using new SDK pattern
            client = self._ensure_client()
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**config) if config else None,
            )

            response_time_ms = int((time.time() - start_time) * 1000)

            # Check for empty response
            if not response.text:
                raise LLMResponseError(
                    "Gemini returned an empty response",
                    provider=self.PROVIDER_NAME,
                )

            # Extract usage metadata
            usage = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = LLMUsageMetadata(
                    prompt_tokens=getattr(
                        response.usage_metadata, "prompt_token_count", 0
                    )
                    or 0,
                    completion_tokens=getattr(
                        response.usage_metadata, "candidates_token_count", 0
                    )
                    or 0,
                    total_tokens=getattr(
                        response.usage_metadata, "total_token_count", 0
                    )
                    or 0,
                )

            # Log response
            logger.info(
                f"Gemini response | model={model_name} | time={response_time_ms}ms | "
                f"tokens={usage.prompt_tokens if usage else 0}+{usage.completion_tokens if usage else 0} | "
                f"response_len={len(response.text)} | response={self._truncate(response.text, self.RESPONSE_LOG_LIMIT)!r}"
            )

            return LLMResponse(
                text=response.text,
                model=model_name,
                usage=usage,
                response_time_ms=response_time_ms,
            )

        except LLMError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            error_str = str(e).lower()

            # Classify the error
            if "api key" in error_str or "authentication" in error_str:
                logger.error(f"Gemini authentication error after {response_time_ms}ms")
                raise LLMAuthenticationError(
                    f"Gemini authentication failed: {e}",
                    provider=self.PROVIDER_NAME,
                ) from e
            if "rate limit" in error_str or "quota" in error_str:
                logger.warning(f"Gemini rate limit hit after {response_time_ms}ms")
                raise LLMRateLimitError(
                    f"Gemini rate limit exceeded: {e}",
                    provider=self.PROVIDER_NAME,
                ) from e
            if "timeout" in error_str or "deadline" in error_str:
                logger.warning(f"Gemini timeout after {response_time_ms}ms")
                raise LLMTimeoutError(
                    f"Gemini request timed out: {e}",
                    provider=self.PROVIDER_NAME,
                ) from e
            logger.error(f"Gemini error after {response_time_ms}ms: {e}", exc_info=True)
            raise LLMError(
                f"Gemini generation failed: {e}",
                provider=self.PROVIDER_NAME,
            ) from e

    async def health_check(self) -> bool:
        """Verify Gemini API connectivity.

        Sends a minimal "ping" prompt to verify the service is available.

        Returns:
            True if healthy, False otherwise (including if no API key)
        """
        try:
            client = self._ensure_client()
            response = await client.aio.models.generate_content(
                model=self._default_model,
                contents="ping",
            )
            return bool(response.text)
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False
