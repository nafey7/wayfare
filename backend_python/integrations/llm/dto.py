"""Data Transfer Objects for LLM integration.

These DTOs provide a standardized interface for LLM requests and responses,
decoupling the application from specific provider implementations.
"""

from pydantic import BaseModel, Field


class LLMUsageMetadata(BaseModel):
    """Token usage metadata from LLM response."""

    prompt_tokens: int = Field(default=0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(
        default=0, description="Number of tokens in the completion"
    )
    total_tokens: int = Field(default=0, description="Total tokens used")


class LLMResponse(BaseModel):
    """Standardized LLM response.

    This DTO wraps responses from any LLM provider in a consistent format,
    enabling easy provider swapping and testing.
    """

    text: str = Field(..., description="Generated text content")
    model: str = Field(..., description="Model identifier used for generation")
    usage: LLMUsageMetadata | None = Field(
        default=None, description="Token usage statistics"
    )
    response_time_ms: int = Field(
        default=0, description="Response time in milliseconds"
    )
