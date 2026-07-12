"""Custom exceptions for LLM integration.

These exceptions provide specific error handling for LLM operations,
enabling appropriate retry logic and error messages.
"""


class LLMError(Exception):
    """Base exception for all LLM-related errors.

    Attributes:
        message: Human-readable error message
        provider: The LLM provider that raised the error (e.g., "gemini")
    """

    def __init__(self, message: str, provider: str = "unknown") -> None:
        self.message = message
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class LLMAuthenticationError(LLMError):
    """Raised when API key is invalid or missing.

    This error is not retryable - requires configuration fix.
    """

    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded.

    This error is retryable after a backoff period.

    Attributes:
        retry_after_seconds: Suggested wait time before retry (if provided by API)
    """

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message, provider)
        self.retry_after_seconds = retry_after_seconds


class LLMResponseError(LLMError):
    """Raised when the LLM returns an invalid or unexpected response.

    This includes empty responses, malformed JSON, or safety blocks.
    """

    pass


class LLMTimeoutError(LLMError):
    """Raised when the LLM request times out.

    This error is retryable.
    """

    pass
