"""Tests for LLM Data Transfer Objects."""

from integrations.llm.dto import LLMResponse, LLMUsageMetadata


class TestLLMUsageMetadata:
    """Tests for LLMUsageMetadata DTO."""

    def test_default_values(self) -> None:
        """Test that default values are zero."""
        usage = LLMUsageMetadata()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_custom_values(self) -> None:
        """Test creation with custom token values."""
        usage = LLMUsageMetadata(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_model_dump(self) -> None:
        """Test serialization to dict."""
        usage = LLMUsageMetadata(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
        data = usage.model_dump()
        assert data == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }


class TestLLMResponse:
    """Tests for LLMResponse DTO."""

    def test_minimal_response(self) -> None:
        """Test creation with required fields only."""
        response = LLMResponse(text="Hello, world!", model="gemini-2.5-flash")
        assert response.text == "Hello, world!"
        assert response.model == "gemini-2.5-flash"
        assert response.usage is None
        assert response.response_time_ms == 0

    def test_full_response(self) -> None:
        """Test creation with all fields."""
        usage = LLMUsageMetadata(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        response = LLMResponse(
            text="Generated text",
            model="gemini-2.5-flash",
            usage=usage,
            response_time_ms=234,
        )
        assert response.text == "Generated text"
        assert response.model == "gemini-2.5-flash"
        assert response.usage is not None
        assert response.usage.prompt_tokens == 100
        assert response.response_time_ms == 234

    def test_model_dump_with_usage(self) -> None:
        """Test serialization includes nested usage metadata."""
        usage = LLMUsageMetadata(
            prompt_tokens=10, completion_tokens=20, total_tokens=30
        )
        response = LLMResponse(
            text="Test",
            model="test-model",
            usage=usage,
            response_time_ms=100,
        )
        data = response.model_dump()
        assert data["text"] == "Test"
        assert data["model"] == "test-model"
        assert data["usage"]["prompt_tokens"] == 10
        assert data["response_time_ms"] == 100

    def test_model_dump_without_usage(self) -> None:
        """Test serialization when usage is None."""
        response = LLMResponse(text="Test", model="test-model")
        data = response.model_dump()
        assert data["usage"] is None

    def test_empty_text_allowed(self) -> None:
        """Test that empty text is technically allowed (validation at service level)."""
        response = LLMResponse(text="", model="test-model")
        assert response.text == ""


class TestLLMResponseFromDict:
    """Tests for LLMResponse creation from dictionaries (common pattern)."""

    def test_from_dict_full(self) -> None:
        """Test creating response from dict data."""
        data = {
            "text": "Response text",
            "model": "gemini-2.5-flash",
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150,
            },
            "response_time_ms": 500,
        }
        response = LLMResponse(**data)
        assert response.text == "Response text"
        assert response.usage is not None
        assert response.usage.total_tokens == 150

    def test_from_dict_minimal(self) -> None:
        """Test creating response from minimal dict."""
        data = {"text": "Hello", "model": "test"}
        response = LLMResponse(**data)
        assert response.text == "Hello"
        assert response.model == "test"
